# Dicionário de Dados do Sistema (SFM)

Este documento detalha o modelo de dados relacional e geoespacial implementado no **PostgreSQL 18** com a extensão **PostGIS 3.7**, sob o schema `geo`.

---

## 1. Tabela: `geo.municipios`

Armazena os limites territoriais dos municípios de interesse da análise (área de estudo: Parauapebas/PA).

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | NÃO | Identificador sequencial único (Primary Key) |
| `cd_mun` | VARCHAR(10) | NÃO | Código numérico oficial do IBGE (Unique Key) |
| `nm_mun` | TEXT | NÃO | Nome do município (ex.: 'Parauapebas') |
| `sigla_uf` | VARCHAR(2) | NÃO | Sigla da Unidade Federativa ('PA') |
| `area_km2_ibge` | NUMERIC(14,4) | SIM | Área territorial informada pelo IBGE em km² |
| `area_km2_calculada` | NUMERIC(14,4) | SIM | Área calculada em projeção UTM Zone 22S em km² |
| `geom` | geometry(Geometry, 4674) | NÃO | Polígono geográfico em SIRGAS 2000 (Índice GiST) |
| `geometria_valida` | BOOLEAN | NÃO | Indicador de validade topológica original da geometria |
| `importado_em` | TIMESTAMPTZ | NÃO | Carimbo de data/hora de importação |

---

## 2. Tabela: `geo.processos_minerarios`

Armazena a base cadastral de processos minerários da ANM/SIGMINE para todo o Estado do Pará.

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | NÃO | Identificador sequencial único (Primary Key) |
| `id_anm` | TEXT | SIM | Identificador alfanumérico interno da ANM |
| `processo` | TEXT | SIM | Código formatado do processo (ex.: '850.123/2010') |
| `numero` | BIGINT | SIM | Número sequencial do processo na ANM |
| `ano` | SMALLINT | SIM | Ano de autuação do processo mineral |
| `area_ha` | NUMERIC(18,4) | SIM | Área do título informada pela ANM em hectares |
| `fase` | TEXT | SIM | Fase administrativa da ANM (ex.: 'CONCESSÃO DE LAVRA') |
| `ultimo_evento` | TEXT | SIM | Descrição do último evento formal protocolado |
| `nome_titular` | TEXT | SIM | Nome ou razão social do titular outorgado |
| `substancia` | TEXT | SIM | Nome da substância mineral autorizada |
| `uso` | TEXT | SIM | Uso mineral previsto |
| `uf` | TEXT | SIM | Sigla da Unidade da Federação |
| `ds_processo` | TEXT | SIM | Descrição complementar do processo |
| `geom` | geometry(Geometry, 4674) | NÃO | Poligonal delimitadora do processo em SIRGAS 2000 |
| `geometria_valida` | BOOLEAN | NÃO | Se a geometria original estava válida |
| `geometria_corrigida` | BOOLEAN | NÃO | Se a geometria passou por correção topológica |
| `origem_arquivo` | TEXT | NÃO | Nome do arquivo de origem (ex.: 'PA.shp') |
| `importado_em` | TIMESTAMPTZ | NÃO | Data e hora de importação |

**Índices**: `idx_processos_geom` (GIST), `idx_processos_fase` (B-Tree), `idx_processos_processo` (B-Tree).

---

## 3. Tabela: `geo.processos_parauapebas`

Armazena o recorte territorial espacial dos processos que incidem sobre o município de Parauapebas.

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | NÃO | Identificador sequencial do recorte (Primary Key) |
| `processo_origem_id` | BIGINT | SIM | Chave estrangeira para `geo.processos_minerarios(id)` |
| `processo` | TEXT | SIM | Código do processo minerário |
| `numero` | BIGINT | SIM | Número do processo |
| `ano` | SMALLINT | SIM | Ano do processo |
| `area_ha_original` | NUMERIC(18,4) | SIM | Área original total do processo em hectares |
| `area_ha_mun` | NUMERIC(18,4) | NÃO | Área do polígono estritamente dentro de Parauapebas (ha) |
| `fase` | TEXT | SIM | Fase administrativa ANM |
| `ultimo_evento` | TEXT | SIM | Último evento do processo |
| `nome_titular` | TEXT | SIM | Razão social do titular |
| `substancia` | TEXT | SIM | Substância mineral |
| `uso` | TEXT | SIM | Uso mineral |
| `uf` | TEXT | SIM | UF do processo |
| `ds_processo` | TEXT | SIM | Descrição do processo |
| `tipo_recorte` | TEXT | NÃO | `'TOTAL'` (100% dentro) ou `'PARCIAL'` (intercepta limite) |
| `geom` | geometry(Geometry, 4674) | NÃO | Polígono recortado no limite de Parauapebas |
| `processado_em` | TIMESTAMPTZ | NÃO | Carimbo de data/hora do recorte |

**Índices**: `idx_processos_parauapebas_geom` (GIST), `idx_processos_parauapebas_fase`, `idx_processos_parauapebas_processo`.

---

## 4. Tabela: `geo.mapbiomas_mineracao_parauapebas`

Armazena os polígonos de mineração vetorizados a partir do raster da Coleção 11 do MapBiomas.

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | NÃO | Chave primária sequencial |
| `codigo_classe` | INTEGER | NÃO | Código numérico da classe MapBiomas (ex.: 4002 = Ferro) |
| `descricao_classe` | TEXT | NÃO | Descrição textual da classe |
| `tipo_mineracao` | TEXT | NÃO | `'INDUSTRIAL'` ou `'GARIMPO'` |
| `ano` | VARCHAR(10) | NÃO | Ano do mapeamento |
| `area_ha` | NUMERIC(14,4) | NÃO | Área do polígono em hectares calculada em UTM 22S |
| `geom` | geometry(Geometry, 4674) | NÃO | Geometria do polígono de mineração detectado |
| `processado_em` | TIMESTAMPTZ | SIM | Data e hora de processamento |

---

## 5. Tabela: `geo.cruzamento_fiscalizacao`

Armazena o resultado da interseção e diferença espacial entre MapBiomas e processos minerários (Tema 10).

| Coluna | Tipo | Nulo? | Descrição |
| :--- | :--- | :--- | :--- |
| `id` | BIGINT | NÃO | Chave primária sequencial |
| `categoria_tema10` | TEXT | NÃO | Categoria: `'A_FORA_DA_POLIGONAL'`, `'B_INCOMPATIBILIDADE_FASE'` ou `'CONFORME_TITULO_VALIDO'` |
| `descricao_categoria` | TEXT | NÃO | Descrição do indício técnico apurado |
| `processo_id` | BIGINT | SIM | ID do processo minerário correspondente (se houver) |
| `processo_numero` | TEXT | SIM | Número do processo minerário |
| `processo_fase` | TEXT | SIM | Fase administrativa do processo |
| `processo_titular` | TEXT | SIM | Titular do processo |
| `processo_substancia` | TEXT | SIM | Substância mineral do processo |
| `tipo_mineracao_mapbiomas` | TEXT | SIM | Tipo de mineração (`INDUSTRIAL` ou `GARIMPO`) |
| `classe_mapbiomas` | TEXT | SIM | Classe da substância mapeada pelo satélite |
| `area_ha` | NUMERIC(14,4) | NÃO | Área da poligonal resultante em hectares |
| `geom` | geometry(Geometry, 4674) | NÃO | Geometria vetorial da ocorrência |
| `processado_em` | TIMESTAMPTZ | SIM | Data e hora do processamento do cruzamento |
