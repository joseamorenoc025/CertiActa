"""
Pruebas unitarias para el módulo hasher.
"""

import hashlib
from pathlib import Path
import pytest
from src.core.hasher import calcular_sha256, verificar_sha256


def test_calcular_sha256_archivo_conocido(tmp_path: Path):
    archivo_prueba = tmp_path / "prueba.txt"
    contenido = b"Prueba de integridad de acta escaneada"
    archivo_prueba.write_bytes(contenido)

    hash_esperado = hashlib.sha256(contenido).hexdigest().lower()
    hash_calculado = calcular_sha256(archivo_prueba)

    assert hash_calculado == hash_esperado
    assert len(hash_calculado) == 64


def test_calcular_sha256_archivo_inexistente():
    with pytest.raises(FileNotFoundError):
        calcular_sha256("archivo_fantasma_12345.pdf")


def test_verificar_sha256(tmp_path: Path):
    archivo = tmp_path / "documento.pdf"
    contenido = b"PDF dummy content"
    archivo.write_bytes(contenido)
    
    hash_real = hashlib.sha256(contenido).hexdigest()
    
    # Coincide exactamente (incluso con mayúsculas/espacios)
    coincide, _ = verificar_sha256(archivo, f"  {hash_real.upper()}  ")
    assert coincide is True

    # No coincide
    coincide_falso, _ = verificar_sha256(archivo, "0" * 64)
    assert coincide_falso is False
