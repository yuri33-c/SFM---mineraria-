import unittest
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

class TestImportsEMVC(unittest.TestCase):
    def test_import_dependencias_principais(self):
        import geopandas
        import shapely
        import psycopg
        import dotenv
        import waitress
        self.assertIsNotNone(geopandas.__version__)
        self.assertIsNotNone(shapely.__version__)

    def test_estrutura_diretorios_mvc(self):
        app_dir = BASE_DIR / "app"
        subpastas = {p.name for p in app_dir.iterdir() if p.is_dir() and p.name != "__pycache__"}
        self.assertEqual(subpastas, {"models", "views", "controllers"})

    def test_existencia_arquivos_views(self):
        views_dir = BASE_DIR / "app" / "views"
        self.assertTrue((views_dir / "index.html").is_file())
        self.assertTrue((views_dir / "apresentacao.html").is_file())
        self.assertTrue((views_dir / "static" / "css" / "style.css").is_file())
        self.assertTrue((views_dir / "static" / "js" / "app.js").is_file())

    def test_configuracoes_e_caminhos(self):
        from config import (
            IBGE_SHP_PATH,
            SIGMINE_SHP_PATH,
            MAPBIOMAS_DIR,
            COD_IBGE_PARAUAPEBAS,
            EPSG_GEODESICO,
            EPSG_METRICO,
        )
        self.assertTrue(IBGE_SHP_PATH.exists())
        self.assertTrue(SIGMINE_SHP_PATH.exists())
        self.assertTrue(MAPBIOMAS_DIR.exists())
        self.assertEqual(COD_IBGE_PARAUAPEBAS, "1505536")
        self.assertEqual(EPSG_GEODESICO, 4674)
        self.assertEqual(EPSG_METRICO, 31982)

    def test_conexao_banco_e_postgis(self):
        from app.models.database import obter_conexao
        with obter_conexao() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                self.assertEqual(cur.fetchone()[0], 1)
                cur.execute("SELECT PostGIS_Version();")
                postgis_ver = cur.fetchone()[0]
                self.assertTrue(len(postgis_ver) > 0)

if __name__ == "__main__":
    unittest.main()
