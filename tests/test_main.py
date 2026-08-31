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


def registar_e_autenticar(email="teste@example.com", senha="palavrapasse123", nome="Utilizador Teste"):
    resposta = client.post("/api/auth/registar", json={"nome": nome, "email": email, "senha": senha})
    assert resposta.status_code == 201
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_saude():
    resposta = client.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_pagina_inicial_carrega():
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Controlo de Gastos" in resposta.text


def test_registar_novo_utilizador():
    resposta = client.post("/api/auth/registar", json={
        "nome": "Ana", "email": "ana@example.com", "senha": "segredo123"
    })
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert "access_token" in corpo
    assert corpo["token_type"] == "bearer"


def test_registar_com_email_invalido_e_rejeitado():
    resposta = client.post("/api/auth/registar", json={
        "nome": "Ana", "email": "nao-e-um-email", "senha": "segredo123"
    })
    assert resposta.status_code == 422


def test_registar_email_duplicado_e_rejeitado():
    client.post("/api/auth/registar", json={"nome": "Ana", "email": "dup@example.com", "senha": "segredo123"})
    resposta = client.post("/api/auth/registar", json={"nome": "Outra Ana", "email": "dup@example.com", "senha": "outra123"})
    assert resposta.status_code == 400


def test_login_com_credenciais_corretas():
    client.post("/api/auth/registar", json={"nome": "Bruno", "email": "bruno@example.com", "senha": "segredo123"})
    resposta = client.post("/api/auth/login", data={"username": "bruno@example.com", "password": "segredo123"})
    assert resposta.status_code == 200
    assert "access_token" in resposta.json()


def test_login_com_palavra_passe_errada_e_rejeitado():
    client.post("/api/auth/registar", json={"nome": "Bruno", "email": "bruno2@example.com", "senha": "segredo123"})
    resposta = client.post("/api/auth/login", data={"username": "bruno2@example.com", "password": "errada"})
    assert resposta.status_code == 401


def test_login_com_email_inexistente_e_rejeitado():
    resposta = client.post("/api/auth/login", data={"username": "ninguem@example.com", "password": "qualquer"})
    assert resposta.status_code == 401


def test_movimentos_exige_autenticacao():
    resposta = client.get("/api/movimentos")
    assert resposta.status_code == 401


def test_lista_vazia_no_arranque_para_novo_utilizador():
    cabecalhos = registar_e_autenticar(email="vazio@example.com")
    resposta = client.get("/api/movimentos", headers=cabecalhos)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_e_listar_movimento():
    cabecalhos = registar_e_autenticar(email="cria@example.com")
    payload = {
        "descricao": "Supermercado",
        "valor": 45.50,
        "tipo": "despesa",
        "categoria": "Alimentação",
        "data": str(date.today()),
    }
    resposta = client.post("/api/movimentos", json=payload, headers=cabecalhos)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["descricao"] == "Supermercado"
    assert "id" in corpo

    resposta_lista = client.get("/api/movimentos", headers=cabecalhos)
    assert resposta_lista.status_code == 200
    assert len(resposta_lista.json()) == 1


def test_utilizadores_nao_veem_movimentos_uns_dos_outros():
    cabecalhos_a = registar_e_autenticar(email="userA@example.com")
    cabecalhos_b = registar_e_autenticar(email="userB@example.com")

    client.post("/api/movimentos", json={
        "descricao": "Só da Ana", "valor": 10, "tipo": "despesa",
        "categoria": "Outros", "data": str(date.today())
    }, headers=cabecalhos_a)

    resposta_b = client.get("/api/movimentos", headers=cabecalhos_b)
    assert resposta_b.json() == []

    resposta_a = client.get("/api/movimentos", headers=cabecalhos_a)
    assert len(resposta_a.json()) == 1


def test_resumo_calcula_saldo():
    cabecalhos = registar_e_autenticar(email="saldo@example.com")
    client.post("/api/movimentos", json={
        "descricao": "Salário", "valor": 1000, "tipo": "receita",
        "categoria": "Salário", "data": str(date.today())
    }, headers=cabecalhos)
    client.post("/api/movimentos", json={
        "descricao": "Renda", "valor": 300, "tipo": "despesa",
        "categoria": "Casa", "data": str(date.today())
    }, headers=cabecalhos)
    resposta = client.get("/api/resumo", headers=cabecalhos)
    corpo = resposta.json()
    assert corpo["total_receitas"] == 1000
    assert corpo["total_despesas"] == 300
    assert corpo["saldo"] == 700


def test_resumo_agrupa_por_categoria():
    cabecalhos = registar_e_autenticar(email="categorias@example.com")
    client.post("/api/movimentos", json={
        "descricao": "Mercado 1", "valor": 20, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    }, headers=cabecalhos)
    client.post("/api/movimentos", json={
        "descricao": "Mercado 2", "valor": 30, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    }, headers=cabecalhos)
    resposta = client.get("/api/resumo", headers=cabecalhos)
    por_categoria = resposta.json()["por_categoria"]
    assert por_categoria[0]["categoria"] == "Alimentação"
    assert por_categoria[0]["total"] == 50


def test_apagar_movimento():
    cabecalhos = registar_e_autenticar(email="apagar@example.com")
    criado = client.post("/api/movimentos", json={
        "descricao": "Café", "valor": 2.5, "tipo": "despesa",
        "categoria": "Alimentação", "data": str(date.today())
    }, headers=cabecalhos).json()

    resposta = client.delete(f"/api/movimentos/{criado['id']}", headers=cabecalhos)
    assert resposta.status_code == 204

    resposta_lista = client.get("/api/movimentos", headers=cabecalhos)
    assert resposta_lista.json() == []


def test_apagar_movimento_de_outro_utilizador_devolve_404():
    cabecalhos_a = registar_e_autenticar(email="dono@example.com")
    cabecalhos_b = registar_e_autenticar(email="intruso@example.com")

    criado = client.post("/api/movimentos", json={
        "descricao": "Privado", "valor": 5, "tipo": "despesa",
        "categoria": "Outros", "data": str(date.today())
    }, headers=cabecalhos_a).json()

    resposta = client.delete(f"/api/movimentos/{criado['id']}", headers=cabecalhos_b)
    assert resposta.status_code == 404


def test_apagar_movimento_inexistente_devolve_404():
    cabecalhos = registar_e_autenticar(email="inexistente@example.com")
    resposta = client.delete("/api/movimentos/99999", headers=cabecalhos)
    assert resposta.status_code == 404


def test_valor_negativo_e_rejeitado():
    cabecalhos = registar_e_autenticar(email="negativo@example.com")
    resposta = client.post("/api/movimentos", json={
        "descricao": "Erro", "valor": -10, "tipo": "despesa",
        "categoria": "Outros", "data": str(date.today())
    }, headers=cabecalhos)
    assert resposta.status_code == 422


def test_tipo_invalido_e_rejeitado():
    cabecalhos = registar_e_autenticar(email="tipoinvalido@example.com")
    resposta = client.post("/api/movimentos", json={
        "descricao": "Erro", "valor": 10, "tipo": "poupanca",
        "categoria": "Outros", "data": str(date.today())
    }, headers=cabecalhos)
    assert resposta.status_code == 422


def test_filtro_por_tipo():
    cabecalhos = registar_e_autenticar(email="filtro@example.com")
    client.post("/api/movimentos", json={
        "descricao": "Salário", "valor": 900, "tipo": "receita",
        "categoria": "Salário", "data": str(date.today())
    }, headers=cabecalhos)
    client.post("/api/movimentos", json={
        "descricao": "Renda", "valor": 300, "tipo": "despesa",
        "categoria": "Casa", "data": str(date.today())
    }, headers=cabecalhos)
    resposta = client.get("/api/movimentos", params={"tipo": "receita"}, headers=cabecalhos)
    dados = resposta.json()
    assert len(dados) == 1
    assert dados[0]["tipo"] == "receita"