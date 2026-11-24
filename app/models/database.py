import os
import psycopg
from dotenv import load_dotenv
from config import BASE_DIR

load_dotenv(BASE_DIR / ".env")

def obter_conexao():
    senha = os.getenv("DB_PASSWORD")
    if not senha or senha == "COLOQUE_SUA_SENHA_AQUI":
        raise RuntimeError("Credenciais do banco de dados não configuradas no arquivo .env.")

    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "fiscalizacao_mineraria"),
        user=os.getenv("DB_USER", "fiscalizacao_app"),
        password=senha,
        connect_timeout=10,
    )
