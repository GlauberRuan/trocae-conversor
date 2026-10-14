
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def buscar_conversao(job_id: str):
    """Consulta uma solicitação de conversão pelo ID."""

    with SessionLocal() as banco:
        resultado = banco.execute(
            text("""
                SELECT
                    id,
                    nome_arquivo,
                    tipo_midia,
                    formato_origem,
                    formato_destino,
                    email,
                    status,
                    caminho_original,
                    caminho_convertido,
                    worker_id,
                    bloqueado_ate,
                    tentativas
                FROM conversoes
                WHERE id = :job_id
            """),
            {"job_id": job_id},
        )

        conversao = resultado.mappings().first()

        return dict(conversao) if conversao else None


def reservar_conversao(
    job_id: str,
    worker_id: str,
    duracao_segundos: int = 120,
):
    """
    Reserva atomicamente uma conversão.

    Retorna True somente quando este Worker
    consegue assumir a tarefa.
    """

    with SessionLocal() as banco:
        resultado = banco.execute(
            text("""
                UPDATE conversoes
                SET
                    worker_id = :worker_id,
                    bloqueado_ate = NOW()
                        + (:duracao_segundos * INTERVAL '1 second'),
                    tentativas = tentativas + 1,
                    status = 'PROCESSANDO',
                    atualizado_em = NOW()
                WHERE id = :job_id
                  AND status <> 'CONCLUÍDO'
                  AND (
                      worker_id IS NULL
                      OR bloqueado_ate IS NULL
                      OR bloqueado_ate <= NOW()
                  )
                RETURNING id
            """),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "duracao_segundos": duracao_segundos,
            },
        )

        reservado = resultado.first() is not None
        banco.commit()

        return reservado


def renovar_reserva(
    job_id: str,
    worker_id: str,
    duracao_segundos: int = 120,
):
    """Renova uma reserva pertencente ao Worker informado."""

    with SessionLocal() as banco:
        resultado = banco.execute(
            text("""
                UPDATE conversoes
                SET
                    bloqueado_ate = NOW()
                        + (:duracao_segundos * INTERVAL '1 second'),
                    atualizado_em = NOW()
                WHERE id = :job_id
                  AND worker_id = :worker_id
                  AND status = 'PROCESSANDO'
                  AND bloqueado_ate > NOW()
                RETURNING id
            """),
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "duracao_segundos": duracao_segundos,
            },
        )

        renovado = resultado.first() is not None
        banco.commit()

        return renovado


def liberar_reserva(job_id: str, worker_id: str):
    """Libera uma reserva somente se pertencer ao Worker."""

    with SessionLocal() as banco:
        resultado = banco.execute(
            text("""
                UPDATE conversoes
                SET
                    worker_id = NULL,
                    bloqueado_ate = NULL,
                    atualizado_em = NOW()
                WHERE id = :job_id
                  AND worker_id = :worker_id
                RETURNING id
            """),
            {
                "job_id": job_id,
                "worker_id": worker_id,
            },
        )

        liberado = resultado.first() is not None
        banco.commit()

        return liberado
