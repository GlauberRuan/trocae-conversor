
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Conversao(Base):
    __tablename__ = "conversoes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    nome_arquivo: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    tipo_midia: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    formato_origem: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    formato_destino: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDENTE"
    )

    caminho_original: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    caminho_convertido: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    mensagem_erro: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
