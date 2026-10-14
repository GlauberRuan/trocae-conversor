
import os
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Conversao
from storage import BUCKET_CONVERTIDOS, minio_client


router = APIRouter()

PUBLIC_API_URL = os.getenv(
    "PUBLIC_API_URL",
    "http://localhost:8000"
).rstrip("/")


def obter_banco_download():
    banco = SessionLocal()
    try:
        yield banco
    finally:
        banco.close()


def gerar_link_download(conversao_id: str):
    return (
        f"{PUBLIC_API_URL}/conversoes/"
        f"{conversao_id}/download"
    )


@router.get("/conversoes/{conversao_id}/download")
def baixar_conversao(
    conversao_id: UUID,
    banco: Session = Depends(obter_banco_download),
):
    conversao = banco.get(
        Conversao,
        str(conversao_id)
    )

    if conversao is None:
        raise HTTPException(
            status_code=404,
            detail="Conversão não encontrada."
        )

    if (
        conversao.status != "CONCLUÍDO"
        or not conversao.caminho_convertido
    ):
        raise HTTPException(
            status_code=409,
            detail="Arquivo ainda não disponível para download."
        )

    try:
        resposta_minio = minio_client.get_object(
            BUCKET_CONVERTIDOS,
            conversao.caminho_convertido
        )
    except Exception as erro:
        print(
            f"Erro ao acessar arquivo convertido: {erro}",
            flush=True
        )
        raise HTTPException(
            status_code=404,
            detail="Arquivo convertido não encontrado."
        )

    def transmitir_arquivo():
        try:
            while True:
                bloco = resposta_minio.read(1024 * 1024)
                if not bloco:
                    break
                yield bloco
        finally:
            resposta_minio.close()
            resposta_minio.release_conn()

    nome_arquivo = (
        f"{conversao_id}.{conversao.formato_destino}"
    )

    nome_codificado = quote(nome_arquivo)

    return StreamingResponse(
        transmitir_arquivo(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename*=UTF-8''{nome_codificado}"
            )
        }
    )
