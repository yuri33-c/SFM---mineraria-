from config import VIEWS_DIR

class HomeController:
    def index(self) -> str:
        return (VIEWS_DIR / "index.html").read_text(encoding="utf-8")

    def apresentacao(self) -> str:
        caminho = VIEWS_DIR / "apresentacao.html"
        if caminho.exists():
            return caminho.read_text(encoding="utf-8")
        return (VIEWS_DIR / "index.html").read_text(encoding="utf-8")
