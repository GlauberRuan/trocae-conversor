
FROM python:3.13-slim

WORKDIR /app

# Instala o FFmpeg para converter vídeos e áudios
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instala as bibliotecas Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do worker
COPY . .

# Inicia o processamento das mensagens
CMD ["python", "main.py"]
