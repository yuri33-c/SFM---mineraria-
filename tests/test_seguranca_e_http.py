import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.models.processo_minerario import ProcessoMinerario
from main import application, _obter_headers_seguranca

class TestSegurancaEHTTP(unittest.TestCase):
    def test_headers_de_seguranca_presentes(self):
        headers = _obter_headers_seguranca("text/html; charset=utf-8")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_protecao_contra_sql_injection(self):
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE geo.municipios; --",
            "1 UNION SELECT null, null, null, null, null, null, null, null, null, null, null, null --",
            "1' AND 1=(SELECT 1 FROM pg_sleep(5)) --",
        ]
        for payload in payloads:
            res_termo = ProcessoMinerario.listar_com_filtros(termo=payload, apenas_parauapebas=True)
            self.assertIsInstance(res_termo["registros"], list)

            res_titular = ProcessoMinerario.listar_com_filtros(titular=payload, apenas_parauapebas=True)
            self.assertIsInstance(res_titular["registros"], list)

            res_subst = ProcessoMinerario.listar_com_filtros(substancia=payload, apenas_parauapebas=True)
            self.assertIsInstance(res_subst["registros"], list)

    def test_bloqueio_path_traversal_em_estaticos(self):
        def fake_start_response(status, headers):
            self.status = status
            self.headers = dict(headers)

        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/static/../../.env",
            "QUERY_STRING": "",
        }
        res = application(environ, fake_start_response)
        self.assertIn(self.status, ("403 Forbidden", "404 Not Found"))
        self.assertNotIn(b"DB_PASSWORD", b"".join(res))

    def test_limite_maximo_de_registros(self):
        res = ProcessoMinerario.listar_com_filtros(limite=999999, apenas_parauapebas=True)
        self.assertLessEqual(len(res["registros"]), 500)
        self.assertLessEqual(res["limite"], 500)

if __name__ == "__main__":
    unittest.main()
