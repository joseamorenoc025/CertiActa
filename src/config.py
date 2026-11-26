"""
Configuración central y rutas del sistema.
Define constantes, rutas absolutas y asegura la existencia de la jerarquía de carpetas.
"""

from pathlib import Path
import sys
from typing import Final

# Detección de ejecución empaquetada (PyInstaller) vs desarrollo
IS_FROZEN: Final[bool] = getattr(sys, "frozen", False)

# Directorio raíz para datos persistentes (junto al .exe cuando está congelado)
BASE_DIR: Final[Path] = (
    Path(sys.executable).resolve().parent
    if IS_FROZEN
    else Path(__file__).resolve().parent.parent
)

# Directorio de recursos empaquetados (_MEIPASS en PyInstaller o BASE_DIR en desarrollo)
RESOURCE_DIR: Final[Path] = (
    Path(getattr(sys, "_MEIPASS", BASE_DIR))
    if IS_FROZEN
    else BASE_DIR
)

# Carpetas del sistema
DIR_DATOS: Final[Path] = BASE_DIR / "datos"
DIR_EXPORTACIONES: Final[Path] = DIR_DATOS / "exportaciones"
DIR_ORIGINALES: Final[Path] = BASE_DIR / "01_Escaneos_Originales"
DIR_CON_HASH: Final[Path] = BASE_DIR / "02_Actas_Con_Hash"
DIR_ASSETS: Final[Path] = RESOURCE_DIR / "assets"
DIR_DOCS: Final[Path] = RESOURCE_DIR / "docs"

# Archivos de persistencia y recursos
FILE_REGISTRO: Final[Path] = DIR_DATOS / "registro_actas.json"
FILE_LOGO: Final[Path] = DIR_ASSETS / "logo.png"
FILE_ICON: Final[Path] = DIR_ASSETS / "icon.ico"

# Tipos de sesión válidos
TIPOS_SESION: Final[list[str]] = [
    "Ordinaria",
    "Extraordinaria",
    "Especial",
    "Solemne",
]

# Configuración visual y autoría
APP_NAME: Final[str] = "CertiActa"
APP_VERSION: Final[str] = "1.0.0"
APP_TITLE: Final[str] = "CertiActa — Verificador de Actas SHA-256"
APP_AUTHOR: Final[str] = "José Moreno — Secretario de Cámara del Consejo Legislativo del Estado Bolivariano Delta Amacuro"
APP_GEOMETRY: Final[str] = "1050x720"
APP_MIN_SIZE: Final[tuple[int, int]] = (950, 650)


def init_directories() -> None:
    """Crea automáticamente todas las carpetas necesarias si aún no existen."""
    for directory in (DIR_DATOS, DIR_EXPORTACIONES, DIR_ORIGINALES, DIR_CON_HASH):
        directory.mkdir(parents=True, exist_ok=True)
    
    # Inicializa el archivo JSON si no existe
    if not FILE_REGISTRO.exists():
        FILE_REGISTRO.write_text("[]", encoding="utf-8")
