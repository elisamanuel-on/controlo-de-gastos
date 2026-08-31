"""
Modelo ORM: um Movimento representa uma despesa ou uma receita.
"""
import enum
from datetime import date

from sqlalchemy import Column, Integer, String, Float, Date, Enum as SAEnum

from database import Base


class TipoMovimento(str, enum.Enum):
    despesa = "despesa"
    receita = "receita"


class Movimento(Base):
    __tablename__ = "movimentos"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    tipo = Column(SAEnum(TipoMovimento), nullable=False)
    categoria = Column(String, nullable=False)
    data = Column(Date, nullable=False, default=date.today)