"""
Controlo de Gastos — API em FastAPI.

Endpoints principais:
  GET    /                    → dashboard (HTML)
  POST   /api/auth/registar   → cria uma conta e devolve um token de acesso + código de recuperação
  POST   /api/auth/login      → autentica e devolve um token de acesso
  POST   /api/auth/recuperar  → repõe a palavra-passe com o código de recuperação
  GET    /api/auth/eu         → dados do utilizador autenticado
  GET    /api/movimentos      → lista movimentos do utilizador autenticado (filtros: tipo, categoria)
  POST   /api/movimentos      → cria um movimento para o utilizador autenticado
  DELETE /api/movimentos/{id} → apaga um movimento do utilizador autenticado
  GET    /api/resumo          → saldo, totais e distribuição por categoria
  GET    /api/saude           → healthcheck simples

Todas as rotas de movimentos exigem autenticação (cabeçalho
`Authorization: Bearer <token>`) e cada utilizador só vê os seus próprios
movimentos.
"""
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import crud
import models
import schemas
import seguranca
from database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Semeia uma conta de demonstração no arranque (útil porque o disco é
    # efémero no plano gratuito da Render — ver README).
    db = SessionLocal()
    try:
        crud.semear_dados_exemplo(db, seguranca.gerar_hash_senha("demo12345"))
    finally:
        db.close()
    yield


app = FastAPI(
    title="Controlo de Gastos API",
    description="API para registar despesas e receitas pessoais, com autenticação por utilizador.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def pagina_inicial(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/auth/registar", response_model=schemas.RegistoSaida, status_code=201)
def registar(dados: schemas.UtilizadorCriar, db: Session = Depends(get_db)):
    if crud.obter_utilizador_por_email(db, dados.email):
        raise HTTPException(status_code=400, detail="Já existe uma conta com este email")
    senha_hash = seguranca.gerar_hash_senha(dados.senha)
    codigo_recuperacao = seguranca.gerar_codigo_recuperacao()
    codigo_hash = seguranca.gerar_hash_senha(codigo_recuperacao)
    utilizador = crud.criar_utilizador(db, dados.nome, dados.email, senha_hash, codigo_hash)
    token = seguranca.criar_token_acesso({"sub": str(utilizador.id)})
    return {"access_token": token, "token_type": "bearer", "codigo_recuperacao": codigo_recuperacao}


@app.post("/api/auth/recuperar", response_model=schemas.RegistoSaida)
def recuperar_password(dados: schemas.RecuperarSenha, db: Session = Depends(get_db)):
    utilizador = crud.obter_utilizador_por_email(db, dados.email)
    codigo_valido = (
        utilizador
        and utilizador.codigo_recuperacao_hash
        and seguranca.verificar_senha(dados.codigo_recuperacao, utilizador.codigo_recuperacao_hash)
    )
    if not codigo_valido:
        raise HTTPException(status_code=400, detail="Email ou código de recuperação incorretos")

    novo_codigo = seguranca.gerar_codigo_recuperacao()
    crud.atualizar_password_e_codigo(
        db,
        utilizador,
        seguranca.gerar_hash_senha(dados.nova_senha),
        seguranca.gerar_hash_senha(novo_codigo),
    )
    token = seguranca.criar_token_acesso({"sub": str(utilizador.id)})
    return {"access_token": token, "token_type": "bearer", "codigo_recuperacao": novo_codigo}


@app.post("/api/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    utilizador = crud.obter_utilizador_por_email(db, form.username)
    if not utilizador or not seguranca.verificar_senha(form.password, utilizador.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="Email ou palavra-passe incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = seguranca.criar_token_acesso({"sub": str(utilizador.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/eu", response_model=schemas.UtilizadorSaida)
def eu(utilizador_atual: models.Utilizador = Depends(seguranca.obter_utilizador_atual)):
    return utilizador_atual


@app.get("/api/movimentos", response_model=List[schemas.MovimentoSaida])
def obter_movimentos(
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
    utilizador_atual: models.Utilizador = Depends(seguranca.obter_utilizador_atual),
):
    return crud.listar_movimentos(db, utilizador_atual.id, tipo=tipo, categoria=categoria)


@app.post("/api/movimentos", response_model=schemas.MovimentoSaida, status_code=201)
def criar_movimento(
    movimento: schemas.MovimentoCriar,
    db: Session = Depends(get_db),
    utilizador_atual: models.Utilizador = Depends(seguranca.obter_utilizador_atual),
):
    return crud.criar_movimento(db, utilizador_atual.id, movimento)


@app.delete("/api/movimentos/{movimento_id}", status_code=204)
def apagar_movimento(
    movimento_id: int,
    db: Session = Depends(get_db),
    utilizador_atual: models.Utilizador = Depends(seguranca.obter_utilizador_atual),
):
    sucesso = crud.apagar_movimento(db, utilizador_atual.id, movimento_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")


@app.get("/api/resumo", response_model=schemas.Resumo)
def obter_resumo(
    db: Session = Depends(get_db),
    utilizador_atual: models.Utilizador = Depends(seguranca.obter_utilizador_atual),
):
    return crud.calcular_resumo(db, utilizador_atual.id)


@app.get("/api/saude")
def verificar_saude():
    return {"status": "ok"}