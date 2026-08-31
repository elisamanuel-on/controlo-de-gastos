"""
Testes automáticos da API — correm com `pytest` e também no GitHub Actions (CI).
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db

TEST_DATABASE_URL = "sqlite:///./test_gastos.db"

engine_teste = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)


def get_db_teste():
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = get_db_teste


@pytest.fixture(autouse=True)
def preparar_bd():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


client = TestClient(app)


def test_saude():
    resposta = client.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_pagina_inicial_carrega():
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Controlo de Gastos" in resposta.text


def test_lista_vazia_no_arranque():
    resposta = client.get("/api/movimentos")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_e_listar_movimento():
    payload = {
        "descricao": "Supermercado",
        "valor": 45.50,
        "tipo": "despesa",
        "categoria": "Alimentação",
        "data": str(date.today()),
    }
    resposta = client.post("/api/movimentos", json=payload)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["descricao"] == "Supermercado"
    assert "id" in corpo

    resposta_lista = client.get("/api/movimentos")
    assert resposta_lista.status_code == 200
    assert len(resposta_lista.json()) == 1


def test_resumo_calcula_saldo():
    client.post("/api/movimentos", json={
        "descricao": "Salário", "valor": 1000, "tipo": "receita",
        "categoria": "Salário", "data": str(date.today())
    })
    client.post("/api/movimentos", json={
        "descricao": "Renda", "valor": 300, "tipo": "despesa",
        "categoria": "Casa", "data": str(date.today())
    })
    resposta = client.get("/api/resumo")
    corpo = resposta.json()
    assert corpo["total_receitas"] == 1000
    assert corpo["total_despesas"] == 300
    assert corpo["saldo"] == 700


def test_resumo_agrupa_por_categoria():
    client.post("/api/movimentos", json={
        "descricao": "Mercado 1", "valor": 20, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    })
    client.post("/api/movimentos", json={
        "descricao": "Mercado 2", "valor": 30, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    })
    resposta = client.get("/api/resumo")
    por_categoria = resposta.json()["por_categoria"]
    assert por_categoria[0]["categoria"] == "Alimentação"
    assert por_categoria[0]["total"] == 50


def test_apagar_movimento():
    criado = client.post("/api/movimentos", json={
        "descricao": "Café", "valor": 2.5, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    }).json()

    resposta = client.delete(f"/api/movimentos/{criado['id']}")
    assert resposta.status_code == 204

    resposta_lista = client.get("/api/movimentos")
    assert resposta_lista.json() == []


def test_apagar_movimento_inexistente_devolve_404():
    resposta = client.delete("/api/movimentos/99999")
    assert resposta.status_code == 404


def test_valor_negativo_e_rejeitado():
    resposta = client.post("/api/movimentos", json={
        "descricao": "Erro", "valor": -10, "tipo": "despesa",
        "categoria": "Outros", "data": str(date.today())
    })
    assert resposta.status_code == 422


def test_tipo_invalido_e_rejeitado():
    resposta = client.post("/api/movimentos", json={
        "descricao": "Erro", "valor": 10, "tipo": "poupanca",
        "categoria": "Outros", "data": str(date.today())
    })
    assert resposta.status_code == 422


def test_filtro_por_tipo():
    client.post("/api/movimentos", json={
        "descricao": "Salário", "valor": 900, "tipo": "receita",
        "categoria": "Salário", "data": str(date.today())
    })
    client.post("/api/movimentos", json={
        "descricao": "Renda", "valor": 300, "tipo": "despesa",
        "categoria": "Casa", "data": str(date.today())
    })
    resposta = client.get("/api/movimentos", params={"tipo": "receita"})
    dados = resposta.json()
    assert len(dados) == 1
    assert dados[0]["tipo"] == "receita"