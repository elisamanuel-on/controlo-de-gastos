"""
Schemas Pydantic — validam os dados que entram e saem da API.
"""
import re
from datetime import date
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, ConfigDict, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TipoMovimento(str, Enum):
    despesa = "despesa"
    receita = "receita"


class MovimentoBase(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=120)
    valor: float = Field(..., gt=0, description="Valor tem de ser maior que zero")
    tipo: TipoMovimento
    categoria: str = Field(..., min_length=1, max_length=60)
    data: date


class MovimentoCriar(MovimentoBase):
    pass


class MovimentoSaida(MovimentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ResumoCategoria(BaseModel):
    categoria: str
    total: float


class Resumo(BaseModel):
    total_receitas: float
    total_despesas: float
    saldo: float
    por_categoria: List[ResumoCategoria]


class UtilizadorCriar(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=150)
    senha: str = Field(..., min_length=6, max_length=100)

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        if not EMAIL_REGEX.match(v):
            raise ValueError("Email inválido")
        return v.lower().strip()


class UtilizadorSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"