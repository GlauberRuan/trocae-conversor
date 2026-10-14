
import json
import os

import pika


# Configurações recebidas do Docker Compose
RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_USER = os.environ["RABBITMQ_USER"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]

# Nome da fila de processamento
FILA_CONVERSOES = "fila_conversoes"


def conectar_rabbitmq():
    credenciais = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD
    )

    parametros = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credenciais,
        heartbeat=60,
        blocked_connection_timeout=30
    )

    return pika.BlockingConnection(parametros)


def criar_fila():
    conexao = conectar_rabbitmq()

    try:
        canal = conexao.channel()

        canal.queue_declare(
            queue=FILA_CONVERSOES,
            durable=True
        )

        return FILA_CONVERSOES

    finally:
        conexao.close()


def publicar_conversao(job_id: str):
    conexao = conectar_rabbitmq()

    try:
        canal = conexao.channel()

        # Garante que a fila exista
        canal.queue_declare(
            queue=FILA_CONVERSOES,
            durable=True
        )

        # Solicita confirmação de publicação
        canal.confirm_delivery()

        # A mensagem contém apenas o identificador
        mensagem = {
            "jobId": job_id
        }

        publicado = canal.basic_publish(
            exchange="",
            routing_key=FILA_CONVERSOES,
            body=json.dumps(mensagem),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                message_id=job_id
            ),
            mandatory=True
        )

        return mensagem


    finally:
        conexao.close()
