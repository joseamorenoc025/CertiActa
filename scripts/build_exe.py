"""
Script reproducible para empaquetar CertiActa para Windows con PyInstaller
y generar el archivo ZIP portátil listo para GitHub Releases.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
APP_NAME = "CertiActa"
VERSION = "1.2.0"


def main() -> None:
    # Limpiar compilaciones previas
    shutil.rmtree(DIST_DIR / APP_NAME, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    icon_path = ROOT_DIR / "assets" / "icon.ico"
    manual_path = ROOT_DIR / "docs" / "Manual_de_Usuario.pdf"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        f"--name={APP_NAME}",
        f"--icon={icon_path}",
        f"--add-data={ROOT_DIR / 'assets'};assets",
        f"--add-data={manual_path};docs",
        "--collect-data=customtkinter",
        "--hidden-import=PIL._tkinter_finder",
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=scipy",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=pyarrow",
        "--exclude-module=numba",
        "--exclude-module=llvmlite",
        "--exclude-module=matplotlib",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=pytest",
        str(ROOT_DIR / "main.py"),
    ]

    print("Ejecutando PyInstaller...")
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)

    app_out_dir = DIST_DIR / APP_NAME
    if not (app_out_dir / f"{APP_NAME}.exe").exists():
        raise FileNotFoundError(f"No se generó {app_out_dir / f'{APP_NAME}.exe'}")

    # Copiar Manual y LEEME junto al ejecutable para acceso directo del usuario
    if manual_path.exists():
        shutil.copy2(manual_path, app_out_dir / "Manual_de_Usuario.pdf")

    leeme = (
        f"CertiActa v{VERSION} - Sistema de Integridad Documental SHA-256\n"
        "Creado por: Jose Moreno - Secretario de Camara CLEBDA\n\n"
        "INSTRUCCIONES DE USO PORTATIL (WINDOWS 10/11):\n"
        "1. Extraiga toda esta carpeta en una ubicacion permanente (ej. C:\\CertiActa\\ o D:\\CertiActa\\).\n"
        "2. Ejecute CertiActa.exe.\n"
        "3. Por defecto, las carpetas '01_Escaneos_Originales', '02_Actas_Con_Hash' y 'datos'\n"
        "   se crearan junto a CertiActa.exe (puede cambiar la carpeta en la pestana Ajustes).\n"
        "4. Consulte Manual_de_Usuario.pdf para la guia completa de operacion y auditoria.\n"
    )
    (app_out_dir / "LEEME.txt").write_text(leeme, encoding="utf-8")

    zip_path = DIST_DIR / f"{APP_NAME}-v{VERSION}-Windows-x64.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in app_out_dir.rglob("*"):
            if file_path.is_file():
                rel = file_path.relative_to(DIST_DIR)
                zf.write(file_path, arcname=str(rel))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Paquete generado exitosamente: {zip_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
