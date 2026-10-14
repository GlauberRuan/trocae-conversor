
# Imagem base com Python 3.13
FROM python:3.13-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia a lista de dependências
COPY requirements.txt .

# Instala as bibliotecas Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Porta utilizada pela API
EXPOSE 8000

# Inicia o servidor FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
