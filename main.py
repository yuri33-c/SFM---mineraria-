import json
import mimetypes
import time
import uuid
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from app.controllers.home_controller import HomeController
from app.controllers.processo_controller import ProcessoController
from app.controllers.status_controller import StatusController
from config import (
    ALLOWED_HOSTS,
    DEFAULT_PAGE_LIMIT,
    IS_PRODUCTION,
    MAX_PAGE_LIMIT,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    SERVER_HOST,
    SERVER_PORT,
    VIEWS_DIR,
    validar_configuracao,
)

_requisicoes_por_ip: Dict[str, List[float]] = defaultdict(list)

def _verificar_rate_limit(ip: str) -> bool:
    agora = time.time()
    janela = agora - RATE_LIMIT_WINDOW
    timestamps = [t for t in _requisicoes_por_ip[ip] if t > janela]
    timestamps.append(agora)
    _requisicoes_por_ip[ip] = timestamps
    return len(timestamps) <= RATE_LIMIT_REQUESTS

def _obter_headers_seguranca(tipo_conteudo: str, eh_api: bool = False) -> Dict[str, str]:
    headers = {
        "Content-Type": tipo_conteudo,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://server.arcgisonline.com https://services.arcgisonline.com https://*.arcgisonline.com https://unpkg.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
    }
    if IS_PRODUCTION:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if eh_api:
        headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return headers

class SistemaHandler(BaseHTTPRequestHandler):
    def _enviar_resposta(self, codigo: int, corpo_bytes: bytes, headers: Dict[str, str]):
        self.send_response(codigo)
        for chave, valor in headers.items():
            self.send_header(chave, valor)
        self.send_header("Content-Length", str(len(corpo_bytes)))
        self.end_headers()
        self.wfile.write(corpo_bytes)

    def _enviar_json(self, codigo: int, dados: Any):
        corpo = json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")
        headers = _obter_headers_seguranca("application/json; charset=utf-8", eh_api=True)
        self._enviar_resposta(codigo, corpo, headers)

    def _enviar_texto(self, codigo: int, texto: str, tipo_mime: str = "text/plain; charset=utf-8"):
        corpo = texto.encode("utf-8")
        headers = _obter_headers_seguranca(tipo_mime)
        self._enviar_resposta(codigo, corpo, headers)

    def _validar_host(self) -> bool:
        host = self.headers.get("Host", "").split(":")[0].strip().lower()
        if not host:
            return not IS_PRODUCTION
        return host in ALLOWED_HOSTS

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        ip_cliente = self.client_address[0]
        if not _verificar_rate_limit(ip_cliente):
            self._enviar_json(429, {"status": "erro", "mensagem": "Limite de requisições excedido. Tente novamente em breve."})
            return

        if not self._validar_host():
            self._enviar_json(400, {"status": "erro", "mensagem": "Cabeçalho Host inválido."})
            return

        rota = urlparse(self.path)
        try:
            if rota.path == "/api/municipio/recortar":
                resultado = ProcessoController().executar_recorte()
                self._enviar_json(200, {"status": "sucesso", "resultado": resultado})
                return

            self._enviar_json(404, {"status": "erro", "mensagem": "Endpoint não encontrado."})
        except Exception as erro:
            req_id = str(uuid.uuid4())
            print(f"[ERRO POST][{req_id}] Falha em {rota.path}: {erro}")
            self._enviar_json(500, {"status": "erro", "mensagem": "Erro interno do servidor.", "request_id": req_id})

    def do_GET(self):
        ip_cliente = self.client_address[0]
        if not _verificar_rate_limit(ip_cliente):
            self._enviar_json(429, {"status": "erro", "mensagem": "Limite de requisições excedido. Tente novamente em breve."})
            return

        if not self._validar_host():
            self._enviar_json(400, {"status": "erro", "mensagem": "Cabeçalho Host inválido."})
            return

        rota = urlparse(self.path)
        params = parse_qs(rota.query)

        try:
            if rota.path in ("/", "/apresentacao", "/apresentacao.html"):
                conteudo_html = HomeController().apresentacao()
                self._enviar_texto(200, conteudo_html, "text/html; charset=utf-8")
                return

            if rota.path in ("/sistema", "/index.html"):
                conteudo_html = HomeController().index()
                self._enviar_texto(200, conteudo_html, "text/html; charset=utf-8")
                return

            if rota.path.startswith("/static/"):
                caminho_relativo = rota.path.removeprefix("/static/").lstrip("/\\")
                diretorio_estatico = (VIEWS_DIR / "static").resolve()
                arquivo_estatico = (diretorio_estatico / caminho_relativo).resolve()

                if not arquivo_estatico.is_relative_to(diretorio_estatico):
                    self._enviar_texto(403, "Acesso negado.", "text/plain; charset=utf-8")
                    return

                if not arquivo_estatico.is_file():
                    self._enviar_texto(404, "Arquivo não encontrado.", "text/plain; charset=utf-8")
                    return

                if arquivo_estatico.suffix == ".css":
                    tipo_mime = "text/css; charset=utf-8"
                elif arquivo_estatico.suffix == ".js":
                    tipo_mime = "application/javascript; charset=utf-8"
                else:
                    guess, _ = mimetypes.guess_type(str(arquivo_estatico))
                    tipo_mime = guess or "application/octet-stream"

                conteudo_bytes = arquivo_estatico.read_bytes()
                headers = _obter_headers_seguranca(tipo_mime)
                headers["Cache-Control"] = "public, max-age=86400" if IS_PRODUCTION else "no-cache, must-revalidate"
                self._enviar_resposta(200, conteudo_bytes, headers)
                return

            if rota.path == "/api/status":
                self._enviar_json(200, StatusController().verificar())
                return

            if rota.path in ("/api/resumo", "/api/processos/resumo_geral"):
                self._enviar_json(200, ProcessoController().resumo_geral())
                return

            if rota.path == "/api/processos/resumo":
                self._enviar_json(200, ProcessoController().resumo())
                return

            if rota.path == "/api/municipio":
                self._enviar_json(200, ProcessoController().municipio_info())
                return

            if rota.path == "/api/municipio/geojson":
                self._enviar_json(200, ProcessoController().municipio_geojson())
                return

            if rota.path == "/api/processos":
                limite = int(params.get("limite", [str(DEFAULT_PAGE_LIMIT)])[0])
                offset = int(params.get("offset", ["0"])[0])
                fase = params.get("fase", [None])[0]
                substancia = params.get("substancia", [None])[0]
                titular = params.get("titular", [None])[0]
                numero = params.get("numero", [None])[0]
                termo = params.get("termo", [None])[0]
                apenas_mun = params.get("apenas_parauapebas", ["true"])[0].lower() in ("true", "1", "sim")

                dados = ProcessoController().listar(
                    limite=limite,
                    offset=offset,
                    fase=fase,
                    substancia=substancia,
                    numero=numero,
                    titular=titular,
                    termo=termo,
                    apenas_parauapebas=apenas_mun,
                )
                self._enviar_json(200, dados)
                return

            if rota.path == "/api/processos/geojson":
                limite = int(params.get("limite", ["400"])[0])
                fase = params.get("fase", [None])[0]
                substancia = params.get("substancia", [None])[0]
                titular = params.get("titular", [None])[0]
                numero = params.get("numero", [None])[0]
                termo = params.get("termo", [None])[0]

                geojson = ProcessoController().processos_geojson(
                    limite=limite,
                    fase=fase,
                    substancia=substancia,
                    numero=numero,
                    titular=titular,
                    termo=termo,
                )
                self._enviar_json(200, geojson)
                return

            if rota.path == "/api/fases":
                apenas_mun = params.get("apenas_parauapebas", ["true"])[0].lower() in ("true", "1", "sim")
                self._enviar_json(200, ProcessoController().fases(apenas_parauapebas=apenas_mun))
                return

            if rota.path == "/api/fiscalizacao/analise":
                self._enviar_json(200, ProcessoController().analise_fiscalizacao())
                return

            self._enviar_json(404, {"status": "erro", "mensagem": "Endpoint não encontrado."})

        except Exception as erro:
            req_id = str(uuid.uuid4())
            print(f"[ERRO GET][{req_id}] Falha ao processar {rota.path}: {erro}")
            self._enviar_json(500, {
                "status": "erro",
                "mensagem": "Erro interno do servidor.",
                "request_id": req_id,
            })

    def log_message(self, formato, *args):
        if not IS_PRODUCTION:
            print(f"[{self.log_date_time_string()}] {formato % args}")

def application(environ, start_response):
    caminho = environ.get("PATH_INFO", "/")
    metodo = environ.get("REQUEST_METHOD", "GET").upper()
    query_string = environ.get("QUERY_STRING", "")
    params = parse_qs(query_string)

    headers_padrao = _obter_headers_seguranca("application/json; charset=utf-8", eh_api=True)

    try:
        if metodo == "GET":
            if caminho in ("/", "/apresentacao", "/apresentacao.html"):
                html = HomeController().apresentacao().encode("utf-8")
                headers = list(_obter_headers_seguranca("text/html; charset=utf-8").items())
                headers.append(("Content-Length", str(len(html))))
                start_response("200 OK", headers)
                return [html]

            if caminho in ("/sistema", "/index.html"):
                html = HomeController().index().encode("utf-8")
                headers = list(_obter_headers_seguranca("text/html; charset=utf-8").items())
                headers.append(("Content-Length", str(len(html))))
                start_response("200 OK", headers)
                return [html]

            if caminho.startswith("/static/"):
                caminho_relativo = caminho.removeprefix("/static/").lstrip("/\\")
                diretorio_estatico = (VIEWS_DIR / "static").resolve()
                arquivo_estatico = (diretorio_estatico / caminho_relativo).resolve()

                if not arquivo_estatico.is_relative_to(diretorio_estatico):
                    start_response("403 Forbidden", [("Content-Type", "text/plain")])
                    return [b"Acesso negado."]

                if not arquivo_estatico.is_file():
                    start_response("404 Not Found", [("Content-Type", "text/plain")])
                    return [b"Arquivo nao encontrado."]

                if arquivo_estatico.suffix == ".css":
                    tipo_mime = "text/css; charset=utf-8"
                elif arquivo_estatico.suffix == ".js":
                    tipo_mime = "application/javascript; charset=utf-8"
                else:
                    guess, _ = mimetypes.guess_type(str(arquivo_estatico))
                    tipo_mime = guess or "application/octet-stream"

                corpo = arquivo_estatico.read_bytes()
                headers = list(_obter_headers_seguranca(tipo_mime).items())
                headers.append(("Content-Length", str(len(corpo))))
                headers.append(("Cache-Control", "public, max-age=86400" if IS_PRODUCTION else "no-cache, must-revalidate"))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/status":
                corpo = json.dumps(StatusController().verificar(), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho in ("/api/resumo", "/api/processos/resumo_geral"):
                corpo = json.dumps(ProcessoController().resumo_geral(), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/processos":
                limite = int(params.get("limite", [str(DEFAULT_PAGE_LIMIT)])[0])
                offset = int(params.get("offset", ["0"])[0])
                fase = params.get("fase", [None])[0]
                substancia = params.get("substancia", [None])[0]
                titular = params.get("titular", [None])[0]
                numero = params.get("numero", [None])[0]
                termo = params.get("termo", [None])[0]
                apenas_mun = params.get("apenas_parauapebas", ["true"])[0].lower() in ("true", "1", "sim")

                dados = ProcessoController().listar(
                    limite=limite, offset=offset, fase=fase, substancia=substancia,
                    numero=numero, titular=titular, termo=termo, apenas_parauapebas=apenas_mun,
                )
                corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/processos/geojson":
                limite = int(params.get("limite", ["400"])[0])
                fase = params.get("fase", [None])[0]
                substancia = params.get("substancia", [None])[0]
                titular = params.get("titular", [None])[0]
                numero = params.get("numero", [None])[0]
                termo = params.get("termo", [None])[0]

                geojson = ProcessoController().processos_geojson(
                    limite=limite, fase=fase, substancia=substancia,
                    numero=numero, titular=titular, termo=termo,
                )
                corpo = json.dumps(geojson, ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/municipio":
                corpo = json.dumps(ProcessoController().municipio_info(), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/municipio/geojson":
                corpo = json.dumps(ProcessoController().municipio_geojson(), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/fases":
                apenas_mun = params.get("apenas_parauapebas", ["true"])[0].lower() in ("true", "1", "sim")
                corpo = json.dumps(ProcessoController().fases(apenas_parauapebas=apenas_mun), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

            if caminho == "/api/fiscalizacao/analise":
                corpo = json.dumps(ProcessoController().analise_fiscalizacao(), ensure_ascii=False).encode("utf-8")
                headers = list(headers_padrao.items())
                headers.append(("Content-Length", str(len(corpo))))
                start_response("200 OK", headers)
                return [corpo]

        start_response("404 Not Found", list(headers_padrao.items()))
        return [b'{"status": "erro", "mensagem": "Endpoint nao encontrado."}']

    except Exception as erro:
        req_id = str(uuid.uuid4())
        print(f"[ERRO WSGI][{req_id}]: {erro}")
        start_response("500 Internal Server Error", list(headers_padrao.items()))
        return [json.dumps({"status": "erro", "mensagem": "Erro interno.", "request_id": req_id}).encode("utf-8")]

def iniciar_servidor(host: str = SERVER_HOST, porta: int = SERVER_PORT):
    erros = validar_configuracao()
    if erros:
        for e in erros:
            print(f"[ERRO CONFIG] {e}")
        if IS_PRODUCTION:
            raise RuntimeError("Configuração de produção inválida.")

    servidor = ThreadingHTTPServer((host, porta), SistemaHandler)
    print("=" * 70)
    print("  SISTEMA DE FISCALIZAÇÃO MINERÁRIA (SFM) — TEMA 10")
    print(f"  Ambiente: {'PRODUÇÃO' if IS_PRODUCTION else 'DESENVOLVIMENTO'}")
    print(f"  Apresentação: http://{host}:{porta}/")
    print(f"  Ambiente Operacional: http://{host}:{porta}/sistema")
    print("=" * 70)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado pelo operador.")
    finally:
        servidor.server_close()

if __name__ == "__main__":
    iniciar_servidor()
