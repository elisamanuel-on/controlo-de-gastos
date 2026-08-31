"""
Operações de acesso à base de dados (Create / Read / Update / Delete).

Todas as operações sobre movimentos são sempre filtradas por `utilizador_id`,
para cada pessoa só ver e alterar os seus próprios dados.
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas


def obter_utilizador_por_email(db: Session, email: str) -> Optional[models.Utilizador]:
    return db.query(models.Utilizador).filter(models.Utilizador.email == email).first()


def obter_utilizador_por_id(db: Session, utilizador_id: int) -> Optional[models.Utilizador]:
    return db.query(models.Utilizador).filter(models.Utilizador.id == utilizador_id).first()


def criar_utilizador(db: Session, nome: str, email: str, senha_hash: str) -> models.Utilizador:
    utilizador = models.Utilizador(nome=nome, email=email, senha_hash=senha_hash)
    db.add(utilizador)
    db.commit()
    db.refresh(utilizador)
    return utilizador


def listar_movimentos(
    db: Session, utilizador_id: int, tipo: Optional[str] = None, categoria: Optional[str] = None
):
    query = db.query(models.Movimento).filter(models.Movimento.utilizador_id == utilizador_id)
    if tipo:
        query = query.filter(models.Movimento.tipo == tipo)
    if categoria:
        query = query.filter(models.Movimento.categoria == categoria)
    return query.order_by(
        models.Movimento.data.desc(), models.Movimento.id.desc()
    ).all()


def criar_movimento(
    db: Session, utilizador_id: int, movimento: schemas.MovimentoCriar
) -> models.Movimento:
    db_movimento = models.Movimento(utilizador_id=utilizador_id, **movimento.model_dump())
    db.add(db_movimento)
    db.commit()
    db.refresh(db_movimento)
    return db_movimento


def apagar_movimento(db: Session, utilizador_id: int, movimento_id: int) -> bool:
    db_movimento = (
        db.query(models.Movimento)
        .filter(
            models.Movimento.id == movimento_id,
            models.Movimento.utilizador_id == utilizador_id,
        )
        .first()
    )
    if not db_movimento:
        return False
    db.delete(db_movimento)
    db.commit()
    return True


def calcular_resumo(db: Session, utilizador_id: int) -> dict:
    total_receitas = db.query(
        func.coalesce(func.sum(models.Movimento.valor), 0.0)
    ).filter(
        models.Movimento.utilizador_id == utilizador_id,
        models.Movimento.tipo == "receita",
    ).scalar()

    total_despesas = db.query(
        func.coalesce(func.sum(models.Movimento.valor), 0.0)
    ).filter(
        models.Movimento.utilizador_id == utilizador_id,
        models.Movimento.tipo == "despesa",
    ).scalar()

    linhas = (
        db.query(models.Movimento.categoria, func.sum(models.Movimento.valor).label("total"))
        .filter(
            models.Movimento.utilizador_id == utilizador_id,
            models.Movimento.tipo == "despesa",
        )
        .group_by(models.Movimento.categoria)
        .order_by(func.sum(models.Movimento.valor).desc())
        .all()
    )
    por_categoria = [{"categoria": c, "total": float(t)} for c, t in linhas]

    total_receitas = float(total_receitas)
    total_despesas = float(total_despesas)

    return {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo": total_receitas - total_despesas,
        "por_categoria": por_categoria,
    }


def semear_dados_exemplo(db: Session, senha_hash_demo: str) -> None:
    """
    Cria uma conta de demonstração com alguns movimentos de exemplo, só se a
    base de dados ainda não tiver nenhum utilizador. Útil porque no plano
    gratuito da Render o disco é efémero (reinicia a cada deploy), por isso
    a demonstração fica sempre com uma conta pronta a experimentar.
    """
    from datetime import date, timedelta

    if db.query(models.Utilizador).first():
        return

    demo = models.Utilizador(
        nome="Conta de Demonstração",
        email="demo@controlo-de-gastos.app",
        senha_hash=senha_hash_demo,
    )
    db.add(demo)
    db.commit()
    db.refresh(demo)

    hoje = date.today()
    exemplos = [
        {"descricao": "Salário", "valor": 1200.0, "tipo": "receita", "categoria": "Salário", "data": hoje.replace(day=1)},
        {"descricao": "Renda de casa", "valor": 350.0, "tipo": "despesa", "categoria": "Casa", "data": hoje - timedelta(days=20)},
        {"descricao": "Supermercado", "valor": 87.40, "tipo": "despesa", "categoria": "Alimentação", "data": hoje - timedelta(days=15)},
        {"descricao": "Passe de transportes", "valor": 40.0, "tipo": "despesa", "categoria": "Transporte", "data": hoje - timedelta(days=14)},
        {"descricao": "Freelance — apoio administrativo", "valor": 150.0, "tipo": "receita", "categoria": "Freelance", "data": hoje - timedelta(days=10)},
        {"descricao": "Farmácia", "valor": 22.90, "tipo": "despesa", "categoria": "Saúde", "data": hoje - timedelta(days=8)},
        {"descricao": "Cinema", "valor": 16.0, "tipo": "despesa", "categoria": "Lazer", "data": hoje - timedelta(days=5)},
        {"descricao": "Curso online", "valor": 29.99, "tipo": "despesa", "categoria": "Educação", "data": hoje - timedelta(days=3)},
    ]
    for dados in exemplos:
        db.add(models.Movimento(utilizador_id=demo.id, **dados))
    db.commit()