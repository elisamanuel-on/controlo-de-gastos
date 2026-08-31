# Controlo de Gastos

Aplicação full-stack para registar despesas e receitas pessoais, com resumo automático de saldo e distribuição de gastos por categoria.

**Demo ao vivo:** _(a preencher depois do deploy — ver instruções mais abaixo)_
**Documentação da API:** `/docs` (gerada automaticamente pelo FastAPI, via Swagger UI)

## Stack técnica

- **Backend:** Python + [FastAPI](https://fastapi.tiangolo.com/)
- **Base de dados:** SQLite, acedida via [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- **Validação de dados:** [Pydantic](https://docs.pydantic.dev/)
- **Frontend:** HTML + CSS + JavaScript puro, a consumir a API via `fetch`
- **Testes:** [pytest](https://docs.pytest.org/) + `TestClient` do FastAPI (11 testes, cobrindo criação, listagem, filtros, validação e apagar)
- **Integração contínua (CI):** GitHub Actions corre os testes automaticamente a cada `push`/pull request
- **Deployment contínuo (CD):** [Render](https://render.com) faz deploy automático sempre que há um `push` para `main`

## Como correr localmente

```bash
python -m venv venv
source venv/bin/activate   # no Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

A aplicação fica disponível em `http://localhost:8000`, e a documentação interativa da API em `http://localhost:8000/docs`.

## Correr os testes

```bash
pytest -v
```

## Endpoints da API

| Método | Rota                      | Descrição                                   |
|--------|---------------------------|----------------------------------------------|
| GET    | `/api/movimentos`         | Lista movimentos (filtros: `tipo`, `categoria`) |
| POST   | `/api/movimentos`         | Cria um novo movimento                        |
| DELETE | `/api/movimentos/{id}`    | Apaga um movimento                            |
| GET    | `/api/resumo`             | Saldo, totais e despesas agrupadas por categoria |
| GET    | `/api/saude`               | Healthcheck                                   |

## Nota sobre o plano gratuito

O deploy usa o plano gratuito da Render, o que significa duas coisas:

1. **O serviço "adormece" ao fim de 15 minutos sem visitas** e demora cerca de 1 minuto a arrancar de novo na primeira visita seguinte.
2. **O disco é efémero** — os dados ficam guardados em SQLite, mas são repostos sempre que o serviço reinicia. Por isso a aplicação semeia automaticamente alguns movimentos de exemplo no arranque, para a demonstração nunca aparecer vazia.

Para um caso de uso real (não uma demonstração de portfólio), o próximo passo seria mudar para uma base de dados gerida (Postgres) com disco persistente.

---
Projeto de portfólio — [Elisama Manuel](https://elisamanuel-on.github.io/HTML/)