"""
Módulo criptográfico para el cálculo y auditoría de huellas digitales SHA-256.
Garantiza lectura en bloques de memoria para soportar archivos de gran tamaño sin saturar RAM.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Union


def calcular_sha256(ruta_archivo: Union[str, Path], chunk_size: int = 65536) -> str:
    """
    Calcula el hash SHA-256 de un archivo local leyendo por bloques.

    Args:
        ruta_archivo: Ruta al archivo.
        chunk_size: Tamaño de bloque de lectura en bytes (por defecto 64 KB).

    Returns:
        Cadena hexadecimal en minúsculas del hash SHA-256 (64 caracteres).

    Raises:
        FileNotFoundError: Si el archivo no existe.
        PermissionError: Si no hay permisos de lectura.
        IsADirectoryError: Si la ruta apunta a un directorio.
    """
    path = Path(ruta_archivo)
    if not path.is_file():
        raise FileNotFoundError(f"El archivo especificado no existe o no es válido: {path}")

    sha256_hasher = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hasher.update(chunk)

    return sha256_hasher.hexdigest().lower()


def verificar_sha256(ruta_archivo: Union[str, Path], hash_esperado: str) -> tuple[bool, str]:
    """
    Compara el hash del archivo contra el hash esperado en tiempo constante.

    Args:
        ruta_archivo: Archivo a auditar.
        hash_esperado: Cadena de hash de referencia.

    Returns:
        Tupla (coincide: bool, hash_calculado: str)
    """
    hash_limpio_esperado = hash_esperado.strip().lower()
    hash_calculado = calcular_sha256(ruta_archivo)
    
    coincide = hmac.compare_digest(hash_calculado, hash_limpio_esperado)
    return coincide, hash_calculado
