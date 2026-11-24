# Sistema de Fiscalização Minerária (SFM)
### Tema 10 — Fiscalização de lavra fora da poligonal autorizada
**Estudo de Caso Territorial:** Município de Parauapebas, Pará (Código IBGE: 1505536)

---

## 1. Apresentação do Projeto

O **Sistema de Fiscalização Minerária (SFM)** é uma aplicação de geoprocessamento e inteligência territorial desenvolvida para identificar, qualificar e espacializar indícios técnicos de desconformidades na atividade mineral.

O sistema cruza dados vetoriais oficiais dos títulos minerários outorgados pela **Agência Nacional de Mineração (ANM / SIGMINE)** com o mapeamento anual de cicatrizes de mineração gerado por sensoriamento remoto pelo **MapBiomas (Coleção 11 — Substância Minerada)**, tendo como limite geográfico o município de **Parauapebas/PA** (Malha Municipal 2025 do **IBGE**).

> **Critério Prudencial Acadêmico:** As análises espaciais produzem **indícios técnicos objetivos** de desconformidade territorial e administrativa. O sistema não declara automaticamente ilicitude jurídica, servindo como instrumento preliminar de triagem e inteligência territorial para fiscalização presencial.

---

## 2. Tecnologias Utilizadas

A arquitetura do SFM foi construída sob o princípio de **independência de frameworks web**, utilizando bibliotecas geoespaciais e de banco de dados consolidadas no ecossistema Python:

* **Linguagem:** Python 3.13.15 (sem uso de Flask, Django, FastAPI ou Laravel).
* **Padrão Arquitetural:** MVC (Model-View-Controller) estrito.
* **Banco de Dados Relacional e Geográfico:** PostgreSQL 18 + PostGIS 3.7.0.
* **Driver de Banco:** Psycopg 3.3.9 (com conexões parametrizadas).
* **Manipulação Vetorial e Matricial:** GeoPandas 1.2.0, Shapely 2.2.0, PyProj 3.8.0, Pyogrio 0.13.0, Rasterio 1.5.2, NumPy 2.5.5, Pandas 3.1.1.
* **Servidor de Produção:** Waitress 3.0.2 (servidor WSGI multithread puro em conformidade com a PEP 3333).
* **Interface do Usuário (Frontend):** HTML5 semântico, CSS3 sob medida e JavaScript puro (ES6+ assíncrono).
* **Visualização Cartográfica:** Leaflet 1.9.4 com mapa-base oficial OpenStreetMap (sem tokens externos).

---

## 3. Estrutura de Pastas do Projeto

```
fiscalizacao_mineraria/
│
├── app/
│   ├── models/                         # Camada Model (PostGIS, SQL, Regras de Negócio)
│   │   ├── database.py                 # Conexão transacional centralizada com PostgreSQL
│   │   ├── municipio.py                # Gestão territorial de Parauapebas e recorte espacial
│   │   ├── processo_minerario.py       # Consultas, filtros e metodologia analítica do Tema 10
│   │   └── status.py                   # Diagnóstico de integridade do banco e MapBiomas
│   │
│   ├── views/                          # Camada View (Interface, Templates e Estáticos)
│   │   ├── apresentacao.html           # Página institucional acadêmica do projeto
│   │   ├── index.html                  # Ambiente operacional interativo
│   │   └── static/
│   │       ├── css/style.css           # Estilo visual institucional escuro
│   │       ├── js/app.js               # Frontend JavaScript seguro e assíncrono
│   │       └── images/                 # Recursos gráficos institucionais
│   │
│   └── controllers/                    # Camada Controller (Roteamento e Validação)
│       ├── home_controller.py          # Entrega de páginas HTML
│       ├── processo_controller.py      # Validação e processamento de consultas
│       └── status_controller.py        # Intermediação de diagnóstico de saúde
│
├── dados/                              # Dados Geográficos Oficiais
│   ├── originais/
│   │   ├── anm/                        # Base estadual SIGMINE Pará (PA.shp)
│   │   ├── ibge/                       # Malha municipal 2025 (PA_Municipios_2025.shp)
│   │   └── mapbiomas/                  # Diretório para GeoTIFF da Coleção 11
│   └── processados/                    # Produtos intermediários vetorizados
│
├── resultados/                         # Saídas do Sistema
│   ├── mapas/                          # Mapas temáticos exportados
│   ├── relatorios/                     # Relatórios sintéticos e analíticos
│   └── exportacoes/                    # Arquivos GeoJSON e CSV gerados
│
├── docs/                               # Documentação Técnica e Acadêmica
│   ├── arquitetura.md                  # Especificação do padrão MVC e ciclo de vida
│   ├── metodologia.md                  # Metodologia espacial do Tema 10 e grandezas de área
│   ├── dicionario_dados.md             # Dicionário completo das tabelas e índices PostGIS
│   ├── seguranca.md                    # Política de segurança (OWASP Top 10)
│   └── implantacao.md                  # Guia de implantação em produção (Linux/Windows)
│
├── migrations/
│   └── 001_schema_inicial.sql          # DDL completo das tabelas e índices espaciais
│
├── tests/                              # Suite de Testes Automatizados
│   ├── test_imports_e_mvc.py           # Teste de integridade de módulos e diretórios
│   ├── test_models_e_geoprocessamento.py # Teste de consultas, cálculos de área e GeoJSON
│   ├── test_seguranca_e_http.py        # Testes de SQLi, XSS, Path Traversal e Headers
│   ├── test_producao_wsgi.py           # Teste da interface WSGI e endpoints
│   └── executar_todos_testes.py        # Runner consolidado da suite de testes
│
├── scripts/                            # Scripts de Manutenção e Geoprocessamento
│   ├── exportar_gee.js                 # Script para extração do raster no Google Earth Engine
│   └── importar_mapbiomas.py           # Vetorização e cruzamento espacial do Tema 10
│
├── deploy/                             # Configurações de Publicação e Produção
│   ├── servidor_producao.py            # Inicializador do servidor WSGI Waitress
│   ├── Caddyfile                       # Configuração de Proxy Reverso com HTTPS automático
│   ├── nginx.conf                      # Configuração para Nginx + Certbot
│   └── sfm.service                     # Arquivo de serviço para o systemd (Linux)
│
├── .venv/                              # Ambiente virtual Python (ignorado no Git)
├── .env                                # Variáveis de ambiente sensíveis (ignorado no Git)
├── .env.example                        # Modelo de configuração sem credenciais
├── .gitignore                          # Regras estritas de exclusão do Git
├── config.py                           # Parâmetros centrais, caminhos e segurança
├── main.py                             # Servidor HTTP nativo e aplicação WSGI pura
├── requirements.txt                    # Dependências com versões estritamente fixadas
└── README.md                           # Documentação principal
```

---

## 4. Estado Atual da Base de Dados

Conforme auditado no PostgreSQL 18 / PostGIS 3.7.0:

* **`geo.processos_minerarios`:** **24.445** processos minerários do Pará cadastrados.
* **`geo.municipios`:** Município de Parauapebas importado (Código IBGE `1505536`), com área oficial de **6.885,865 km²** (688.586,5 hectares).
* **`geo.processos_parauapebas`:** **349** processos com incidência territorial sobre o município.

### Métricas de Área em Parauapebas
* **Soma das áreas recortadas:** `547.751,92 ha` (inclui áreas de sobreposição entre títulos de fases distintas).
* **Área territorial única titulada (`ST_UnaryUnion`):** `431.912,08 ha` (**62,72%** do município coberto por processos).
* **Soma das áreas originais ANM:** `946.425,24 ha`.

---

## 5. Metodologia do Tema 10 (Fiscalização de Lavra)

O sistema classifica indícios de possíveis irregularidades em três categorias:

1. **Categoria A — Área minerada fora da poligonal autorizada:** Mineração detectada por satélite sem correspondência espacial com qualquer título minerário cadastrado na ANM.
2. **Categoria B — Incompatibilidade de fase administrativa:** Atividade minerária situada sobre processo em fase preliminar sem amparo legal de extração (ex.: *Autorização de Pesquisa* ou *Requerimento de Pesquisa*).
3. **Categoria C — Mineração sem título identificado:** Atividade minerária em áreas públicas ou devolutas sem nenhum registro formal no SIGMINE.

---

## 6. Mecanismos de Segurança Implementados

* **SQL Injection:** Consultas 100% parametrizadas via `psycopg 3`, com allowlist estrita para ordenação dinâmica (`COLUNAS_ORDENACAO_PERMITIDAS`).
* **Cross-Site Scripting (XSS):** Construção segura de nós DOM via `textContent` e `document.createElement()` no JavaScript, com popups do Leaflet devidamente higienizados.
* **Path Traversal:** Verificação de caminho canônico com `is_relative_to()` impedindo o acesso a qualquer arquivo fora de `app/views/static/`.
* **Cabeçalhos de Segurança:** Aplicação sistemática de `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` e `Permissions-Policy`.
* **Rate Limiting:** Controle em memória por IP (120 req/minuto) retornando HTTP 429 em caso de abuso.
* **Validação de Host:** Rejeição de requisições com cabeçalho `Host` não cadastrado em `ALLOWED_HOSTS`.
* **Auditoria de Vulnerabilidades:** Execução de `pip-audit` sem nenhuma vulnerabilidade encontrada nas dependências.

---

## 7. Como Executar a Aplicação

### 7.1 Requisitos Prévios
* Windows 11 ou Linux (Ubuntu/Debian).
* Python 3.13.15.
* PostgreSQL 18 com extensão PostGIS 3.7.0 instalada e rodando localmente.

### 7.2 Instalação das Dependências
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 7.3 Execução em Modo de Desenvolvimento
Inicia o servidor HTTP nativo multithread na porta 8000:
```powershell
.\.venv\Scripts\python.exe main.py
```
* **Apresentação Institucional:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Ambiente Operacional do Sistema:** [http://127.0.0.1:8000/sistema](http://127.0.0.1:8000/sistema)

### 7.4 Execução em Modo de Produção (Waitress WSGI)
Inicia o servidor WSGI de alto desempenho sem nenhum framework web:
```powershell
.\.venv\Scripts\python.exe deploy/servidor_producao.py
```

### 7.5 Execução dos Testes Automatizados
Executa a suite completa com 23 testes unitários, espaciais, de segurança e de integração:
```powershell
.\.venv\Scripts\python.exe tests/executar_todos_testes.py
```

---

## 8. Integração com o MapBiomas Coleção 11

Caso deseje executar o cruzamento espacial com os dados do satélite:

1. Acesse o **Google Earth Engine Code Editor** ([https://code.earthengine.google.com](https://code.earthengine.google.com)).
2. Copie e execute o conteúdo do script `scripts/exportar_gee.js`.
3. Faça o download do arquivo GeoTIFF gerado no Google Drive (`mapbiomas_mineracao_2023.tif`).
4. Deposite o arquivo em `dados/originais/mapbiomas/`.
5. Execute o processador automatizado:
   ```powershell
   .\.venv\Scripts\python.exe scripts/importar_mapbiomas.py
   ```
6. O sistema atualizará os dados da análise automaticamente no painel e na rota `/api/fiscalizacao/analise`.

---

## 9. Licença e Responsabilidade Técnica

Projeto desenvolvido para fins acadêmicos e de pesquisa técnico-científica no âmbito do **Tema 10 (Fiscalização de lavra fora da poligonal autorizada)**.
Fontes primárias: Agência Nacional de Mineração (ANM) e Instituto Brasileiro de Geografia e Estatística (IBGE).
