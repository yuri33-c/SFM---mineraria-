from typing import Any, Dict
from app.models.status import StatusBanco

class StatusController:
    def verificar(self) -> Dict[str, Any]:
        return StatusBanco.verificar()
