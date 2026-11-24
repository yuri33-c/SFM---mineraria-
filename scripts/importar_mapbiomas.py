import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from rasterio.mask import mask as rasterio_mask
    from rasterio.warp import transform_geom
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    HAS_RASTERIO = True
except ImportError as e:
    HAS_RASTERIO = False

from app.models.database import obter_conexao
from config import MAPBIOMAS_DIR

LEGENDA_MAPBIOMAS = {
    4001: ("Mineração Industrial - Ouro", "INDUSTRIAL"),
    4002: ("Mineração Industrial - Ferro", "INDUSTRIAL"),
    4003: ("Mineração Industrial - Bauxita", "INDUSTRIAL"),
    4004: ("Mineração Industrial - Cobre", "INDUSTRIAL"),
    4005: ("Mineração Industrial - Manganês", "INDUSTRIAL"),
    4006: ("Mineração Industrial - Nióbio", "INDUSTRIAL"),
    4007: ("Mineração Industrial - Fosfato", "INDUSTRIAL"),
    4008: ("Mineração Industrial - Cromo", "INDUSTRIAL"),
    4009: ("Mineração Industrial - Níquel", "INDUSTRIAL"),
    4010: ("Mineração Industrial - Zinco", "INDUSTRIAL"),
    4011: ("Mineração Industrial - Chumbo", "INDUSTRIAL"),
    4012: ("Mineração Industrial - Estanho", "INDUSTRIAL"),
    4013: ("Mineração Industrial - Titânio", "INDUSTRIAL"),
    4014: ("Mineração Industrial - Nquimbite", "INDUSTRIAL"),
    4015: ("Mineração Industrial - Argila", "INDUSTRIAL"),
    4016: ("Mineração Industrial - Areia/Cascalho", "INDUSTRIAL"),
    4017: ("Mineração Industrial - Calcário", "INDUSTRIAL"),
    4018: ("Mineração Industrial - Carvão", "INDUSTRIAL"),
    4019: ("Mineração Industrial - Diamante", "INDUSTRIAL"),
    4099: ("Mineração Industrial - Outras Substâncias", "INDUSTRIAL"),
    5001: ("Garimpo - Ouro", "GARIMPO"),
    5002: ("Garimpo - Diamante", "GARIMPO"),
    5003: ("Garimpo - Cassiterita", "GARIMPO"),
    5004: ("Garimpo - Coltan", "GARIMPO"),
    5005: ("Garimpo - Areia/Cascalho", "GARIMPO"),
    5006: ("Garimpo - Argila", "GARIMPO"),
    5099: ("Garimpo - Outras Substâncias", "GARIMPO"),
}

def encontrar_geotiff() -> Path:
    pasta = MAPBIOMAS_DIR
    for padrao in ("*.tif", "*.geotiff", "*.TIF"):
        arquivos = sorted(pasta.glob(padrao))
        if arquivos:
            return arquivos[0]
    raise FileNotFoundError(
        f"Nenhum arquivo GeoTIFF encontrado em {pasta}.\n"
        "Execute scripts/exportar_gee.js no Google Earth Engine e deposite o "
        "arquivo exportado em dados/originais/mapbiomas/mapbiomas_mineracao_AAAA.tif"
    )

def rasterizar_e_importar(arquivo_tif: Path):
    if not HAS_RASTERIO:
        print("[ERRO] Dependências geoespaciais (rasterio) não disponíveis.")
        return

    print(f"\nProcessando: {arquivo_tif}")
    ano = "desconhecido"
    for parte in arquivo_tif.stem.split("_"):
        if parte.isdigit() and len(parte) == 4:
            ano = parte
            break

    with obter_conexao() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ST_AsGeoJSON(geom)
                FROM geo.municipios
                WHERE cd_mun = '1505536' LIMIT 1;
            """)
            row = cur.fetchone()
            if not row or not row[0]:
                print("[ERRO] Município 1505536 não encontrado no PostGIS.")
                return
            geom_mun_geojson = json.loads(row[0])

    with rasterio.open(arquivo_tif) as src:
        crs_raster = src.crs
        geom_mun_proj = transform_geom("EPSG:4674", crs_raster.to_string(), geom_mun_geojson)
        out_image, out_transform = rasterio_mask(src, [geom_mun_proj], crop=True, nodata=0)
        dados = out_image[0]
        mascara = dados > 0

        poligonos = []
        for geom_dict, valor in shapes(dados, mask=mascara, transform=out_transform):
            codigo = int(valor)
            if codigo == 0:
                continue
            descricao, tipo = LEGENDA_MAPBIOMAS.get(
                codigo, (f"Código {codigo}", "INDETERMINADO")
            )
            geom_wgs = transform_geom(crs_raster.to_string(), "EPSG:4674", geom_dict)
            poligonos.append({
                "codigo": codigo,
                "descricao": descricao,
                "tipo": tipo,
                "geometry": shape(geom_wgs),
            })

    if not poligonos:
        print("[AVISO] Nenhum pixel de mineração identificado no recorte.")
        return

    gdf = gpd.GeoDataFrame(poligonos, crs="EPSG:4674")
    gdf_utm = gdf.to_crs(epsg=31982)
    gdf["area_ha"] = (gdf_utm.geometry.area / 10000.0).round(4)

    with obter_conexao() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS geo.mapbiomas_mineracao_parauapebas (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    codigo_classe INTEGER NOT NULL,
                    descricao_classe TEXT NOT NULL,
                    tipo_mineracao TEXT NOT NULL,
                    ano VARCHAR(10) NOT NULL,
                    area_ha NUMERIC(14,4) NOT NULL,
                    geom geometry(Geometry, 4674) NOT NULL,
                    processado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                TRUNCATE TABLE geo.mapbiomas_mineracao_parauapebas;
            """)

            sql_insert = """
                INSERT INTO geo.mapbiomas_mineracao_parauapebas
                    (codigo_classe, descricao_classe, tipo_mineracao, ano, area_ha, geom)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4674));
            """
            for _, r in gdf.iterrows():
                cur.execute(sql_insert, (
                    r["codigo"],
                    r["descricao"],
                    r["tipo"],
                    ano,
                    float(r["area_ha"]),
                    json.dumps(mapping(r["geometry"])),
                ))

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_mapbiomas_geom
                ON geo.mapbiomas_mineracao_parauapebas USING GIST (geom);
            """)

    print(f"[SUCESSO] {len(gdf)} polígonos importados em geo.mapbiomas_mineracao_parauapebas.")
    executar_cruzamento_fiscalizacao()

def executar_cruzamento_fiscalizacao():
    print("\nExecutando cruzamento espacial do Tema 10 no PostGIS...")
    with obter_conexao() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS geo.cruzamento_fiscalizacao (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    categoria_tema10 TEXT NOT NULL,
                    descricao_categoria TEXT NOT NULL,
                    processo_id BIGINT,
                    processo_numero TEXT,
                    processo_fase TEXT,
                    processo_titular TEXT,
                    processo_substancia TEXT,
                    tipo_mineracao_mapbiomas TEXT,
                    classe_mapbiomas TEXT,
                    area_ha NUMERIC(14,4) NOT NULL,
                    geom geometry(Geometry, 4674) NOT NULL,
                    processado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                TRUNCATE TABLE geo.cruzamento_fiscalizacao;
            """)

            fases_com_lavra = (
                "'CONCESSÃO DE LAVRA', 'LICENCIAMENTO', 'LAVRA GARIMPEIRA', "
                "'REQUERIMENTO DE LAVRA GARIMPEIRA', 'DIREITO DE REQUERER A LAVRA', "
                "'REGISTRO DE EXTRAÇÃO', 'MANIFESTO DE MINA'"
            )

            sql_cruzamento = f"""
            WITH uniao_titulos AS (
                SELECT ST_UnaryUnion(ST_Collect(geom)) AS geom_titulos
                FROM geo.processos_parauapebas
                WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
            ),
            cat_a AS (
                SELECT
                    'A_FORA_DA_POLIGONAL' AS categoria,
                    'Área minerada fora da poligonal autorizada' AS desc_cat,
                    NULL::BIGINT AS proc_id,
                    NULL::TEXT AS proc_num,
                    NULL::TEXT AS proc_fase,
                    NULL::TEXT AS proc_titular,
                    NULL::TEXT AS proc_subst,
                    m.tipo_mineracao,
                    m.descricao_classe,
                    ROUND((ST_Area(ST_Transform(
                        ST_CollectionExtract(ST_Difference(m.geom, u.geom_titulos), 3),
                        31982
                    )) / 10000.0)::numeric, 4) AS area_ha,
                    ST_Multi(ST_CollectionExtract(ST_Difference(m.geom, u.geom_titulos), 3)) AS geom
                FROM geo.mapbiomas_mineracao_parauapebas m
                CROSS JOIN uniao_titulos u
                WHERE NOT ST_Within(m.geom, u.geom_titulos)
                  AND ST_Difference(m.geom, u.geom_titulos) IS NOT NULL
                  AND NOT ST_IsEmpty(ST_Difference(m.geom, u.geom_titulos))
            ),
            sobreposicoes AS (
                SELECT
                    p.id AS proc_id,
                    p.processo AS proc_num,
                    p.fase AS proc_fase,
                    p.nome_titular AS proc_titular,
                    p.substancia AS proc_subst,
                    m.tipo_mineracao,
                    m.descricao_classe,
                    ST_CollectionExtract(ST_Intersection(m.geom, p.geom), 3) AS geom_intersecao,
                    UPPER(p.fase) IN ({fases_com_lavra}) AS tem_amparo_lavra
                FROM geo.mapbiomas_mineracao_parauapebas m
                JOIN geo.processos_parauapebas p ON ST_Intersects(m.geom, p.geom)
            ),
            cat_b AS (
                SELECT
                    'B_INCOMPATIBILIDADE_FASE' AS categoria,
                    'Mineração sobre processo sem amparo de lavra' AS desc_cat,
                    proc_id, proc_num, proc_fase, proc_titular, proc_subst,
                    tipo_mineracao, descricao_classe,
                    ROUND((ST_Area(ST_Transform(geom_intersecao, 31982)) / 10000.0)::numeric, 4) AS area_ha,
                    ST_Multi(geom_intersecao) AS geom
                FROM sobreposicoes
                WHERE NOT tem_amparo_lavra
                  AND geom_intersecao IS NOT NULL
                  AND NOT ST_IsEmpty(geom_intersecao)
            ),
            cat_conforme AS (
                SELECT
                    'CONFORME_TITULO_VALIDO' AS categoria,
                    'Mineração sobre processo com amparo de lavra' AS desc_cat,
                    proc_id, proc_num, proc_fase, proc_titular, proc_subst,
                    tipo_mineracao, descricao_classe,
                    ROUND((ST_Area(ST_Transform(geom_intersecao, 31982)) / 10000.0)::numeric, 4) AS area_ha,
                    ST_Multi(geom_intersecao) AS geom
                FROM sobreposicoes
                WHERE tem_amparo_lavra
                  AND geom_intersecao IS NOT NULL
                  AND NOT ST_IsEmpty(geom_intersecao)
            )
            INSERT INTO geo.cruzamento_fiscalizacao (
                categoria_tema10, descricao_categoria, processo_id, processo_numero,
                processo_fase, processo_titular, processo_substancia,
                tipo_mineracao_mapbiomas, classe_mapbiomas, area_ha, geom
            )
            SELECT * FROM cat_a WHERE area_ha > 0.01
            UNION ALL
            SELECT * FROM cat_b WHERE area_ha > 0.01
            UNION ALL
            SELECT * FROM cat_conforme WHERE area_ha > 0.01;
            """
            cur.execute(sql_cruzamento)

            cur.execute("""
                SELECT categoria_tema10, COUNT(*), ROUND(SUM(area_ha)::numeric, 2)
                FROM geo.cruzamento_fiscalizacao
                GROUP BY categoria_tema10;
            """)
            print("\nRESULTADOS DO CRUZAMENTO ESPACIAL:")
            for cat, cnt, area in cur.fetchall():
                print(f"  {cat}: {cnt} polígonos ({area} ha)")

def main():
    print("=" * 65)
    print("  IMPORTADOR MAPBIOMAS COLEÇÃO 11 — TEMA 10")
    print("=" * 65)
    try:
        arquivo_tif = encontrar_geotiff()
        rasterizar_e_importar(arquivo_tif)
    except FileNotFoundError as e:
        print(f"\n[STATUS: AGUARDANDO DADOS]\n{e}")

if __name__ == "__main__":
    main()
