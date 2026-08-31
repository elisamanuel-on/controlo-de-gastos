"""
reset_password.py — repõe a palavra-passe de uma conta diretamente na base
de dados local, para usar SÓ em emergência (se perderes a palavra-passe E
o código de recuperação ao mesmo tempo).

Não depende do FastAPI nem de mais nenhum pacote do projeto — só usa a
biblioteca padrão do Python — por isso funciona mesmo que o venv não
esteja ativado ou algo esteja partido na aplicação.

Como usar:
    python reset_password.py teu-email@example.com

Depois de correr, é-te pedida a nova palavra-passe (duas vezes, para
confirmar) e o script:
  1. gera um novo código de recuperação (o antigo deixa de valer, tal como
     acontece quando repões a palavra-passe pela aplicação);
  2. atualiza a linha do utilizador na base de dados `gastos.db`;
  3. mostra-te o novo código — guarda-o num sítio seguro.

Nota: pára o servidor (uvicorn) antes de correr este script, para evitar
escritas em simultâneo na mesma base de dados.
"""
import getpass
import hashlib
import os
import secrets
import sqlite3
import sys

ITERACOES_PBKDF2 = 260_000
NOME_BASE_DADOS = "gastos.db"


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES_PBKDF2
    )
    return f"{sal}${hash_bytes.hex()}"


def gerar_codigo_recuperacao() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    partes = ["".join(secrets.choice(alfabeto) for _ in range(4)) for _ in range(3)]
    return "-".join(partes)


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python reset_password.py teu-email@example.com")
        sys.exit(1)

    email = sys.argv[1].strip().lower()

    caminho_bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOME_BASE_DADOS)
    if not os.path.exists(caminho_bd):
        print(f"Não encontrei '{NOME_BASE_DADOS}' em {os.path.dirname(caminho_bd)}.")
        print("Corre este script a partir da pasta do projeto (onde está o gastos.db).")
        sys.exit(1)

    ligacao = sqlite3.connect(caminho_bd)
    cursor = ligacao.cursor()
    cursor.execute("SELECT id, nome FROM utilizadores WHERE email = ?", (email,))
    resultado = cursor.fetchone()

    if resultado is None:
        print(f"Não existe nenhuma conta com o email '{email}'.")
        ligacao.close()
        sys.exit(1)

    utilizador_id, nome = resultado
    print(f"Conta encontrada: {nome} ({email})")

    nova_senha = getpass.getpass("Nova palavra-passe (mínimo 6 caracteres): ")
    if len(nova_senha) < 6:
        print("A palavra-passe tem de ter pelo menos 6 caracteres.")
        ligacao.close()
        sys.exit(1)

    confirmacao = getpass.getpass("Confirma a nova palavra-passe: ")
    if nova_senha != confirmacao:
        print("As palavras-passe não coincidem. Nada foi alterado.")
        ligacao.close()
        sys.exit(1)

    senha_hash = gerar_hash_senha(nova_senha)
    novo_codigo = gerar_codigo_recuperacao()
    codigo_hash = gerar_hash_senha(novo_codigo)

    cursor.execute(
        "UPDATE utilizadores SET senha_hash = ?, codigo_recuperacao_hash = ? WHERE id = ?",
        (senha_hash, codigo_hash, utilizador_id),
    )
    ligacao.commit()
    ligacao.close()

    print()
    print("Palavra-passe reposta com sucesso.")
    print(f"Novo código de recuperação (guarda-o já): {novo_codigo}")
    print("Podes agora voltar a iniciar o servidor e entrar com a nova palavra-passe.")


if __name__ == "__main__":
    main()