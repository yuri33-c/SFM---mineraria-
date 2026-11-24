# Política e Mecanismos de Segurança — SFM

Este documento detalha os princípios de defesa em profundidade e as proteções de segurança implementadas no Sistema de Fiscalização Minerária, alinhadas aos padrões **OWASP Top 10**.

---

## 1. Proteção de Credenciais e Segredos

* **Isolamento de Credenciais:** As credenciais do banco de dados residem exclusivamente no arquivo `.env`, localizado na raiz do projeto e explicitamente bloqueado no `.gitignore`.
* **Proibição de Servir Arquivos de Configuração:** O servidor web não possui nenhuma rota que permita a leitura ou download do `.env`, arquivos `.py`, scripts ou dados brutos.
* **Validação de Inicialização:** A função `validar_configuracao()` em `config.py` impede que a aplicação suba em modo de produção (`SFM_ENV=production`) caso variáveis essenciais como `DB_PASSWORD`, `DB_USER` ou `DB_HOST` estejam ausentes.
* **Template Seguro:** O repositório versiona unicamente o `.env.example`, contendo valores fictícios para orientar novas instalações.

---

## 2. Prevenção Contra Injeção de SQL (SQL Injection)

* **Consultas 100% Parametrizadas:** Nenhuma entrada de usuário é concatenada em cláusulas SQL. Todas as pesquisas por termo, fase, titular, substância e paginação utilizam marcadores `%s` processados com segurança pelo driver `psycopg 3`.
* **Allowlist para Ordenação:** Ordenações dinâmicas passam obrigatoriamente por um dicionário fechado de colunas autorizadas (`COLUNAS_ORDENACAO_PERMITIDAS`). Se o cliente enviar um nome de coluna malicioso, a consulta retrocede automaticamente para o padrão seguro `area_ha_mun`.
* **Validação e Limitação de Intervalo:** Os parâmetros numéricos de paginação (`limite` e `offset`) são convertidos para inteiros e limitados (`min(limite, 500)`), impedindo que consultas abusivas esgotem a memória do banco de dados.

---

## 3. Prevenção Contra Cross-Site Scripting (XSS)

* **Construção Segura do DOM:** O JavaScript (`app.js`) prioriza o uso de `textContent` e `document.createElement()` para renderizar nomes de titulares, processos, substâncias e áreas na tabela.
* **Popups Cartográficos Seguros:** Os popups gerados para as poligonais do Leaflet utilizam nós DOM criados programaticamente com valores anexados via `document.createTextNode()`, neutralizando qualquer injeção de tags HTML maliciosas vindas de atributos cadastrais.
* **Função de Escape:** Funções utilitárias como `escaparHtml()` garantem que eventuais renderizações dinâmicas sejam devidamente sanitizadas.

---

## 4. Prevenção Contra Directory Traversal (Path Traversal)

* **Verificação de Prefixo Canônico:** A entrega de arquivos estáticos (`/static/...`) utiliza resolução canônica via `Path.resolve()`. O caminho resultante é validado estritamente com `arquivo_estatico.is_relative_to(diretorio_estatico)`.
* **Bloqueio de Saída de Diretório:** Requisições forjadas com sequências como `/static/../../.env` ou `/static/../../../config.py` recebem automaticamente o código HTTP `403 Forbidden`, impedindo o vazamento de arquivos internos do projeto.

---

## 5. Cabeçalhos HTTP de Segurança

Todas as respostas HTTP do servidor aplicam os seguintes cabeçalhos de proteção:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; connect-src 'self'; frame-ancestors 'none';
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
Strict-Transport-Security: max-age=31536000; includeSubDomains (em modo produção)
Cache-Control: no-store, no-cache, must-revalidate (em endpoints de API)
```

* **Anti-Clickjacking:** `X-Frame-Options: DENY` e `frame-ancestors 'none'` impedem que o sistema seja embutido em iframes de outros sites.
* **MIME Sniffing:** `X-Content-Type-Options: nosniff` proíbe o navegador de interpretar arquivos com extensões divergentes do cabeçalho declarado.

---

## 6. Rate Limiting e Validação de Host

* **Proteção Contra Força Bruta e DoS:** Algoritmo em memória controla requisições por endereço IP. O limite padrão é de 120 requisições por minuto (`RATE_LIMIT_REQUESTS=120`, `RATE_LIMIT_WINDOW_SECONDS=60`). Requisições excedentes recebem HTTP `429 Too Many Requests`.
* **Host Header Injection:** O cabeçalho `Host` da requisição é validado contra a lista autorizada em `ALLOWED_HOSTS`. Requisições com hosts não reconhecidos são sumariamente rejeitadas com HTTP `400 Bad Request`.

---

## 7. Tratamento de Erros e Logs Privados

* **Não Exposição de Stack Traces:** Em caso de exceção no servidor, o cliente recebe apenas uma resposta padronizada com status `500` e um identificador único de rastreamento (`request_id` via UUIDv4).
* **Logs Técnicos:** O stack trace completo e a causa raiz são impressos exclusivamente no console privado do servidor para auditoria dos administradores, sem nunca trafegar pela rede externa.
* **Auditoria de Dependências:** O comando `pip-audit` foi executado sobre o ambiente virtual e não identificou nenhuma vulnerabilidade conhecida nas bibliotecas instaladas.
