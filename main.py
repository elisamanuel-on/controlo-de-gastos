"""
Controlo de Gastos — API em FastAPI.

Endpoints principais:
  GET    /                    → dashboard (HTML)
  GET    /api/movimentos      → lista movimentos (filtros opcionais: tipo, categoria)
  POST   /api/movimentos      → cria um movimento
  DELETE /api/movimentos/{id} → apaga um movimento
  GET    /api/resumo          → saldo, totais e distribuição por categoria
  GET    /api/saude           → healthcheck simples
"""
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Semeia dados de exemplo no arranque (útil porque o disco é efémero no plano
    # gratuito da Render — ver README).
    db = SessionLocal()
    try:
        crud.semear_dados_exemplo(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Controlo de Gastos API",
    description="API para registar despesas e receitas pessoais.",
    version="1.0.0",
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def pagina_inicial(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/movimentos", response_model=List[schemas.MovimentoSaida])
def obter_movimentos(
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.listar_movimentos(db, tipo=tipo, categoria=categoria)


@app.post("/api/movimentos", response_model=schemas.MovimentoSaida, status_code=201)
def criar_movimento(movimento: schemas.MovimentoCriar, db: Session = Depends(get_db)):
    return crud.criar_movimento(db, movimento)


@app.delete("/api/movimentos/{movimento_id}", status_code=204)
def apagar_movimento(movimento_id: int, db: Session = Depends(get_db)):
    sucesso = crud.apagar_movimento(db, movimento_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")


@app.get("/api/resumo", response_model=schemas.Resumo)
def obter_resumo(db: Session = Depends(get_db)):
    return crud.calcular_resumo(db)


@app.get("/api/saude")
def verificar_saude():
    return {"status": "ok"}