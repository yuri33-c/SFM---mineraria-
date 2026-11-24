CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS geo;

CREATE TABLE IF NOT EXISTS geo.municipios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cd_mun VARCHAR(10) NOT NULL UNIQUE,
    nm_mun TEXT NOT NULL,
    sigla_uf VARCHAR(2) NOT NULL,
    area_km2_ibge NUMERIC(14,4),
    area_km2_calculada NUMERIC(14,4),
    geom geometry(Geometry, 4674) NOT NULL,
    geometria_valida BOOLEAN NOT NULL,
    importado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_municipios_geom
ON geo.municipios USING GIST (geom);

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
    geom geometry(Geometry, 4674) NOT NULL,
    geometria_valida BOOLEAN NOT NULL,
    geometria_corrigida BOOLEAN NOT NULL DEFAULT FALSE,
    origem_arquivo TEXT NOT NULL,
    importado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processos_geom
ON geo.processos_minerarios USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_processos_fase
ON geo.processos_minerarios (fase);

CREATE INDEX IF NOT EXISTS idx_processos_processo
ON geo.processos_minerarios (processo);

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
    geom geometry(Geometry, 4674) NOT NULL,
    processado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_geom
ON geo.processos_parauapebas USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_fase
ON geo.processos_parauapebas (fase);

CREATE INDEX IF NOT EXISTS idx_processos_parauapebas_processo
ON geo.processos_parauapebas (processo);

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

CREATE INDEX IF NOT EXISTS idx_mapbiomas_geom
ON geo.mapbiomas_mineracao_parauapebas USING GIST (geom);

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

CREATE INDEX IF NOT EXISTS idx_cruzamento_geom
ON geo.cruzamento_fiscalizacao USING GIST (geom);
