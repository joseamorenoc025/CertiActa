"""
Configuración central y rutas del sistema.
Define constantes, rutas dinámicas de trabajo y asegura la existencia de la jerarquía de carpetas.
"""

from pathlib import Path
import sys
from typing import Final

# Detección de ejecución empaquetada (PyInstaller) vs desarrollo
IS_FROZEN: Final[bool] = getattr(sys, "frozen", False)

# Directorio del ejecutable o raíz del proyecto (donde vive settings.json)
APP_DIR: Final[Path] = (
    Path(sys.executable).resolve().parent
    if IS_FROZEN
    else Path(__file__).resolve().parent.parent
)

# Directorio de recursos empaquetados (_MEIPASS en PyInstaller o APP_DIR en desarrollo)
RESOURCE_DIR: Final[Path] = (
    Path(getattr(sys, "_MEIPASS", APP_DIR))
    if IS_FROZEN
    else APP_DIR
)

# Archivo de configuración local junto al ejecutable
FILE_SETTINGS: Final[Path] = APP_DIR / "settings.json"

# Recursos estáticos
DIR_ASSETS: Final[Path] = RESOURCE_DIR / "assets"
DIR_DOCS: Final[Path] = RESOURCE_DIR / "docs"
FILE_LOGO: Final[Path] = DIR_ASSETS / "logo.png"
FILE_ICON: Final[Path] = DIR_ASSETS / "icon.ico"

# Rutas de trabajo activas (pueden cambiar desde Ajustes)
BASE_DIR: Path = APP_DIR
DIR_DATOS: Path = BASE_DIR / "datos"
DIR_EXPORTACIONES: Path = DIR_DATOS / "exportaciones"
DIR_ORIGINALES: Path = BASE_DIR / "01_Escaneos_Originales"
DIR_CON_HASH: Path = BASE_DIR / "02_Actas_Con_Hash"

# Archivos de persistencia y bóveda
FILE_REGISTRO: Path = DIR_DATOS / "registro_actas.json"
FILE_REGISTRO_ENC: Path = DIR_DATOS / "registro_actas.enc"
FILE_VAULT: Path = DIR_DATOS / "vault.json"

# Tipos de sesión válidos
TIPOS_SESION: Final[list[str]] = [
    "Ordinaria",
    "Extraordinaria",
    "Especial",
    "Solemne",
]

# Configuración visual y autoría
APP_NAME: Final[str] = "CertiActa"
APP_VERSION: Final[str] = "1.2.0"
APP_TITLE: Final[str] = "CertiActa — Verificador de Actas SHA-256"
APP_AUTHOR: Final[str] = "José Moreno — Secretario de Cámara del Consejo Legislativo del Estado Bolivariano Delta Amacuro"
APP_GEOMETRY: Final[str] = "1080x740"
APP_MIN_SIZE: Final[tuple[int, int]] = (980, 660)


def apply_work_dir(work_dir: Path) -> None:
    """Actualiza dinámicamente las rutas activas de datos y actas."""
    global BASE_DIR, DIR_DATOS, DIR_EXPORTACIONES, DIR_ORIGINALES, DIR_CON_HASH
    global FILE_REGISTRO, FILE_REGISTRO_ENC, FILE_VAULT

    resolved = Path(work_dir).resolve()
    BASE_DIR = resolved
    DIR_DATOS = BASE_DIR / "datos"
    DIR_EXPORTACIONES = DIR_DATOS / "exportaciones"
    DIR_ORIGINALES = BASE_DIR / "01_Escaneos_Originales"
    DIR_CON_HASH = BASE_DIR / "02_Actas_Con_Hash"
    FILE_REGISTRO = DIR_DATOS / "registro_actas.json"
    FILE_REGISTRO_ENC = DIR_DATOS / "registro_actas.enc"
    FILE_VAULT = DIR_DATOS / "vault.json"


def init_directories() -> None:
    """Crea automáticamente todas las carpetas necesarias si aún no existen."""
    for directory in (DIR_DATOS, DIR_EXPORTACIONES, DIR_ORIGINALES, DIR_CON_HASH):
        directory.mkdir(parents=True, exist_ok=True)

    # Inicializa el archivo JSON si no existe ni la versión cifrada ni la plana
    if not FILE_REGISTRO.exists() and not FILE_REGISTRO_ENC.exists():
        FILE_REGISTRO.write_text("[]", encoding="utf-8")
