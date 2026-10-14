
import os
import smtplib
import time
from email.message import EmailMessage

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.environ["DATABASE_URL"]
SMTP_HOST = os.getenv("SMTP_HOST", "mailpit")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
API_PUBLIC_URL = os.getenv(
    "API_PUBLIC_URL",
    "http://localhost:8000",
).rstrip("/")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)


def preparar_banco():
    """Adiciona controle de envio sem apagar dados."""

    with engine.begin() as banco:
        banco.execute(
            text("""
                ALTER TABLE conversoes
                ADD COLUMN IF NOT EXISTS
                email_enviado_em TIMESTAMPTZ
            """)
        )


def enviar_email(conversao):
    job_id = conversao["id"]
    destino = conversao["email"]
    arquivo = conversao["nome_arquivo"]

    link = (
        f"{API_PUBLIC_URL}/conversoes/"
        f"{job_id}/download"
    )

    mensagem = EmailMessage()
    mensagem["From"] = "conversor@localhost"
    mensagem["To"] = destino
    mensagem["Subject"] = "Sua conversão foi concluída"

    mensagem.set_content(
        f"Olá!\n\n"
        f"O arquivo {arquivo} foi convertido "
        f"com sucesso.\n\n"
        f"Baixe o arquivo pelo link:\n"
        f"{link}\n\n"
        f"Identificador: {job_id}\n\n"
        f"Conversor de Mídia"
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=15,
    ) as smtp:
        smtp.send_message(mensagem)

    print(
        f"[NOTIFICACAO] E-mail enviado para "
        f"{destino} | Job: {job_id}",
        flush=True,
    )


def processar_notificacao():
    """
    Seleciona uma conversão concluída ainda
    não notificada.

    O bloqueio evita que duas instâncias
    selecionem o mesmo registro ao mesmo tempo.
    """

    with SessionLocal() as banco:
        conversao = banco.execute(
            text("""
                SELECT
                    id,
                    nome_arquivo,
                    email
                FROM conversoes
                WHERE status = 'CONCLUÍDO'
                  AND caminho_convertido IS NOT NULL
                  AND email_enviado_em IS NULL
                ORDER BY criado_em ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
        ).mappings().first()

        if conversao is None:
            banco.rollback()
            return False

        enviar_email(conversao)

        banco.execute(
            text("""
                UPDATE conversoes
                SET email_enviado_em = NOW()
                WHERE id = :job_id
            """),
            {"job_id": conversao["id"]},
        )

        banco.commit()
        return True


def iniciar():
    print(
        "[NOTIFICACAO] Iniciando serviço...",
        flush=True,
    )

    while True:
        try:
            preparar_banco()
            break
        except Exception as erro:
            print(
                f"[NOTIFICACAO] Aguardando banco: {erro}",
                flush=True,
            )
            time.sleep(5)

    print(
        "[NOTIFICACAO] Aguardando conversões...",
        flush=True,
    )

    while True:
        try:
            encontrou = processar_notificacao()

            if not encontrou:
                time.sleep(3)

        except Exception as erro:
            print(
                f"[NOTIFICACAO] Erro: {erro}",
                flush=True,
            )
            time.sleep(5)


if __name__ == "__main__":
    iniciar()
