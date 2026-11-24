# Arquitetura do Sistema — SFM (Sistema de Fiscalização Minerária)

## 1. Visão Geral da Arquitetura

O **Sistema de Fiscalização Minerária (SFM)** foi projetado seguindo rigorosamente o padrão de arquitetura de software **MVC (Model-View-Controller)**, implementado em **Python 3.13 puro**, sem acoplamento a frameworks web monolíticos (como Django) ou microframeworks (como Flask ou FastAPI). Essa escolha técnica garante:

1. **Transparência total de execução**: Todas as camadas de roteamento, serialização, validação e resposta HTTP são controladas diretamente no código-fonte.
2. **Desempenho e leveza**: Baixo consumo de memória e inicialização instantânea.
3. **Padrão WSGI interoperável**: Compatibilidade nativa com servidores de produção em conformidade com a PEP 3333 (como Waitress e Gunicorn).

```
                      +-----------------------------+
                      |   Cliente (Navegador Web)   |
                      +--------------+--------------+
                                     |  HTTP(S)
                                     v
                      +-----------------------------+
                      | Proxy Reverso (Caddy/Nginx) |
                      +--------------+--------------+
                                     |  WSGI (127.0.0.1:8000)
                                     v
                      +-----------------------------+
                      |    Servidor WSGI (Waitress)  |
                      |          ou main.py         |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
               v                     v                     v
      +-----------------+   +-----------------+   +-----------------+
      |   CONTROLLER    |   |      VIEW       |   |      MODEL      |
      |                 |   |                 |   |                 |
      | - HomeCtrl      |   | - index.html    |   | - Database      |
      | - ProcessoCtrl  |   | - apresentacao  |   | - ProcessoMiner |
      | - StatusCtrl    |   | - CSS / JS      |   | - Municipio     |
      | - Validações    |   | - Leaflet Map   |   | - Status        |
      +--------+--------+   +-----------------+   +--------+--------+
               |                                           |
               +---------------------+---------------------+
                                     |  Psycopg 3 (Pool/Conexão)
                                     v
                      +-----------------------------+
                      |  PostgreSQL 18 / PostGIS 3  |
                      |   Schema: geo (EPSG:4674)   |
                      +-----------------------------+
```

---

## 2. Camada Model (`app/models/`)

A camada Model encapsula todas as entidades de negócio, regras de integridade territorial, persistência e processamento espacial com PostGIS.

* **`database.py`**: Gerenciador de conexões transacionais com PostgreSQL via `psycopg`. Lê variáveis protegidas de `.env` e impõe limites de tempo de conexão (`connect_timeout`).
* **`municipio.py`**: Gerencia o limite territorial de Parauapebas (`geo.municipios`), o recorte espacial dos processos minerários (`geo.processos_parauapebas`) em projeção métrica UTM Zone 22S (`EPSG:31982`) e cálculos topológicos de união (`ST_UnaryUnion`).
* **`processo_minerario.py`**: Gerencia a base estadual ANM (`geo.processos_minerarios`), consultas filtradas, paginação com ordenação por allowlist e a metodologia de fiscalização do Tema 10.
* **`status.py`**: Módulo de auditoria e diagnóstico em tempo real das tabelas do PostGIS, extensões e integridade dos arquivos do MapBiomas.

**Princípio**: O Model não gera HTML, não manipula requisições HTTP e nunca acessa a View.

---

## 3. Camada View (`app/views/`)

A View é composta exclusivamente por arquivos estáticos e templates HTML estruturados:

* **`apresentacao.html`**: Página institucional acadêmica que contextualiza o projeto, os objetivos de pesquisa e a fundamentação do Tema 10.
* **`index.html`**: Ambiente operacional do sistema contendo cards de indicadores (KPIs), mapa cartográfico territorial interativo com Leaflet e OpenStreetMap, painel de busca com filtros recolhíveis e tabela paginada com link direto aos polígonos.
* **`static/css/style.css`**: Folha de estilo profissional sóbria, responsiva e com tema escuro institucional acadêmico.
* **`static/js/app.js`**: JavaScript ES6 puro, sem frameworks pesados, com requisições assíncronas `fetch`, debounce de digitação (350ms), criação segura de nós DOM contra XSS e integração ao Leaflet.

**Princípio**: A View nunca executa SQL e nunca comunica com o banco diretamente.

---

## 4. Camada Controller (`app/controllers/`)

O Controller atua como mediador entre a recepção de requisições e a invocação dos modelos:

* **`home_controller.py`**: Entrega os templates HTML das páginas inicial e operacional.
* **`processo_controller.py`**: Valida todos os parâmetros de busca (tipo de dado, limites máximos entre 1 e 500, higienização de strings), aciona o Model correspondente e formata os dados para entrega JSON ou GeoJSON.
* **`status_controller.py`**: Intermedia o diagnóstico de saúde do banco de dados e do PostGIS.

**Princípio**: O Controller não monta SQL e não renderiza layouts visuais diretamente.

---

## 5. Roteamento e Padrão WSGI (`main.py`)

A aplicação disponibiliza duas formas de execução integradas:

1. **Servidor HTTP Nativo (`ThreadingHTTPServer`)**: Ideal para desenvolvimento local e testes rápidos.
2. **Interface WSGI Pura (`application(environ, start_response)`)**: Permite que o servidor de produção **Waitress** execute a aplicação em modo multithread com alto throughput e baixo consumo de memória, sem qualquer framework web intermediário.
