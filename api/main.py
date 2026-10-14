from download import router as download_router

from datetime import datetime
from uuid import UUID
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Conversao
from rabbitmq_client import publicar_conversao
from storage import BUCKET_ORIGINAIS, minio_client


app = FastAPI(
    title="Conversor Escalável de Mídia",
    description="API para conversão assíncrona de vídeos, áudios e imagens.",
    version="0.1.0"
)


# ---------------------------------------------------------
# MODELO DE RESPOSTA
# ---------------------------------------------------------

class ConversaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome_arquivo: str
    tipo_midia: str
    formato_origem: str
    formato_destino: str
    email: str
    status: str
    criado_em: datetime
    atualizado_em: datetime
    mensagem_erro: str | None


# ---------------------------------------------------------
# CONEXÃO COM O BANCO
# ---------------------------------------------------------

def obter_banco():
    banco = SessionLocal()

    try:
        yield banco
    finally:
        banco.close()


# ---------------------------------------------------------
# ENDPOINTS BÁSICOS
# ---------------------------------------------------------

@app.get("/")
def inicio():
    return {
        "mensagem": "API do Conversor de Mídia funcionando!"
    }


@app.get("/health")
def verificar_saude():
    return {
        "status": "ok",
        "servico": "api"
    }


# ---------------------------------------------------------
# CONSULTAR CONVERSÃO
# ---------------------------------------------------------

@app.get(
    "/conversoes/{conversao_id}",
    response_model=ConversaoResposta
)
def consultar_conversao(
    conversao_id: UUID,
    banco: Session = Depends(obter_banco)
):
    conversao = banco.get(Conversao, str(conversao_id))

    if conversao is None:
        raise HTTPException(
            status_code=404,
            detail="Conversão não encontrada."
        )

    return conversao


# ---------------------------------------------------------
# CRIAR CONVERSÃO DE TESTE NO BANCO
# ---------------------------------------------------------

@app.post(
    "/conversoes/teste",
    response_model=ConversaoResposta,
    status_code=201
)
def criar_conversao_teste(
    banco: Session = Depends(obter_banco)
):
    nova_conversao = Conversao(
        nome_arquivo="video_teste.mp4",
        tipo_midia="video",
        formato_origem="mp4",
        formato_destino="avi",
        email="teste@exemplo.com",
        status="PENDENTE"
    )

    banco.add(nova_conversao)
    banco.commit()
    banco.refresh(nova_conversao)

    return nova_conversao


# ---------------------------------------------------------
# UPLOAD DE TESTE PARA O MINIO
# ---------------------------------------------------------

@app.post("/upload/teste", status_code=201)
def upload_arquivo_teste(
    arquivo: UploadFile = File(...)
):
    formatos_permitidos = {
        ".jpg", ".jpeg", ".png", ".webp",
        ".mp3", ".wav",
        ".mp4", ".avi", ".mov"
    }

    nome_original = Path(arquivo.filename or "").name
    extensao = Path(nome_original).suffix.lower()

    if extensao not in formatos_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Formato de arquivo não permitido."
        )

    identificador = str(uuid.uuid4())
    nome_minio = f"{identificador}{extensao}"
    caminho_temporario = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao
        ) as temporario:
            caminho_temporario = temporario.name

            while bloco := arquivo.file.read(1024 * 1024):
                temporario.write(bloco)

        minio_client.fput_object(
            bucket_name=BUCKET_ORIGINAIS,
            object_name=nome_minio,
            file_path=caminho_temporario,
            content_type=(
                arquivo.content_type
                or "application/octet-stream"
            )
        )

        return {
            "mensagem": "Arquivo enviado com sucesso!",
            "nome_original": nome_original,
            "nome_minio": nome_minio,
            "bucket": BUCKET_ORIGINAIS
        }

    finally:
        arquivo.file.close()

        if (
            caminho_temporario
            and os.path.exists(caminho_temporario)
        ):
            os.remove(caminho_temporario)


# ---------------------------------------------------------
# SOLICITAR CONVERSÃO
# MINIO + POSTGRESQL + RABBITMQ
# ---------------------------------------------------------

@app.post("/conversoes", status_code=202)
def solicitar_conversao(
    arquivo: UploadFile = File(...),
    formato_destino: str = Form(...),
    email: str = Form(...),
    banco: Session = Depends(obter_banco)
):
    formatos_por_tipo = {
        "imagem": {".jpg", ".jpeg", ".png", ".webp"},
        "audio": {".mp3", ".wav"},
        "video": {".mp4", ".avi", ".mov"}
    }

    formatos_destino = {
        "imagem": {"jpg", "png", "webp"},
        "audio": {"mp3", "wav"},
        "video": {"mp4", "avi", "mov"}
    }

    nome_original = Path(arquivo.filename or "").name
    extensao = Path(nome_original).suffix.lower()
    destino = formato_destino.lower().strip().lstrip(".")

    # Identificar o tipo de mídia
    tipo_midia = None

    for tipo, extensoes in formatos_por_tipo.items():
        if extensao in extensoes:
            tipo_midia = tipo
            break

    if tipo_midia is None:
        raise HTTPException(
            status_code=400,
            detail="Formato de origem não permitido."
        )

    # Validar formato de destino
    if destino not in formatos_destino[tipo_midia]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Formato de destino incompatível "
                "com o tipo de mídia."
            )
        )

    # Validar e-mail
    if not email.strip() or "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Informe um e-mail válido."
        )

    # Identificadores da conversão
    identificador = str(uuid.uuid4())
    nome_minio = f"{identificador}{extensao}"

    caminho_temporario = None
    arquivo_enviado = False
    registro_salvo = False

    try:
        # 1. Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao
        ) as temporario:
            caminho_temporario = temporario.name

            while bloco := arquivo.file.read(1024 * 1024):
                temporario.write(bloco)

        # 2. Enviar arquivo original para o MinIO
        minio_client.fput_object(
            bucket_name=BUCKET_ORIGINAIS,
            object_name=nome_minio,
            file_path=caminho_temporario,
            content_type=(
                arquivo.content_type
                or "application/octet-stream"
            )
        )

        arquivo_enviado = True

        # 3. Registrar solicitação no PostgreSQL
        nova_conversao = Conversao(
            id=identificador,
            nome_arquivo=nome_original,
            tipo_midia=tipo_midia,
            formato_origem=extensao.lstrip("."),
            formato_destino=destino,
            email=email.strip(),
            status="PENDENTE",
            caminho_original=nome_minio
        )

        banco.add(nova_conversao)
        banco.commit()

        registro_salvo = True

        # 4. Publicar tarefa no RabbitMQ
        publicar_conversao(identificador)

        # 5. Retornar resposta sem aguardar conversão
        return {
            "mensagem": (
                "Solicitação registrada e enviada "
                "para processamento!"
            ),
            "jobId": identificador,
            "status": "PENDENTE"
        }

    except Exception as erro:
        banco.rollback()

        # Só remove o arquivo se o registro não
        # tiver sido salvo no PostgreSQL.
        if arquivo_enviado and not registro_salvo:
            try:
                minio_client.remove_object(
                    BUCKET_ORIGINAIS,
                    nome_minio
                )
            except Exception:
                pass

        print(
            f"Erro ao solicitar conversão "
            f"{identificador}: {erro}"
        )

        raise HTTPException(
            status_code=503 if registro_salvo else 500,
            detail=(
                "Solicitação registrada, mas não foi "
                "possível confirmar o envio para a fila."
                if registro_salvo
                else "Não foi possível registrar a solicitação."
            )
        )

    finally:
        arquivo.file.close()

        if (
            caminho_temporario
            and os.path.exists(caminho_temporario)
        ):
            os.remove(caminho_temporario)

app.include_router(download_router)


from frontend_router import router as frontend_router
app.include_router(frontend_router)

