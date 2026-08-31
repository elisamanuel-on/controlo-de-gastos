"""
Operações de acesso à base de dados (Create / Read / Update / Delete).
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas


def listar_movimentos(
    db: Session, tipo: Optional[str] = None, categoria: Optional[str] = None
):
    query = db.query(models.Movimento)
    if tipo:
        query = query.filter(models.Movimento.tipo == tipo)
    if categoria:
        query = query.filter(models.Movimento.categoria == categoria)
    return query.order_by(
        models.Movimento.data.desc(), models.Movimento.id.desc()
    ).all()


def criar_movimento(db: Session, movimento: schemas.MovimentoCriar) -> models.Movimento:
    db_movimento = models.Movimento(**movimento.model_dump())
    db.add(db_movimento)
    db.commit()
    db.refresh(db_movimento)
    return db_movimento


def apagar_movimento(db: Session, movimento_id: int) -> bool:
    db_movimento = (
        db.query(models.Movimento).filter(models.Movimento.id == movimento_id).first()
    )
    if not db_movimento:
        return False
    db.delete(db_movimento)
    db.commit()
    return True


def calcular_resumo(db: Session) -> dict:
    total_receitas = db.query(
        func.coalesce(func.sum(models.Movimento.valor), 0.0)
    ).filter(models.Movimento.tipo == "receita").scalar()

    total_despesas = db.query(
        func.coalesce(func.sum(models.Movimento.valor), 0.0)
    ).filter(models.Movimento.tipo == "despesa").scalar()

    linhas = (
        db.query(models.Movimento.categoria, func.sum(models.Movimento.valor).label("total"))
        .filter(models.Movimento.tipo == "despesa")
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


def contar_movimentos(db: Session) -> int:
    return db.query(models.Movimento).count()


def semear_dados_exemplo(db: Session) -> None:
    """
    Popula a base de dados com alguns movimentos de exemplo, só se estiver vazia.
    Útil porque no plano gratuito da Render o disco é efémero (reinicia a cada deploy),
    por isso a demonstração fica sempre com dados visíveis.
    """
    from datetime import date, timedelta

    if contar_movimentos(db) > 0:
        return

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
        db.add(models.Movimento(**dados))
    db.commit()