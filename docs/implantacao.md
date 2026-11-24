# Guia de Implantação e Publicação em Produção — SFM

Este documento orienta a publicação profissional do **Sistema de Fiscalização Minerária** em servidores Linux (Ubuntu 22.04/24.04 LTS ou Debian 12) e Windows Server, utilizando **Waitress** como servidor WSGI e **Caddy** ou **Nginx** como proxy reverso com HTTPS automático.

---

## 1. Requisitos de Infraestrutura

* **Sistema Operacional:** Linux (Ubuntu 22.04 LTS / Debian 12) ou Windows Server 2022.
* **Processador:** Mínimo de 2 vCPUs.
* **Memória RAM:** Mínimo de 4 GB (recomendado 8 GB para consultas espaciais complexas).
* **Armazenamento:** Mínimo de 20 GB SSD.
* **Rede:** Portas 80 (HTTP) e 443 (HTTPS) públicas; porta 5432 (PostgreSQL) restrita à rede local/privada.

---

## 2. Preparação do Servidor Linux

### 2.1 Instalação de Pacotes do Sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.13 python3.13-venv python3.13-dev postgresql-18 postgresql-18-postgis-3 gdal-bin
```

### 2.2 Criação do Usuário e Estrutura de Pastas
```bash
sudo useradd -r -m -s /bin/bash sfm
sudo mkdir -p /var/www/sfm
sudo chown -R sfm:sfm /var/www/sfm
```

### 2.3 Clonagem do Código e Ambiente Virtual
```bash
# Como usuário sfm
sudo -u sfm git clone <URL_DO_REPOSITORIO> /var/www/sfm
cd /var/www/sfm
sudo -u sfm python3.13 -m venv .venv
sudo -u sfm .venv/bin/pip install --upgrade pip
sudo -u sfm .venv/bin/pip install -r requirements.txt
```

---

## 3. Configuração do Banco de Dados PostgreSQL/PostGIS

```bash
# Acessar console do PostgreSQL
sudo -u postgres psql

# Criar banco e usuário com privilégios estritos
CREATE DATABASE fiscalizacao_mineraria;
\c fiscalizacao_mineraria
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE USER fiscalizacao_app WITH PASSWORD 'SENHA_FORTE_AQUI';
GRANT CONNECT ON DATABASE fiscalizacao_mineraria TO fiscalizacao_app;
GRANT USAGE ON SCHEMA geo TO fiscalizacao_app;
GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ALL TABLES IN SCHEMA geo TO fiscalizacao_app;
```

---

## 4. Configuração das Variáveis de Ambiente (`.env`)

Crie o arquivo `/var/www/sfm/.env` com permissões restritas:

```ini
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=fiscalizacao_mineraria
DB_USER=fiscalizacao_app
DB_PASSWORD=SENHA_FORTE_AQUI

SFM_ENV=production
SFM_HOST=127.0.0.1
SFM_PORT=8000
SFM_ALLOWED_HOSTS=seu-dominio.com.br,www.seu-dominio.com.br
SFM_RATE_LIMIT_REQUESTS=120
SFM_RATE_LIMIT_WINDOW_SECONDS=60
```

```bash
chmod 600 /var/www/sfm/.env
chown sfm:sfm /var/www/sfm/.env
```

---

## 5. Serviço de Execução Contínua (Systemd)

Copie o arquivo de serviço disponibilizado em `deploy/sfm.service`:

```bash
sudo cp /var/www/sfm/deploy/sfm.service /etc/systemd/system/sfm.service
sudo systemctl daemon-reload
sudo systemctl enable sfm
sudo systemctl start sfm
sudo systemctl status sfm
```

---

## 6. Publicação com Proxy Reverso HTTPS

### Opção A: Caddy (Recomendado — TLS Automático Let's Encrypt)

```bash
sudo apt install -y caddy
sudo cp /var/www/sfm/deploy/Caddyfile /etc/caddy/Caddyfile
# Editar o domínio em /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### Opção B: Nginx + Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /var/www/sfm/deploy/nginx.conf /etc/nginx/sites-available/sfm.conf
sudo ln -s /etc/nginx/sites-available/sfm.conf /etc/nginx/sites-enabled/
sudo certbot --nginx -d seu-dominio.com.br
sudo systemctl restart nginx
```

---

## 7. Procedimentos de Backup e Atualização

### Backup do Banco de Dados
```bash
pg_dump -h 127.0.0.1 -U postgres -d fiscalizacao_mineraria -F c -b -v -f /var/backups/sfm_$(date +%Y%m%d_%H%M%S).dump
```

### Procedimento de Atualização
```bash
cd /var/www/sfm
sudo -u sfm git pull origin main
sudo -u sfm .venv/bin/pip install -r requirements.txt
sudo -u sfm .venv/bin/python tests/executar_todos_testes.py
sudo systemctl restart sfm
```
