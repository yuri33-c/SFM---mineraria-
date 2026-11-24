import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
from shapely import force_2d, make_valid, to_wkb

from app.models.database import obter_conexao
from config import (
    COD_IBGE_PARAUAPEBAS,
    EPSG_GEODESICO,
    EPSG_METRICO,
    IBGE_SHP_PATH,
)

SQL_CRIAR_TABELA_MUNICIPIOS = f"""
CREATE TABLE IF NOT EXISTS geo.municipios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cd_mun VARCHAR(10) NOT NULL UNIQUE,
    nm_mun TEXT NOT NULL,
    sigla_uf VARCHAR(2) NOT NULL,
    area_km2_ibge NUMERIC(14,4),
    area_km2_calculada NUMERIC(14,4),
    geom geometry(Geometry, {EPSG_GEODESICO}) NOT NULL,
    geometria_valida BOOLEAN NOT NULL,
    importado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SQL_CRIAR_TABELA_PROCESSOS_PARAUAPEBAS = f"""
CREATE TABLE IF NOT EXISTS geo.processos_parauapebas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_origem_id BIGINT REFERENCES geo.processos_minerarios(id) ON DELETE CASCADE,
    processo TEXT,
    numero BIGINT,
    ano SMALLINT,
    area_ha_original NUMERIC(18,4),
    area_ha_mun NUMERIC(18,4) NOT NULL,
    fase TEXT,
    ultimo_evento TEXT,
    nome_titular TEXT,
    substancia TEXT,
    uso TEXT,
    uf TEXT,
    ds_processo TEXT,
    tipo_recorte TEXT NOT NULL,
    geom geometry(Geometry, {EPSG_GEODESICO}) NOT NULL,
    processado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

class Municipio:
    @staticmethod
    def localizar_shapefile_ibge() -> Path:
        if not IBGE_SHP_PATH.exists():
            raise FileNotFoundError(f"Arquivo não localizado: {IBGE_SHP_PATH}")
        return IBGE_SHP_PATH

    @classmethod
    def importar_municipio(cls, codigo_ibge: str = COD_IBGE_PARAUAPEBAS) -> Dict[str, Any]:
        arquivo_shp = cls.localizar_shapefile_ibge()
        gdf = gpd.read_file(arquivo_shp)

        if gdf.crs is None:
            raise ValueError("O arquivo não possui CRS definido.")

        if gdf.crs.to_epsg() != EPSG_GEODESICO:
            gdf = gdf.to_crs(epsg=EPSG_GEODESICO)

        filtro = gdf["CD_MUN"].astype(str) == str(codigo_ibge)
        if not filtro.any():
            raise ValueError(f"Código IBGE {codigo_ibge} não encontrado.")

        linha = gdf[filtro].iloc[0]
        nm_mun = str(linha.get("NM_MUN", "Parauapebas"))
        sigla_uf = str(linha.get("SIGLA_UF", "PA"))
        area_km2_ibge = (
            Decimal(str(linha.get("AREA_KM2")))
            if "AREA_KM2" in linha and linha.get("AREA_KM2") is not None
            else None
        )

        geometria = force_2d(linha.geometry)
        geom_valida_origem = bool(geometria.is_valid)
        if not geom_valida_origem:
            geometria = make_valid(geometria)

        if geometria.is_empty:
            raise ValueError(f"Geometria inválida para o código {codigo_ibge}.")

        wkb_bytes = bytes(to_wkb(geometria))

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS geo;")
                cursor.execute(SQL_CRIAR_TABELA_MUNICIPIOS)

                cursor.execute(
                    f"""
                    INSERT INTO geo.municipios (
                        cd_mun, nm_mun, sigla_uf, area_km2_ibge, area_km2_calculada, geom, geometria_valida, importado_em
                    ) VALUES (
                        %s, %s, %s, %s,
                        ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromWKB(%s), {EPSG_GEODESICO}), {EPSG_METRICO})) / 1000000.0,
                        ST_SetSRID(ST_GeomFromWKB(%s), {EPSG_GEODESICO}),
                        %s,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (cd_mun) DO UPDATE SET
                        nm_mun = EXCLUDED.nm_mun,
                        sigla_uf = EXCLUDED.sigla_uf,
                        area_km2_ibge = EXCLUDED.area_km2_ibge,
                        area_km2_calculada = EXCLUDED.area_km2_calculada,
                        geom = EXCLUDED.geom,
                        geometria_valida = EXCLUDED.geometria_valida,
                        importado_em = CURRENT_TIMESTAMP
                    RETURNING id, cd_mun, nm_mun, sigla_uf, area_km2_ibge, area_km2_calculada;
                    """,
                    (
                        str(codigo_ibge),
                        nm_mun,
                        sigla_uf,
                        area_km2_ibge,
                        wkb_bytes,
                        wkb_bytes,
                        geom_valida_origem,
                    ),
                )
                res = cursor.fetchone()

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_municipios_geom
                    ON geo.municipios USING GIST (geom);
                    """
                )

        return {
            "id": res[0],
            "cd_mun": res[1],
            "nm_mun": res[2],
            "sigla_uf": res[3],
            "area_km2_ibge": float(res[4]) if res[4] is not None else None,
            "area_km2_calculada": float(res[5]) if res[5] is not None else None,
        }

    @classmethod
    def recortar_processos_municipio(cls, codigo_ibge: str = COD_IBGE_PARAUAPEBAS) -> Dict[str, Any]:
        cls.importar_municipio(codigo_ibge)

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(SQL_CRIAR_TABELA_PROCESSOS_PARAUAPEBAS)
                cursor.execute("TRUNCATE TABLE geo.processos_parauapebas;")

                sql_recorte = f"""
                WITH mun AS (
                    SELECT geom FROM geo.municipios WHERE cd_mun = %s LIMIT 1
                ),
                cruzamento AS (
                    SELECT
                        p.id AS processo_origem_id,
                        p.processo,
                        p.numero,
                        p.ano,
                        p.area_ha AS area_ha_original,
                        p.fase,
                        p.ultimo_evento,
                        p.nome_titular,
                        p.substancia,
                        p.uso,
                        p.uf,
                        p.ds_processo,
                        ST_Within(p.geom, m.geom) AS totalmente_dentro,
                        CASE
                            WHEN ST_Within(p.geom, m.geom) THEN p.geom
                            ELSE ST_CollectionExtract(
                                ST_MakeValid(ST_Intersection(p.geom, m.geom)),
                                3
                            )
                        END AS geom_recortada
                    FROM geo.processos_minerarios p
                    JOIN mun m ON ST_Intersects(p.geom, m.geom)
                )
                INSERT INTO geo.processos_parauapebas (
                    processo_origem_id, processo, numero, ano, area_ha_original,
                    area_ha_mun, fase, ultimo_evento, nome_titular, substancia,
                    uso, uf, ds_processo, tipo_recorte, geom
                )
                SELECT
                    processo_origem_id,
                    processo,
                    numero,
                    ano,
                    area_ha_original,
                    ROUND(
                        (ST_Area(ST_Transform(geom_recortada, {EPSG_METRICO})) / 10000.0)::numeric,
                        4
                    ) AS area_ha_mun,
                    fase,
                    ultimo_evento,
                    nome_titular,
                    substancia,
                    uso,
                    uf,
                    ds_processo,
                    CASE WHEN totalmente_dentro THEN 'TOTAL' ELSE 'PARCIAL' END AS tipo_recorte,
                    ST_Multi(geom_recortada) AS geom
                FROM cruzamento
                WHERE geom_recortada IS NOT NULL
                  AND NOT ST_IsEmpty(geom_recortada)
                  AND ST_Area(ST_Transform(geom_recortada, {EPSG_METRICO})) > 0;
                """
                cursor.execute(sql_recorte, (str(codigo_ibge),))

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_geom
                    ON geo.processos_parauapebas USING GIST (geom);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_fase
                    ON geo.processos_parauapebas (fase);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_processo
                    ON geo.processos_parauapebas (processo);
                """)

                cursor.execute("""
                    SELECT
                        COUNT(*) AS total_recortados,
                        COUNT(*) FILTER (WHERE tipo_recorte = 'TOTAL') AS total_integrais,
                        COUNT(*) FILTER (WHERE tipo_recorte = 'PARCIAL') AS total_parciais,
                        COALESCE(SUM(area_ha_mun), 0) AS area_total_ha
                    FROM geo.processos_parauapebas;
                """)
                stats = cursor.fetchone()

        return {
            "total_processos": stats[0],
            "total_integrais": stats[1],
            "total_parciais": stats[2],
            "area_total_ha": float(stats[3]),
            "municipio_codigo": str(codigo_ibge),
        }

    @classmethod
    def obter_dados_municipio(cls, codigo_ibge: str = COD_IBGE_PARAUAPEBAS) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT cd_mun, nm_mun, sigla_uf, area_km2_ibge, area_km2_calculada, geometria_valida
            FROM geo.municipios
            WHERE cd_mun = %s;
        """
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql, (str(codigo_ibge),))
                linha = cursor.fetchone()

        if not linha:
            cls.importar_municipio(codigo_ibge)
            return cls.obter_dados_municipio(codigo_ibge)

        return {
            "cd_mun": linha[0],
            "nm_mun": linha[1],
            "sigla_uf": linha[2],
            "area_km2_ibge": float(linha[3]) if linha[3] is not None else None,
            "area_km2_calculada": float(linha[4]) if linha[4] is not None else None,
            "geometria_valida": linha[5],
        }

    @classmethod
    def obter_geojson_limite(cls, codigo_ibge: str = COD_IBGE_PARAUAPEBAS) -> Dict[str, Any]:
        cls.obter_dados_municipio(codigo_ibge)
        sql = """
            SELECT
                cd_mun, nm_mun, sigla_uf, area_km2_ibge, area_km2_calculada,
                ST_AsGeoJSON(geom) AS geojson
            FROM geo.municipios
            WHERE cd_mun = %s;
        """
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql, (str(codigo_ibge),))
                linha = cursor.fetchone()

        if not linha or not linha[5]:
            return {"type": "FeatureCollection", "features": []}

        return {
            "type": "Feature",
            "properties": {
                "cd_mun": linha[0],
                "nm_mun": linha[1],
                "sigla_uf": linha[2],
                "area_km2_ibge": float(linha[3]) if linha[3] is not None else None,
                "area_km2_calculada": float(linha[4]) if linha[4] is not None else None,
            },
            "geometry": json.loads(linha[5]),
        }

    @classmethod
    def obter_resumo_parauapebas(cls) -> Dict[str, Any]:
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'geo' AND table_name = 'processos_parauapebas'
                    );
                """)
                tabela_existe = cursor.fetchone()[0]
                total = 0
                if tabela_existe:
                    cursor.execute("SELECT COUNT(*) FROM geo.processos_parauapebas;")
                    total = cursor.fetchone()[0]

        if not tabela_existe or total == 0:
            cls.recortar_processos_municipio()

        dados_mun = cls.obter_dados_municipio()

        sql = """
            SELECT
                COUNT(*) AS total_processos,
                COALESCE(SUM(area_ha_mun), 0) AS soma_area_ha_mun,
                COALESCE(SUM(area_ha_original), 0) AS soma_area_ha_original,
                ROUND((ST_Area(ST_Transform(ST_UnaryUnion(ST_Collect(geom)), 31982)) / 10000.0)::numeric, 4) AS area_unica_ha,
                COUNT(*) FILTER (WHERE tipo_recorte = 'TOTAL') AS processos_integrais,
                COUNT(*) FILTER (WHERE tipo_recorte = 'PARCIAL') AS processos_parciais,
                COUNT(DISTINCT fase) AS fases_distintas,
                COUNT(DISTINCT substancia) AS substancias_distintas
            FROM geo.processos_parauapebas
            WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom);
        """

        sql_fases = """
            SELECT fase, COUNT(*) AS qtd, ROUND(SUM(area_ha_mun)::numeric, 2) AS area_ha
            FROM geo.processos_parauapebas
            GROUP BY fase
            ORDER BY qtd DESC;
        """

        sql_substancias = """
            SELECT COALESCE(substancia, 'NÃO INFORMADA') AS subs, COUNT(*) AS qtd, ROUND(SUM(area_ha_mun)::numeric, 2) AS area_ha
            FROM geo.processos_parauapebas
            GROUP BY subs
            ORDER BY qtd DESC
            LIMIT 10;
        """

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchone()

                cursor.execute("""
                    SELECT
                        ROUND((ST_Area(ST_Transform(ST_UnaryUnion(ST_Collect(geom)), 31982)) / 10000.0)::numeric, 2),
                        ROUND(COALESCE(SUM(area_ha_original), 0)::numeric, 2)
                    FROM geo.processos_parauapebas
                    WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom);
                """)
                row_area = cursor.fetchone()
                area_unica_ha = float(row_area[0]) if row_area[0] is not None else 0.0
                soma_area_original_ha = float(row_area[1]) if row_area[1] is not None else 0.0

                cursor.execute(sql_fases)
                fases = [
                    {"fase": r[0] or "NÃO INFORMADA", "quantidade": r[1], "area_ha": float(r[2])}
                    for r in cursor.fetchall()
                ]

                cursor.execute(sql_substancias)
                subs = [
                    {"substancia": r[0], "quantidade": r[1], "area_ha": float(r[2])}
                    for r in cursor.fetchall()
                ]

        return {
            "municipio": dados_mun,
            "total_processos": int(res[0]),
            "soma_area_recortada_ha": float(res[1]),
            "area_unica_ha": area_unica_ha,
            "soma_area_original_ha": soma_area_original_ha,
            "area_municipio_ha": 688586.5,
            "processos_integrais": int(res[4]),
            "processos_parciais": int(res[5]),
            "fases_distintas": int(res[6]),
            "substancias_distintas": int(res[7]),
            "distribuicao_fases": fases,
            "principais_substancias": subs,
        }

    @classmethod
    def obter_processos_geojson(
        cls,
        limite: int = 400,
        fase: Optional[str] = None,
        substancia: Optional[str] = None,
        numero: Optional[Any] = None,
        titular: Optional[str] = None,
        termo: Optional[str] = None,
    ) -> Dict[str, Any]:
        condicoes = ["geom IS NOT NULL", "NOT ST_IsEmpty(geom)"]
        params: List[Any] = []

        if fase:
            condicoes.append("fase = %s")
            params.append(fase.strip())

        if substancia:
            condicoes.append("substancia ILIKE %s")
            params.append(f"%{substancia.strip()}%")

        if numero:
            num_clean = str(numero).strip().replace(".", "").replace("/", "").replace("-", "")
            condicoes.append("(CAST(numero AS TEXT) ILIKE %s OR processo ILIKE %s)")
            params.extend([f"%{num_clean}%", f"%{num_clean}%"])

        if titular:
            condicoes.append("nome_titular ILIKE %s")
            params.append(f"%{titular.strip()}%")

        if termo:
            termo_clean = termo.strip()
            condicoes.append(
                "(processo ILIKE %s OR nome_titular ILIKE %s OR substancia ILIKE %s OR fase ILIKE %s)"
            )
            params.extend([f"%{termo_clean}%", f"%{termo_clean}%", f"%{termo_clean}%", f"%{termo_clean}%"])

        where_clause = " AND ".join(condicoes)
        limite_val = max(1, min(int(limite), 500))

        sql = f"""
            SELECT
                id, processo, numero, ano, fase, nome_titular, substancia,
                area_ha_mun, area_ha_original, tipo_recorte,
                ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0001)) AS geojson
            FROM geo.processos_parauapebas
            WHERE {where_clause}
            ORDER BY area_ha_mun DESC
            LIMIT %s;
        """
        params.append(limite_val)

        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql, params)
                linhas = cursor.fetchall()

        features = []
        for r in linhas:
            if not r[10]:
                continue
            features.append({
                "type": "Feature",
                "geometry": json.loads(r[10]),
                "properties": {
                    "id": r[0],
                    "processo": r[1],
                    "numero": r[2],
                    "ano": r[3],
                    "fase": r[4],
                    "nome_titular": r[5],
                    "substancia": r[6],
                    "area_ha_mun": float(r[7]) if r[7] is not None else 0.0,
                    "area_ha_original": float(r[8]) if r[8] is not None else None,
                    "tipo_recorte": r[9],
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
        }
