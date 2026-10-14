
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# Endereço de conexão recebido do Docker Compose
DATABASE_URL = os.environ["DATABASE_URL"]

# Motor responsável pela conexão com PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Fábrica de sessões para operações no banco
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# Classe base para nossos futuros modelos de tabelas
class Base(DeclarativeBase):
    pass


# Função simples para testar a conexão
def testar_conexao():
    with engine.connect() as conexao:
        resultado = conexao.execute(text("SELECT 1"))
        return resultado.scalar_one()
