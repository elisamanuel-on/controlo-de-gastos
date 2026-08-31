# Controlo de Gastos

Aplicação full-stack para registar despesas e receitas pessoais, com autenticação por utilizador (cada pessoa só vê os seus próprios movimentos), resumo automático de saldo e distribuição de gastos por categoria.

**Demo ao vivo:** https://controlo-de-gastos.onrender.com
**Documentação da API:** https://controlo-de-gastos.onrender.com/docs (gerada automaticamente pelo FastAPI, via Swagger UI)

Para experimentar sem criar conta, usa o botão **"Experimentar com conta de demonstração"** no ecrã de login (email `demo@controlo-de-gastos.app`, palavra-passe `demo12345`).

Ao criar uma conta, é gerado um **código de recuperação** (ex: `AB12-CD34-EF56`), mostrado uma única vez logo após o registo. Serve para repor a palavra-passe caso a esqueças, sem precisar de email — no ecrã de login, usa o link **"Esqueci-me da palavra-passe"**. Cada código só pode ser usado uma vez: ao repor a palavra-passe com sucesso, é emitido automaticamente um novo código.

## Stack técnica

- **Backend:** Python + [FastAPI](https://fastapi.tiangolo.com/)
- **Autenticação:** tokens JWT ([PyJWT](https://pyjwt.readthedocs.io/)), com palavras-passe encriptadas via PBKDF2-HMAC-SHA256 (biblioteca padrão do Python, sem dependências externas)
- **Base de dados:** SQLite, acedida via [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- **Validação de dados:** [Pydantic](https://docs.pydantic.dev/)
- **Frontend:** HTML + CSS + JavaScript puro, a consumir a API via `fetch`
- **Testes:** [pytest](https://docs.pytest.org/) + `TestClient` do FastAPI (cobrindo registo, login, recuperação de palavra-passe por código, isolamento de dados entre utilizadores, validação e CRUD de movimentos)
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
| POST   | `/api/auth/registar`      | Cria uma conta e devolve um token de acesso + código de recuperação |
| POST   | `/api/auth/login`         | Autentica e devolve um token de acesso        |
| POST   | `/api/auth/recuperar`     | Repõe a palavra-passe com o código de recuperação (emite um novo código) |
| GET    | `/api/auth/eu`            | Dados do utilizador autenticado               |
| GET    | `/api/movimentos`         | Lista movimentos do utilizador autenticado (filtros: `tipo`, `categoria`) |
| POST   | `/api/movimentos`         | Cria um novo movimento                        |
| DELETE | `/api/movimentos/{id}`    | Apaga um movimento                            |
| GET    | `/api/resumo`             | Saldo, totais e despesas agrupadas por categoria |
| GET    | `/api/saude`               | Healthcheck                                   |

Todas as rotas de movimentos exigem o cabeçalho `Authorization: Bearer <token>`.

## Recuperação de emergência

Se perderes a palavra-passe **e** o código de recuperação ao mesmo tempo, a aplicação por si só não tem como te deixar entrar — é a troca (trade-off) normal de um sistema de código de recuperação sem email (o mesmo acontece, por exemplo, com códigos de backup de 2FA). Como tens acesso direto à base de dados local, podes repor a tua própria palavra-passe com:

```bash
python reset_password.py teu-email@example.com
```

Pede a nova palavra-passe (duas vezes, para confirmar), atualiza-a diretamente no `gastos.db` e mostra-te um novo código de recuperação. Não depende de mais nenhum pacote do projeto, só da biblioteca padrão do Python. Corre-o com o servidor parado, a partir da pasta do projeto.

## Nota sobre o plano gratuito

O deploy usa o plano gratuito da Render, o que significa duas coisas:

1. **O serviço "adormece" ao fim de 15 minutos sem visitas** e demora cerca de 1 minuto a arrancar de novo na primeira visita seguinte.
2. **O disco é efémero** — os dados (incluindo contas criadas) ficam guardados em SQLite, mas são repostos sempre que o serviço reinicia. Por isso a aplicação semeia automaticamente uma conta de demonstração com alguns movimentos de exemplo no arranque, para a demonstração nunca aparecer vazia.

Para um caso de uso real (não uma demonstração de portfólio), o próximo passo seria mudar para uma base de dados gerida (Postgres) com disco persistente.

---
Projeto de portfólio — [Elisama Manuel](https://elisamanuel-on.github.io/HTML/)