from typing import Any, Dict
from app.models.database import obter_conexao
from config import COD_IBGE_PARAUAPEBAS, MAPBIOMAS_DIR

class StatusBanco:
    @staticmethod
    def verificar() -> Dict[str, Any]:
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("""
                    SELECT current_database(), current_user, version(), PostGIS_Full_Version();
                """)
                banco, usuario, versao_pg, postgis = cursor.fetchone()

                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'geo';
                """)
                tabelas = {row[0] for row in cursor.fetchall()}

                total_processos_pa = 0
                if "processos_minerarios" in tabelas:
                    cursor.execute("SELECT COUNT(*) FROM geo.processos_minerarios;")
                    total_processos_pa = cursor.fetchone()[0]

                total_municipios = 0
                parauapebas_importado = False
                if "municipios" in tabelas:
                    cursor.execute("SELECT COUNT(*) FROM geo.municipios;")
                    total_municipios = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM geo.municipios WHERE cd_mun = %s);",
                        (COD_IBGE_PARAUAPEBAS,),
                    )
                    parauapebas_importado = cursor.fetchone()[0]

                total_processos_parauapebas = 0
                if "processos_parauapebas" in tabelas:
                    cursor.execute("SELECT COUNT(*) FROM geo.processos_parauapebas;")
                    total_processos_parauapebas = cursor.fetchone()[0]

        arquivos_mapbiomas = [
            f.name for f in MAPBIOMAS_DIR.glob("*")
            if f.is_file() and f.suffix.lower() in (".tif", ".geotiff", ".shp", ".gpkg")
        ]

        return {
            "status": "ok",
            "banco": banco,
            "usuario": usuario,
            "versao_postgresql": versao_pg,
            "postgis": postgis,
            "tabelas": {
                "processos_minerarios": {
                    "existe": "processos_minerarios" in tabelas,
                    "total": total_processos_pa,
                },
                "municipios": {
                    "existe": "municipios" in tabelas,
                    "total": total_municipios,
                    "parauapebas_presente": parauapebas_importado,
                },
                "processos_parauapebas": {
                    "existe": "processos_parauapebas" in tabelas,
                    "total": total_processos_parauapebas,
                },
            },
            "mapbiomas": {
                "arquivos_disponiveis": arquivos_mapbiomas,
                "integrado": len(arquivos_mapbiomas) > 0,
                "status_texto": (
                    "Dados disponíveis para cruzamento"
                    if len(arquivos_mapbiomas) > 0
                    else "Aguardando integração de dados da Coleção 11 (Substância Minerada)"
                ),
            },
        }
