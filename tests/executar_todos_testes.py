import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def executar():
    print("=" * 70)
    print("  SUITE DE TESTES AUTOMATIZADOS — SISTEMA DE FISCALIZAÇÃO MINERÁRIA")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(BASE_DIR / "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Testes Executados: {resultado.testsRun}")
    print(f"Sucessos: {resultado.testsRun - len(resultado.failures) - len(resultado.errors)}")
    print(f"Falhas: {len(resultado.failures)}")
    print(f"Erros: {len(resultado.errors)}")
    print("=" * 70)

    if not resultado.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    executar()
