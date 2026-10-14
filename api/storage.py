
import os

from minio import Minio


MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]

BUCKET_ORIGINAIS = os.environ["MINIO_BUCKET_ORIGINAIS"]
BUCKET_CONVERTIDOS = os.environ["MINIO_BUCKET_CONVERTIDOS"]


# Cliente responsável pela comunicação com o MinIO
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


# Verifica se os buckets necessários existem
def verificar_buckets():
    resultados = {}

    for bucket in [BUCKET_ORIGINAIS, BUCKET_CONVERTIDOS]:
        resultados[bucket] = minio_client.bucket_exists(bucket)

    return resultados
