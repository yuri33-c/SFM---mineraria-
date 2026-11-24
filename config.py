import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "dados"
DADOS_ORIGINAIS_DIR = DATA_DIR / "originais"
DADOS_PROCESSADOS_DIR = DATA_DIR / "processados"

VIEWS_DIR = BASE_DIR / "app" / "views"
STATIC_DIR = VIEWS_DIR / "static"
RESULTADOS_DIR = BASE_DIR / "resultados"
MAPAS_DIR = RESULTADOS_DIR / "mapas"
RELATORIOS_DIR = RESULTADOS_DIR / "relatorios"
EXPORTACOES_DIR = RESULTADOS_DIR / "exportacoes"

IBGE_SHP_DIR = DADOS_ORIGINAIS_DIR / "ibge"
IBGE_SHP_PATH = IBGE_SHP_DIR / "PA_Municipios_2025.shp"

SIGMINE_DIR = DADOS_ORIGINAIS_DIR / "anm"
SIGMINE_SHP_PATH = SIGMINE_DIR / "PA.shp"

MAPBIOMAS_DIR = DADOS_ORIGINAIS_DIR / "mapbiomas"

COD_IBGE_PARAUAPEBAS = "1505536"
NOME_MUNICIPIO = "Parauapebas"
UF_PADRAO = "PA"

EPSG_GEODESICO = 4674
EPSG_METRICO = 31982

ENV = os.getenv("SFM_ENV", "development").strip().lower()
IS_PRODUCTION = ENV == "production"
SERVER_HOST = os.getenv("SFM_HOST", "127.0.0.1").strip()
SERVER_PORT = int(os.getenv("SFM_PORT", "8000").strip())

raw_allowed_hosts = os.getenv("SFM_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ALLOWED_HOSTS = {h.strip() for h in raw_allowed_hosts if h.strip()}

RATE_LIMIT_REQUESTS = int(os.getenv("SFM_RATE_LIMIT_REQUESTS", "120"))
RATE_LIMIT_WINDOW = int(os.getenv("SFM_RATE_LIMIT_WINDOW_SECONDS", "60"))
DEFAULT_PAGE_LIMIT = 25
MAX_PAGE_LIMIT = 500

def validar_configuracao():
    erros = []
    if IS_PRODUCTION:
        obrigatorios = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        for var in obrigatorios:
            if not os.getenv(var):
                erros.append(f"Variável de ambiente obrigatória não definida: {var}")
    return erros
