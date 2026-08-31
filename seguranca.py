"""
Segurança: encriptação de palavras-passe e emissão/validação de tokens JWT.

O hashing de palavras-passe usa só a biblioteca padrão do Python (hashlib,
com PBKDF2-HMAC-SHA256) — de propósito, para não depender de pacotes com
extensões compiladas (bcrypt, argon2) que já nos deram problemas de
instalação noutros ambientes.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import crud
import models
from database import get_db

# Em produção (Render), define a variável de ambiente JWT_SECRET_KEY com um
# valor aleatório. Em desenvolvimento local usa-se este valor por omissão —
# não há problema, porque a app só corre na tua máquina.
CHAVE_SECRETA = os.environ.get(
    "JWT_SECRET_KEY", "chave-de-desenvolvimento-local-nao-usar-em-producao"
)
ALGORITMO = "HS256"
MINUTOS_EXPIRACAO_TOKEN = 60 * 24 * 7  # 7 dias

ITERACOES_PBKDF2 = 260_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES_PBKDF2
    )
    return f"{sal}${hash_bytes.hex()}"


def verificar_senha(senha: str, hash_guardado: str) -> bool:
    try:
        sal, hash_hex = hash_guardado.split("$")
    except ValueError:
        return False
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES_PBKDF2
    )
    return hmac.compare_digest(hash_bytes.hex(), hash_hex)


def criar_token_acesso(dados: dict) -> str:
    para_codificar = dados.copy()
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_EXPIRACAO_TOKEN)
    para_codificar.update({"exp": expira_em})
    return jwt.encode(para_codificar, CHAVE_SECRETA, algorithm=ALGORITMO)


def obter_utilizador_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.Utilizador:
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou sessão expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, CHAVE_SECRETA, algorithms=[ALGORITMO])
        utilizador_id = payload.get("sub")
        if utilizador_id is None:
            raise excecao_credenciais
    except jwt.PyJWTError:
        raise excecao_credenciais

    utilizador = crud.obter_utilizador_por_id(db, int(utilizador_id))
    if utilizador is None:
        raise excecao_credenciais
    return utilizador