from typing import Any, Dict, List, Optional
from app.models.municipio import Municipio
from app.models.processo_minerario import ProcessoMinerario
from config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT

class ProcessoController:
    def resumo_geral(self) -> Dict[str, Any]:
        return {
            "estadual": ProcessoMinerario.resumo(),
            "municipio": Municipio.obter_resumo_parauapebas(),
            "fiscalizacao": ProcessoMinerario.analise_fiscalizacao_tema10(),
        }

    def resumo(self) -> Dict[str, Any]:
        return ProcessoMinerario.resumo()

    def municipio_info(self) -> Optional[Dict[str, Any]]:
        return Municipio.obter_dados_municipio()

    def municipio_geojson(self) -> Dict[str, Any]:
        return Municipio.obter_geojson_limite()

    def listar(
        self,
        limite: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
        fase: Optional[str] = None,
        substancia: Optional[str] = None,
        numero: Optional[Any] = None,
        titular: Optional[str] = None,
        termo: Optional[str] = None,
        apenas_parauapebas: bool = True,
        ordenar_por: str = "area_ha_mun",
        ordem_desc: bool = True,
    ) -> Dict[str, Any]:
        limite_val = max(1, min(int(limite), MAX_PAGE_LIMIT))
        offset_val = max(0, int(offset))
        fase_val = fase.strip() if isinstance(fase, str) and fase.strip() else None
        substancia_val = substancia.strip() if isinstance(substancia, str) and substancia.strip() else None
        titular_val = titular.strip() if isinstance(titular, str) and titular.strip() else None
        termo_val = termo.strip() if isinstance(termo, str) and termo.strip() else None

        return ProcessoMinerario.listar_com_filtros(
            limite=limite_val,
            offset=offset_val,
            fase=fase_val,
            substancia=substancia_val,
            numero=numero,
            titular=titular_val,
            termo=termo_val,
            apenas_parauapebas=bool(apenas_parauapebas),
            ordenar_por=ordenar_por,
            ordem_desc=bool(ordem_desc),
        )

    def processos_geojson(
        self,
        limite: int = 400,
        fase: Optional[str] = None,
        substancia: Optional[str] = None,
        numero: Optional[Any] = None,
        titular: Optional[str] = None,
        termo: Optional[str] = None,
    ) -> Dict[str, Any]:
        limite_val = max(1, min(int(limite), MAX_PAGE_LIMIT))
        fase_val = fase.strip() if isinstance(fase, str) and fase.strip() else None
        substancia_val = substancia.strip() if isinstance(substancia, str) and substancia.strip() else None
        titular_val = titular.strip() if isinstance(titular, str) and titular.strip() else None
        termo_val = termo.strip() if isinstance(termo, str) and termo.strip() else None

        return Municipio.obter_processos_geojson(
            limite=limite_val,
            fase=fase_val,
            substancia=substancia_val,
            numero=numero,
            titular=titular_val,
            termo=termo_val,
        )

    def fases(self, apenas_parauapebas: bool = True) -> List[Dict[str, Any]]:
        return ProcessoMinerario.listar_fases(apenas_parauapebas=bool(apenas_parauapebas))

    def analise_fiscalizacao(self) -> Dict[str, Any]:
        return ProcessoMinerario.analise_fiscalizacao_tema10()

    def executar_recorte(self) -> Dict[str, Any]:
        return Municipio.recortar_processos_municipio()
