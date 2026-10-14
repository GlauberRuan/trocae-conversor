
import json
import os
import socket
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pika
from sqlalchemy import text

from database import (
    SessionLocal,
    buscar_conversao,
    reservar_conversao,
    renovar_reserva,
    liberar_reserva,
)
from storage import (
    baixar_arquivo,
    enviar_convertido,
    remover_original,
)
from converter import converter_imagem
from ffmpeg_converter import converter_audio_video


RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_USER = os.environ["RABBITMQ_USER"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]

FILA_CONVERSOES = "fila_conversoes"
FILA_RETRY = "fila_conversoes_retry"

MAX_TENTATIVAS = 3
INTERVALO_RETRY_MS = 10000

DURACAO_RESERVA = 45
INTERVALO_RENOVACAO = 10

WORKER_ID = (
    f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
)


def atualizar_status(
    job_id,
    worker_id,
    status,
    caminho_convertido=None,
    mensagem_erro=None,
):
    with SessionLocal() as banco:
        resultado = banco.execute(
            text("""
                UPDATE conversoes
                SET
                    status = :status,
                    caminho_convertido = COALESCE(
                        :caminho_convertido,
                        caminho_convertido
                    ),
                    mensagem_erro = :mensagem_erro,
                    atualizado_em = NOW()
                WHERE id = :job_id
                  AND worker_id = :worker_id
                  AND bloqueado_ate > NOW()
                  AND status = 'PROCESSANDO'
                RETURNING id
            """),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "status": status,
                "caminho_convertido": caminho_convertido,
                "mensagem_erro": mensagem_erro,
            },
        )

        atualizado = resultado.first() is not None
        banco.commit()
        return atualizado


def renovar_periodicamente(job_id, parar, reserva_perdida):
    while not parar.wait(INTERVALO_RENOVACAO):
        try:
            renovado = renovar_reserva(
                job_id,
                WORKER_ID,
                DURACAO_RESERVA,
            )

            if not renovado:
                reserva_perdida.set()
                print(
                    f"[WORKER] Reserva perdida: {job_id}",
                    flush=True,
                )
                return

        except Exception as erro:
            reserva_perdida.set()
            print(
                f"[WORKER] Falha ao renovar reserva: {erro}",
                flush=True,
            )
            return


def executar_conversao(job_id):
    conversao = buscar_conversao(job_id)

    if conversao is None:
        return "INEXISTENTE"

    if conversao["status"] == "CONCLUÍDO":
        print(
            f"[WORKER] Conversão já concluída: {job_id}",
            flush=True,
        )
        return "CONCLUIDO"

    if (
        conversao["status"] == "ERRO"
        and conversao["tentativas"] >= MAX_TENTATIVAS
    ):
        return "LIMITE"

    reservado = reservar_conversao(
        job_id,
        WORKER_ID,
        DURACAO_RESERVA,
    )

    if not reservado:
        print(
            f"[WORKER] Reserva ativa: {job_id}",
            flush=True,
        )
        return "OCUPADO"

    print(
        f"[WORKER] Processando conversão: {job_id}",
        flush=True,
    )

    parar_renovacao = threading.Event()
    reserva_perdida = threading.Event()

    renovador = threading.Thread(
        target=renovar_periodicamente,
        args=(job_id, parar_renovacao, reserva_perdida),
        daemon=True,
    )
    renovador.start()

    try:
        pausa_teste = int(
            os.getenv("WORKER_PAUSA_TESTE", "0")
        )

        if pausa_teste > 0:
            print(
                f"[WORKER] Pausa de teste: "
                f"{pausa_teste} segundos",
                flush=True,
            )
            time.sleep(pausa_teste)

        extensao_origem = conversao["formato_origem"]
        extensao_destino = conversao["formato_destino"]

        nome_original = conversao["caminho_original"]
        nome_convertido = (
            f"{job_id}.{extensao_destino}"
        )

        with tempfile.TemporaryDirectory() as pasta:
            caminho_origem = str(
                Path(pasta) / f"original.{extensao_origem}"
            )
            caminho_destino = str(
                Path(pasta) / f"convertido.{extensao_destino}"
            )

            baixar_arquivo(
                nome_original,
                caminho_origem,
            )

            if conversao["tipo_midia"] == "imagem":
                converter_imagem(
                    caminho_origem,
                    caminho_destino,
                    extensao_destino,
                )

            elif conversao["tipo_midia"] in {
                "audio",
                "video",
            }:
                converter_audio_video(
                    caminho_origem,
                    caminho_destino,
                    conversao["tipo_midia"],
                    extensao_destino,
                )

            else:
                raise ValueError(
                    "Tipo de mídia não suportado."
                )

            if reserva_perdida.is_set():
                raise RuntimeError(
                    "Reserva perdida durante a conversão."
                )

            enviar_convertido(
                nome_convertido,
                caminho_destino,
            )

            if reserva_perdida.is_set():
                raise RuntimeError(
                    "Reserva perdida antes da conclusão."
                )

            atualizado = atualizar_status(
                job_id,
                WORKER_ID,
                "CONCLUÍDO",
                caminho_convertido=nome_convertido,
            )

            if not atualizado:
                raise RuntimeError(
                    "Não foi possível registrar a conclusão."
                )

            try:
                remover_original(nome_original)
            except Exception as erro:
                print(
                    f"[WORKER] Aviso ao remover original: "
                    f"{erro}",
                    flush=True,
                )

        print(
            f"[WORKER] Conversão concluída: {job_id}",
            flush=True,
        )
        return "CONCLUIDO"

    except Exception as erro:
        print(
            f"[WORKER] Erro na conversão {job_id}: "
            f"{erro}",
            flush=True,
        )

        if not reserva_perdida.is_set():
            try:
                atualizar_status(
                    job_id,
                    WORKER_ID,
                    "ERRO",
                    mensagem_erro=str(erro)[:1000],
                )
            except Exception as erro_banco:
                print(
                    f"[WORKER] Erro ao registrar falha: "
                    f"{erro_banco}",
                    flush=True,
                )

        raise

    finally:
        parar_renovacao.set()
        renovador.join(timeout=5)

        try:
            liberar_reserva(job_id, WORKER_ID)
        except Exception as erro:
            print(
                f"[WORKER] Erro ao liberar reserva: "
                f"{erro}",
                flush=True,
            )


def agendar_nova_entrega(canal, corpo):
    """
    Publica em uma fila temporária.
    Após 10 segundos, o RabbitMQ devolve
    automaticamente a mensagem à fila principal.

    A publicação é confirmada antes do ack
    da mensagem original.
    """
    canal.basic_publish(
        exchange="",
        routing_key=FILA_RETRY,
        body=corpo,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
        mandatory=True,
    )


def rejeitar_para_dlq(canal, metodo):
    canal.basic_reject(
        delivery_tag=metodo.delivery_tag,
        requeue=False,
    )


def processar_mensagem(
    canal,
    metodo,
    propriedades,
    corpo,
):
    try:
        mensagem = json.loads(corpo)
        job_id = mensagem["jobId"]

        if not isinstance(job_id, str) or not job_id:
            raise ValueError("jobId inválido.")

    except (ValueError, KeyError, TypeError) as erro:
        print(
            f"[WORKER] Mensagem inválida: {erro}",
            flush=True,
        )
        rejeitar_para_dlq(canal, metodo)
        return

    print(
        f"[WORKER] Mensagem recebida: {job_id}",
        flush=True,
    )

    try:
        resultado = executar_conversao(job_id)

    except Exception as erro:
        print(
            f"[WORKER] Falha: {erro}",
            flush=True,
        )

        # Se o banco estiver indisponível, não devemos
        # confirmar a mensagem e correr o risco de perdê-la.
        conversao = buscar_conversao(job_id)

        if conversao is None:
            rejeitar_para_dlq(canal, metodo)
            return

        if conversao["status"] == "CONCLUÍDO":
            canal.basic_ack(
                delivery_tag=metodo.delivery_tag,
            )
            return

        tentativas = conversao["tentativas"]

        if tentativas >= MAX_TENTATIVAS:
            print(
                f"[WORKER] Limite de {MAX_TENTATIVAS} "
                f"tentativas atingido: {job_id}",
                flush=True,
            )
            rejeitar_para_dlq(canal, metodo)
            return

        print(
            f"[WORKER] Agendando nova tentativa "
            f"({tentativas}/{MAX_TENTATIVAS}): {job_id}",
            flush=True,
        )

        agendar_nova_entrega(canal, corpo)

        canal.basic_ack(
            delivery_tag=metodo.delivery_tag,
        )
        return

    if resultado in {"INEXISTENTE", "LIMITE"}:
        print(
            f"[WORKER] Encaminhando à DLQ: {job_id}",
            flush=True,
        )
        rejeitar_para_dlq(canal, metodo)
        return

    if resultado == "OCUPADO":
        # Uma reserva ativa não conta como tentativa
        # de conversão. A mensagem aguarda 10 segundos.
        agendar_nova_entrega(canal, corpo)

        canal.basic_ack(
            delivery_tag=metodo.delivery_tag,
        )
        return

    canal.basic_ack(
        delivery_tag=metodo.delivery_tag,
    )


def iniciar_worker():
    print(
        f"[WORKER] Iniciando: {WORKER_ID}",
        flush=True,
    )

    credenciais = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    parametros = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credenciais,
        heartbeat=3600,
        blocked_connection_timeout=30,
    )

    while True:
        conexao = None

        try:
            conexao = pika.BlockingConnection(
                parametros
            )

            canal = conexao.channel()

            canal.queue_declare(
                queue=FILA_CONVERSOES,
                durable=True,
            )

            # Fila de espera para novas tentativas.
            canal.queue_declare(
                queue=FILA_RETRY,
                durable=True,
                arguments={
                    "x-message-ttl": INTERVALO_RETRY_MS,
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key":
                        FILA_CONVERSOES,
                },
            )

            # Confirmação da publicação das mensagens
            # de retry antes do ack da mensagem original.
            canal.confirm_delivery()

            canal.basic_qos(
                prefetch_count=1
            )

            canal.basic_consume(
                queue=FILA_CONVERSOES,
                on_message_callback=processar_mensagem,
                auto_ack=False,
            )

            print(
                "[WORKER] Aguardando mensagens...",
                flush=True,
            )

            canal.start_consuming()

        except KeyboardInterrupt:
            print(
                "[WORKER] Encerrando.",
                flush=True,
            )
            break

        except Exception as erro:
            print(
                f"[WORKER] Falha: {erro}",
                flush=True,
            )
            print(
                "[WORKER] Reconectando em 5 segundos...",
                flush=True,
            )
            time.sleep(5)

        finally:
            if conexao is not None:
                try:
                    if conexao.is_open:
                        conexao.close()
                except Exception:
                    pass


if __name__ == "__main__":
    iniciar_worker()
