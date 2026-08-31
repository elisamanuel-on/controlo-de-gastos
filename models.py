"""
Modelos ORM: Utilizador (conta de acesso) e Movimento (uma despesa ou receita,
que pertence sempre a um utilizador).
"""
import enum
from datetime import date, datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship

from database import Base


class TipoMovimento(str, enum.Enum):
    despesa = "despesa"
    receita = "receita"


class Utilizador(Base):
    __tablename__ = "utilizadores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    codigo_recuperacao_hash = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    movimentos = relationship(
        "Movimento", back_populates="utilizador", cascade="all, delete-orphan"
    )


class Movimento(Base):
    __tablename__ = "movimentos"

    id = Column(Integer, primary_key=True, index=True)
    utilizador_id = Column(Integer, ForeignKey("utilizadores.id"), nullable=False, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    tipo = Column(SAEnum(TipoMovimento), nullable=False)
    categoria = Column(String, nullable=False)
    data = Column(Date, nullable=False, default=date.today)

    utilizador = relationship("Utilizador", back_populates="movimentos")