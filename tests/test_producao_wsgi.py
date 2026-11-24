import unittest
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from main import application

class TestProducaoWSGI(unittest.TestCase):
    def _requisicao_wsgi(self, caminho, metodo="GET", query=""):
        status_recebido = []
        headers_recebidos = []

        def start_response(status, headers):
            status_recebido.append(status)
            headers_recebidos.append(dict(headers))

        environ = {
            "REQUEST_METHOD": metodo,
            "PATH_INFO": caminho,
            "QUERY_STRING": query,
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "8000",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": None,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        corpo_iter = application(environ, start_response)
        corpo = b"".join(corpo_iter)
        return status_recebido[0], headers_recebidos[0], corpo

    def test_rota_apresentacao_html(self):
        status, headers, corpo = self._requisicao_wsgi("/")
        self.assertEqual(status, "200 OK")
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Sistema de Fiscalização Minerária".encode("utf-8"), corpo)

    def test_rota_sistema_html(self):
        status, headers, corpo = self._requisicao_wsgi("/sistema")
        self.assertEqual(status, "200 OK")
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Visualização Cartográfica Territorial".encode("utf-8"), corpo)

    def test_rota_api_status(self):
        status, headers, corpo = self._requisicao_wsgi("/api/status")
        self.assertEqual(status, "200 OK")
        dados = json.loads(corpo.decode("utf-8"))
        self.assertEqual(dados["status"], "ok")
        self.assertEqual(dados["banco"], "fiscalizacao_mineraria")

    def test_rota_api_resumo(self):
        status, headers, corpo = self._requisicao_wsgi("/api/resumo")
        self.assertEqual(status, "200 OK")
        dados = json.loads(corpo.decode("utf-8"))
        self.assertIn("municipio", dados)
        self.assertIn("estadual", dados)
        self.assertEqual(dados["municipio"]["total_processos"], 349)

    def test_rota_api_processos_json(self):
        status, headers, corpo = self._requisicao_wsgi("/api/processos", query="limite=10")
        self.assertEqual(status, "200 OK")
        dados = json.loads(corpo.decode("utf-8"))
        self.assertEqual(len(dados["registros"]), 10)
        self.assertEqual(dados["total"], 349)

    def test_rota_api_processos_geojson(self):
        status, headers, corpo = self._requisicao_wsgi("/api/processos/geojson", query="limite=5")
        self.assertEqual(status, "200 OK")
        dados = json.loads(corpo.decode("utf-8"))
        self.assertEqual(dados["type"], "FeatureCollection")
        self.assertEqual(len(dados["features"]), 5)

    def test_rota_estatica_css_e_js(self):
        status, headers, corpo = self._requisicao_wsgi("/static/css/style.css")
        self.assertEqual(status, "200 OK")
        self.assertIn("text/css", headers["Content-Type"])

        status, headers, corpo = self._requisicao_wsgi("/static/js/app.js")
        self.assertEqual(status, "200 OK")
        self.assertIn("application/javascript", headers["Content-Type"])

    def test_rota_inexistente_retorna_404(self):
        status, headers, corpo = self._requisicao_wsgi("/api/rota_inexistente_xyz")
        self.assertEqual(status, "404 Not Found")

if __name__ == "__main__":
    unittest.main()
