import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from waitress import serve
from main import application
from config import SERVER_HOST, SERVER_PORT, IS_PRODUCTION, validar_configuracao

def iniciar_producao():
    erros = validar_configuracao()
    if erros and IS_PRODUCTION:
        for e in erros:
            print(f"[ERRO PRODUCAO] {e}")
        raise RuntimeError("Configurações obrigatórias ausentes para ambiente de produção.")

    print("=" * 70)
    print("  INICIANDO SERVIDOR DE PRODUÇÃO WSGI (WAITRESS)")
    print("  Aplicação: Sistema de Fiscalização Minerária (SFM)")
    print(f"  Escutando em: http://{SERVER_HOST}:{SERVER_PORT}")
    print("  Conexões seguras: Proxy Reverso TLS (Caddy ou Nginx)")
    print("=" * 70)

    serve(
        application,
        host=SERVER_HOST,
        port=SERVER_PORT,
        threads=8,
        connection_limit=1000,
        channel_timeout=30,
        ident="SFM-Server/1.0",
    )

if __name__ == "__main__":
    iniciar_producao()
