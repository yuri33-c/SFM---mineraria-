import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.models.municipio import Municipio
from app.models.processo_minerario import ProcessoMinerario

class TestModelsEGeoprocessamento(unittest.TestCase):
    def test_contagem_base_estadual(self):
        resumo = ProcessoMinerario.resumo()
        self.assertEqual(resumo["total_processos"], 24445)
        self.assertEqual(resumo["geometrias_validas"], 24389)
        self.assertEqual(resumo["geometrias_invalidas"], 56)
        self.assertEqual(resumo["geometrias_validas"] + resumo["geometrias_invalidas"], 24445)

    def test_resumo_parauapebas_e_areas(self):
        resumo = Municipio.obter_resumo_parauapebas()
        self.assertEqual(resumo["total_processos"], 349)
        self.assertAlmostEqual(resumo["soma_area_recortada_ha"], 547751.92, places=1)
        self.assertAlmostEqual(resumo["area_unica_ha"], 431912.08, places=1)
        self.assertGreater(resumo["soma_area_original_ha"], 900000.0)
        self.assertEqual(resumo["fases_distintas"], 10)
        self.assertEqual(resumo["area_municipio_ha"], 688586.5)

    def test_consulta_com_filtros_parauapebas(self):
        resp = ProcessoMinerario.listar_com_filtros(limite=5, apenas_parauapebas=True)
        self.assertEqual(resp["total"], 349)
        self.assertEqual(len(resp["registros"]), 5)
        for r in resp["registros"]:
            self.assertIn("processo", r)
            self.assertIn("fase", r)
            self.assertIn("area_ha", r)
            self.assertIn("area_ha_original", r)
            self.assertIn("tipo_recorte", r)
            self.assertIn(r["tipo_recorte"], ("TOTAL", "PARCIAL"))
            self.assertIsInstance(r["autorizado_lavra"], bool)

    def test_filtro_por_substancia_e_titular(self):
        resp_ferro = ProcessoMinerario.listar_com_filtros(substancia="ferro", apenas_parauapebas=True)
        self.assertGreater(resp_ferro["total"], 0)
        for r in resp_ferro["registros"]:
            self.assertIn("FERRO", (r["substancia"] or "").upper())

        resp_vale = ProcessoMinerario.listar_com_filtros(titular="vale", apenas_parauapebas=True)
        self.assertGreater(resp_vale["total"], 0)
        for r in resp_vale["registros"]:
            self.assertIn("VALE", (r["nome_titular"] or "").upper())

    def test_geojson_municipio_e_processos(self):
        geo_mun = Municipio.obter_geojson_limite()
        self.assertEqual(geo_mun["type"], "Feature")
        self.assertIn("geometry", geo_mun)
        self.assertEqual(geo_mun["geometry"]["type"], "Polygon")

        geo_proc = Municipio.obter_processos_geojson(limite=10)
        self.assertEqual(geo_proc["type"], "FeatureCollection")
        self.assertLessEqual(len(geo_proc["features"]), 10)
        for feat in geo_proc["features"]:
            self.assertEqual(feat["type"], "Feature")
            self.assertIn("area_ha_mun", feat["properties"])
            self.assertIn("tipo_recorte", feat["properties"])

    def test_analise_fiscalizacao_tema10(self):
        analise = ProcessoMinerario.analise_fiscalizacao_tema10()
        self.assertEqual(analise["municipio_analisado"], "Parauapebas / PA (IBGE 1505536)")
        self.assertIn("diagnostico_fases_parauapebas", analise)
        self.assertIn("resultados_cruzamento", analise)
        self.assertEqual(analise["diagnostico_fases_parauapebas"]["total_processos_municipio"], 349)

if __name__ == "__main__":
    unittest.main()
