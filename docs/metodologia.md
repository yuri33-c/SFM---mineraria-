# Metodologia Técnica e Espacial — Tema 10

## 1. Identificação do Tema e Área de Estudo

* **Tema:** Tema 10 — Fiscalização de lavra fora da poligonal autorizada.
* **Município-alvo:** Parauapebas, Estado do Pará.
* **Código IBGE:** `1505536`.
* **Área Territorial Oficial:** 6.885,865 km² (688.586,5 hectares), conforme Malha Municipal 2025 do IBGE.
* **Sistemas de Coordenadas:**
  * **Armazenamento e exibição:** SIRGAS 2000 geodésico (`EPSG:4674`).
  * **Cálculos métricos e recortes:** SIRGAS 2000 / UTM zone 22S (`EPSG:31982`).

---

## 2. Bases de Dados Oficiais

### 2.1 Agência Nacional de Mineração (ANM / SIGMINE)
* **Base:** Base de Processos Minerários do Estado do Pará (`PA.shp`).
* **Volume:** 24.445 processos cadastrados no estado.
* **Atributos principais:** Número do processo, ano, fase administrativa, nome do titular, substância mineral outorgada, área titulada e uso.
* **Integridade:** 24.445 geometrias válidas (incluindo 56 geometrias originalmente corrompidas que foram corrigidas via algoritmo `make_valid` e persistidas no PostGIS).

### 2.2 Instituto Brasileiro de Geografia e Estatística (IBGE)
* **Base:** Malha Municipal 2025 (`PA_Municipios_2025.shp`).
* **Delimitação de Parauapebas:** Limite político-administrativo oficial utilizado como máscara de interseção territorial.

### 2.3 MapBiomas Coleção 11 — Substância Minerada
* **Produto:** Mapeamento anual de cicatrizes de mineração por sensoriamento remoto (Landsat/Sentinel).
* **Asset GEE:** `projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_mining_substances_v1`.
* **Metodologia de integração:** O script `scripts/exportar_gee.js` exporta o GeoTIFF recortado por Parauapebas. O script `scripts/importar_mapbiomas.py` vetoriza os pixels com valor superior a 0 e armazena os polígonos em `geo.mapbiomas_mineracao_parauapebas`.
* **Critério de transparência acadêmica:** Na ausência do GeoTIFF baixado, o sistema não inventa dados e exibe explicitamente o status `"Aguardando Dados"`.

---

## 3. Conceituação Métrica e Territorial de Áreas

O sistema faz distinção rigorosa entre três grandezas de área, evitando erros conceituais comuns:

1. **Soma das Áreas Originais dos Processos (946.425,24 ha)**:
   Soma das áreas integrais concedidas pela ANM aos processos que interceptam o município, independentemente de estarem totalmente ou parcialmente dentro de Parauapebas.
2. **Soma das Áreas Recortadas (547.751,92 ha)**:
   Soma matemática da área resultante do recorte de cada um dos 349 processos pelo limite municipal. Esse valor inclui áreas de sobreposição entre títulos de fases diferentes.
3. **Área Territorial Única Ocupada por Títulos (431.912,08 ha)**:
   Área geográfica resultante da união topológica (`ST_UnaryUnion`) de todos os polígonos sobre Parauapebas, eliminando duplicações e sobreposições. Representa **62,72%** da área total do município.

$$\text{Cobertura Territorial (\%)} = \frac{\text{Área Única sem Sobreposição (ha)}}{\text{Área Oficial do Município (ha)}} \times 100 = \frac{431.912,08}{688.586,50} \times 100 \approx 62,72\%$$

---

## 4. Classificação Técnica de Fiscalização (Tema 10)

O cruzamento entre cicatrizes de mineração detectadas por sensoriamento remoto e os títulos cadastrados gera três categorias de análise:

### Categoria A — Área minerada fora da poligonal autorizada
* **Definição:** Atividade de extração mapeada por satélite situada fora de qualquer poligonal de processo minerário cadastrado na ANM.
* **Operador espacial:** `ST_Difference(mapbiomas.geom, ST_UnaryUnion(processos.geom))`.

### Categoria B — Incompatibilidade de fase administrativa
* **Definição:** Mineração detectada sobre poligonal de processo cadastrado, mas cuja fase administrativa normativa não concede amparo para lavra ou extração mineral (por exemplo: *Requerimento de Pesquisa* ou *Autorização de Pesquisa*).
* **Fases com amparo legal para lavra consideradas pelo sistema:**
  * Concessão de Lavra
  * Licenciamento
  * Lavra Garimpeira
  * Requerimento de Lavra Garimpeira
  * Direito de Requerer a Lavra
  * Registro de Extração
  * Manifesto de Mina

### Categoria C — Mineração sem título identificado
* **Definição:** Mineração identificada em terras públicas, áreas de preservação ou áreas devolutas sem qualquer solicitação formal registrada no SIGMINE.

---

## 5. Critério Prudencial de Fiscalização

Os resultados gerados pela análise espacial são caracterizados como **indícios técnicos** de possíveis desconformidades. O sistema não declara automaticamente ilicitude ou infração jurídica, servindo como ferramenta de suporte à decisão para os órgãos fiscalizadores (ANM, IBAMA, Polícia Federal e Secretaria Estadual de Meio Ambiente).
