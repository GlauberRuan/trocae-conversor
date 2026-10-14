
import os

from minio import Minio


# Configurações do MinIO
MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]

BUCKET_ORIGINAIS = os.environ["MINIO_BUCKET_ORIGINAIS"]
BUCKET_CONVERTIDOS = os.environ["MINIO_BUCKET_CONVERTIDOS"]


# Cliente de conexão com o MinIO
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


def baixar_arquivo(nome_arquivo: str, caminho_local: str):
    """
    Baixa um arquivo do bucket de originais
    para uma pasta temporária do Worker.
    """

    minio_client.fget_object(
        bucket_name=BUCKET_ORIGINAIS,
        object_name=nome_arquivo,
        file_path=caminho_local
    )

    return caminho_local


def enviar_convertido(nome_arquivo: str, caminho_local: str):
    """
    Envia o arquivo convertido para o
    bucket de arquivos convertidos.
    """

    minio_client.fput_object(
        bucket_name=BUCKET_CONVERTIDOS,
        object_name=nome_arquivo,
        file_path=caminho_local
    )

    return nome_arquivo


def remover_original(nome_arquivo: str):
    """
    Remove o arquivo original do MinIO.

    IMPORTANTE:
    Esta função só deverá ser chamada
    após a conversão e o armazenamento
    do arquivo convertido serem confirmados.
    """

    minio_client.remove_object(
        bucket_name=BUCKET_ORIGINAIS,
        object_name=nome_arquivo
    )
