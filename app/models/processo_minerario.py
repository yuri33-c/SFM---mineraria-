import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import pandas as pd
from shapely import force_2d, make_valid, to_wkb

from app.models.database import obter_conexao
from config import (
    BASE_DIR,
    COD_IBGE_PARAUAPEBAS,
    EPSG_GEODESICO,
    EPSG_METRICO,
    MAPBIOMAS_DIR,
    SIGMINE_SHP_PATH,
)

CAMPOS_ORIGEM = [
    "PROCESSO", "NUMERO", "ANO", "AREA_HA", "ID", "FASE",
    "ULT_EVENTO", "NOME", "SUBS", "USO", "UF", "DSProcesso",
]

FASES_AUTORIZADAS_LAVRA = {
    "CONCESSÃO DE LAVRA",
    "LICENCIAMENTO",
    "LAVRA GARIMPEIRA",
    "REQUERIMENTO DE LAVRA GARIMPEIRA",
    "DIREITO DE REQUERER A LAVRA",
    "REGISTRO DE EXTRAÇÃO",
    "MANIFESTO DE MINA",
}

COLUNAS_ORDENACAO_PERMITIDAS = {
    "area_ha": "area_ha",
    "area_ha_mun": "area_ha_mun",
    "processo": "processo",
    "fase": "fase",
    "nome_titular": "nome_titular",
    "substancia": "substancia",
}

SQL_CRIAR_TABELA = f"""
CREATE TABLE IF NOT EXISTS geo.processos_minerarios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_anm TEXT,
    processo TEXT,
    numero BIGINT,
    ano SMALLINT,
    area_ha NUMERIC(18,4),
    fase TEXT,
    ultimo_evento TEXT,
    nome_titular TEXT,
    substancia TEXT,
    uso TEXT,
    uf TEXT,
    ds_processo TEXT,
    geom geometry(Geometry, {EPSG_GEODESICO}) NOT NULL,
    geometria_valida BOOLEAN NOT NULL,
    geometria_corrigida BOOLEAN NOT NULL DEFAULT FALSE,
    origem_arquivo TEXT NOT NULL,
    importado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

class ProcessoMinerario:
    @staticmethod
    def resumo() -> Dict[str, Any]:
        sql = """
            SELECT
                COUNT(*) AS total_processos,
                COUNT(*) FILTER (WHERE geometria_valida) AS geometrias_validas,
                COUNT(*) FILTER (WHERE NOT geometria_valida) AS geometrias_invalidas,
                COUNT(DISTINCT fase) AS fases_distintas,
                COALESCE(SUM(area_ha), 0) AS area_total_ha
            FROM geo.processos_minerarios;
        """
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql)
                linha = cursor.fetchone()

        return {
            "total_processos": linha[0],
            "geometrias_validas": linha[1],
            "geometrias_invalidas": linha[2],
            "fases_distintas": linha[3],
            "area_total_ha": float(linha[4]) if linha[4] is not None else 0.0,
        }

    @classmethod
    def listar_com_filtros(
        cls,
        limite: int = 25,
        offset: int = 0,
        fase: Optional[str] = None,
        substancia: Optional[str] = None,
        numero: Optional[Any] = None,
        titular: Optional[str] = None,
        termo: Optional[str] = None,
        apenas_parauapebas: bool = True,
        ordenar_por: str = "area_ha_mun",
        ordem_desc: bool = True,
    ) -> Dict[str, Any]:
        tabela = "geo.processos_parauapebas" if apenas_parauapebas else "geo.processos_minerarios"
        coluna_area = "area_ha_mun" if apenas_parauapebas else "area_ha"

        coluna_ordem_segura = COLUNAS_ORDENACAO_PERMITIDAS.get(ordenar_por, coluna_area)
        direcao_ordem = "DESC" if ordem_desc else "ASC"

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                if apenas_parauapebas:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'geo' AND table_name = 'processos_parauapebas'
                        );
                    """)
                    if not cursor.fetchone()[0]:
                        tabela = "geo.processos_minerarios"
                        coluna_ordem_segura = "area_ha"

                condicoes = ["1=1"]
                params: List[Any] = []

                if fase:
                    condicoes.append("fase = %s")
                    params.append(fase.strip())

                if substancia:
                    condicoes.append("substancia ILIKE %s")
                    params.append(f"%{substancia.strip()}%")

                if titular:
                    condicoes.append("nome_titular ILIKE %s")
                    params.append(f"%{titular.strip()}%")

                if numero:
                    num_clean = str(numero).strip().replace(".", "").replace("/", "").replace("-", "")
                    condicoes.append("(CAST(numero AS TEXT) ILIKE %s OR processo ILIKE %s)")
                    params.extend([f"%{num_clean}%", f"%{num_clean}%"])

                if termo:
                    termo_clean = termo.strip()
                    condicoes.append(
                        "(processo ILIKE %s OR nome_titular ILIKE %s OR substancia ILIKE %s OR fase ILIKE %s)"
                    )
                    params.extend([f"%{termo_clean}%", f"%{termo_clean}%", f"%{termo_clean}%", f"%{termo_clean}%"])

                where = " AND ".join(condicoes)

                cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {where};", params)
                total = cursor.fetchone()[0]

                limite_sanitizado = max(1, min(int(limite), 500))
                offset_sanitizado = max(0, int(offset))

                if apenas_parauapebas and tabela == "geo.processos_parauapebas":
                    sql_dados = f"""
                        SELECT id, processo, numero, ano, fase, nome_titular, substancia,
                               area_ha_mun, uf, ultimo_evento, area_ha_original, tipo_recorte
                        FROM {tabela}
                        WHERE {where}
                        ORDER BY {coluna_ordem_segura} {direcao_ordem} NULLS LAST
                        LIMIT %s OFFSET %s;
                    """
                else:
                    sql_dados = f"""
                        SELECT id, processo, numero, ano, fase, nome_titular, substancia,
                               {coluna_area}, uf, ultimo_evento, NULL, NULL
                        FROM {tabela}
                        WHERE {where}
                        ORDER BY {coluna_ordem_segura} {direcao_ordem} NULLS LAST
                        LIMIT %s OFFSET %s;
                    """
                params_pag = params + [limite_sanitizado, offset_sanitizado]
                cursor.execute(sql_dados, params_pag)
                linhas = cursor.fetchall()

        registros = [
            {
                "id": r[0],
                "processo": r[1],
                "numero": r[2],
                "ano": r[3],
                "fase": r[4],
                "nome_titular": r[5],
                "substancia": r[6],
                "area_ha": float(r[7]) if r[7] is not None else None,
                "uf": r[8],
                "ultimo_evento": r[9],
                "area_ha_original": float(r[10]) if r[10] is not None else None,
                "tipo_recorte": r[11],
                "autorizado_lavra": (r[4] or "").strip().upper() in FASES_AUTORIZADAS_LAVRA,
            }
            for r in linhas
        ]

        return {
            "total": total,
            "limite": limite_sanitizado,
            "offset": offset_sanitizado,
            "apenas_parauapebas": apenas_parauapebas,
            "registros": registros,
        }

    @staticmethod
    def listar_fases(apenas_parauapebas: bool = True) -> List[Dict[str, Any]]:
        tabela = "geo.processos_parauapebas" if apenas_parauapebas else "geo.processos_minerarios"
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                if apenas_parauapebas:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'geo' AND table_name = 'processos_parauapebas'
                        );
                    """)
                    if not cursor.fetchone()[0]:
                        tabela = "geo.processos_minerarios"

                cursor.execute(f"""
                    SELECT COALESCE(fase, 'NÃO INFORMADA') AS fase, COUNT(*) AS total
                    FROM {tabela}
                    GROUP BY fase
                    ORDER BY total DESC;
                """)
                linhas = cursor.fetchall()

        return [
            {
                "fase": r[0],
                "total": r[1],
                "amparo_lavra": r[0].upper() in FASES_AUTORIZADAS_LAVRA,
            }
            for r in linhas
        ]

    @classmethod
    def analise_fiscalizacao_tema10(cls) -> Dict[str, Any]:
        arquivos_mapbiomas = [
            f.name for f in MAPBIOMAS_DIR.glob("*")
            if f.is_file() and f.suffix.lower() in (".tif", ".geotiff", ".shp", ".gpkg")
        ]
        tem_mapbiomas = len(arquivos_mapbiomas) > 0

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'geo';
                """)
                tabelas = {r[0] for r in cursor.fetchall()}
                tem_parauapebas = 'processos_parauapebas' in tabelas

                total_proc = proc_com_lavra = proc_sem_lavra = 0
                area_lavra = area_sem_lavra = area_unica_ha = 0.0
                if tem_parauapebas:
                    cursor.execute("""
                        SELECT
                            COUNT(*) AS total,
                            COUNT(*) FILTER (
                                WHERE UPPER(fase) IN ('CONCESSÃO DE LAVRA','LICENCIAMENTO','LAVRA GARIMPEIRA',
                                                      'REQUERIMENTO DE LAVRA GARIMPEIRA','DIREITO DE REQUERER A LAVRA',
                                                      'REGISTRO DE EXTRAÇÃO','MANIFESTO DE MINA')
                            ) AS processos_com_lavra,
                            COUNT(*) FILTER (
                                WHERE UPPER(fase) NOT IN ('CONCESSÃO DE LAVRA','LICENCIAMENTO','LAVRA GARIMPEIRA',
                                                           'REQUERIMENTO DE LAVRA GARIMPEIRA','DIREITO DE REQUERER A LAVRA',
                                                           'REGISTRO DE EXTRAÇÃO','MANIFESTO DE MINA')
                            ) AS processos_sem_lavra,
                            COALESCE(SUM(area_ha_mun) FILTER (
                                WHERE UPPER(fase) IN ('CONCESSÃO DE LAVRA','LICENCIAMENTO','LAVRA GARIMPEIRA',
                                                      'REQUERIMENTO DE LAVRA GARIMPEIRA','DIREITO DE REQUERER A LAVRA',
                                                      'REGISTRO DE EXTRAÇÃO','MANIFESTO DE MINA')
                            ), 0) AS area_lavra_ha,
                            COALESCE(SUM(area_ha_mun) FILTER (
                                WHERE UPPER(fase) NOT IN ('CONCESSÃO DE LAVRA','LICENCIAMENTO','LAVRA GARIMPEIRA',
                                                           'REQUERIMENTO DE LAVRA GARIMPEIRA','DIREITO DE REQUERER A LAVRA',
                                                           'REGISTRO DE EXTRAÇÃO','MANIFESTO DE MINA')
                            ), 0) AS area_sem_lavra_ha
                        FROM geo.processos_parauapebas;
                    """)
                    row = cursor.fetchone()
                    total_proc, proc_com_lavra, proc_sem_lavra = row[0], row[1], row[2]
                    area_lavra, area_sem_lavra = float(row[3]), float(row[4])

                    cursor.execute("""
                        SELECT ROUND((ST_Area(ST_Transform(ST_UnaryUnion(ST_Collect(geom)), 31982)) / 10000.0)::numeric, 2)
                        FROM geo.processos_parauapebas
                        WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom);
                    """)
                    r = cursor.fetchone()
                    area_unica_ha = float(r[0]) if r and r[0] else 0.0

                cruzamento_disponivel = False
                cat_a_ha = cat_b_ha = cat_conforme_ha = 0.0
                if 'cruzamento_fiscalizacao' in tabelas:
                    cursor.execute("SELECT COUNT(*) FROM geo.cruzamento_fiscalizacao;")
                    if cursor.fetchone()[0] > 0:
                        cruzamento_disponivel = True
                        cursor.execute("""
                            SELECT categoria_tema10,
                                   COUNT(*),
                                   ROUND(COALESCE(SUM(area_ha), 0)::numeric, 2)
                            FROM geo.cruzamento_fiscalizacao
                            GROUP BY categoria_tema10;
                        """)
                        for cat, cnt, area in cursor.fetchall():
                            if cat == 'A_FORA_DA_POLIGONAL':
                                cat_a_ha = float(area)
                            elif cat == 'B_INCOMPATIBILIDADE_FASE':
                                cat_b_ha = float(area)
                            elif cat == 'CONFORME_TITULO_VALIDO':
                                cat_conforme_ha = float(area)

        status_cat = "Calculado" if cruzamento_disponivel else "Depende da integração do MapBiomas Coleção 11"
        return {
            "tema": "Tema 10 — Fiscalização de lavra fora da poligonal autorizada",
            "municipio_analisado": "Parauapebas / PA (IBGE 1505536)",
            "data_processamento": None,
            "fontes": {
                "processos": "ANM / SIGMINE — Base Estadual do Pará (EPSG:4674)",
                "limite_municipal": "IBGE — Malha Municipal 2025 (EPSG:4674)",
                "deteccao_mineracao": "MapBiomas — Coleção 11 — Substância Minerada",
                "asset_gee": "projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_mining_substances_v1",
            },
            "mapbiomas_integrado": tem_mapbiomas,
            "cruzamento_calculado": cruzamento_disponivel,
            "status_integracao_mapbiomas": (
                "GeoTIFF localizado no diretório de dados"
                if tem_mapbiomas and not cruzamento_disponivel
                else "Cruzamento espacial calculado" if cruzamento_disponivel
                else "Aguardando GeoTIFF da Coleção 11 em dados/originais/mapbiomas/"
            ),
            "instrucao_obtencao": (
                "Execute scripts/exportar_gee.js no Google Earth Engine, "
                "faça o download do GeoTIFF e deposite em dados/originais/mapbiomas/"
            ),
            "diagnostico_fases_parauapebas": {
                "total_processos_municipio": total_proc,
                "processos_com_amparo_lavra": proc_com_lavra,
                "processos_em_fase_sem_lavra": proc_sem_lavra,
                "area_poligonais_com_lavra_ha": float(area_lavra),
                "area_poligonais_sem_lavra_ha": float(area_sem_lavra),
                "area_unica_sem_sobreposicao_ha": area_unica_ha,
                "area_municipio_oficial_ha": 688586.5,
                "cobertura_percentual": round(area_unica_ha / 688586.5 * 100, 2) if area_unica_ha > 0 else 0,
                "fases_com_amparo_lavra": sorted(FASES_AUTORIZADAS_LAVRA),
            },
            "resultados_cruzamento": {
                "categoria_a": {
                    "codigo": "A_FORA_DA_POLIGONAL",
                    "titulo": "Área minerada fora da poligonal autorizada",
                    "descricao": "Cicatriz de mineração mapeada sem correspondência espacial com qualquer poligonal de título minerário.",
                    "area_ha": cat_a_ha if cruzamento_disponivel else None,
                    "status": status_cat,
                },
                "categoria_b": {
                    "codigo": "B_INCOMPATIBILIDADE_FASE",
                    "titulo": "Possível incompatibilidade de fase administrativa",
                    "descricao": "Mineração sobre processo cadastrado cuja fase não autoriza extração (ex.: Autorização de Pesquisa).",
                    "area_ha": cat_b_ha if cruzamento_disponivel else None,
                    "status": status_cat,
                },
                "categoria_c": {
                    "codigo": "C_SEM_TITULO_IDENTIFICADO",
                    "titulo": "Mineração sem título identificado",
                    "descricao": "Área minerada sem registro de processo correspondente na ANM.",
                    "area_ha": None,
                    "status": status_cat,
                },
            },
        }
