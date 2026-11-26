"""
Gestión de preferencias locales (settings.json) y migración segura de la Carpeta de Trabajo.
"""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
from typing import Literal

import src.config as cfg


@dataclass
class AppSettings:
    """Preferencias persistentes del usuario."""

    work_dir: str = ""
    vault_enabled: bool = False
    pdf_owner_protect: bool = False

    def get_work_dir_path(self) -> Path:
        if self.work_dir:
            p = Path(self.work_dir)
            if p.is_absolute():
                return p
        return cfg.APP_DIR


def load_settings(settings_path: Path | None = None) -> AppSettings:
    """Carga settings.json o devuelve valores por defecto si no existe o está dañado."""
    path = settings_path or cfg.FILE_SETTINGS
    if not path.exists():
        return AppSettings(work_dir=str(cfg.APP_DIR))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return AppSettings(work_dir=str(cfg.APP_DIR))
        return AppSettings(
            work_dir=str(raw.get("work_dir", str(cfg.APP_DIR))),
            vault_enabled=bool(raw.get("vault_enabled", False)),
            pdf_owner_protect=bool(raw.get("pdf_owner_protect", False)),
        )
    except (json.JSONDecodeError, OSError):
        return AppSettings(work_dir=str(cfg.APP_DIR))


def save_settings(settings: AppSettings, settings_path: Path | None = None) -> None:
    """Guarda settings.json de forma atómica."""
    path = settings_path or cfg.FILE_SETTINGS
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _merge_tree(src: Path, dst: Path, move: bool) -> int:
    """Copia o mueve archivos de src a dst preservando estructura sin borrar destino previo."""
    if not src.exists():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                if move:
                    shutil.move(str(item), str(target))
                else:
                    shutil.copy2(str(item), str(target))
                count += 1
            elif move:
                # Si ya existe en destino con el mismo nombre, evitamos sobrescribirlo
                pass
    if move:
        # Limpiar subcarpetas vacías que quedaron tras mover
        try:
            for root_dir, dirs, files in os.walk(src, topdown=False):
                rp = Path(root_dir)
                if not any(rp.iterdir()):
                    rp.rmdir()
        except OSError:
            pass
    return count


def migrate_work_dir(
    old_dir: Path,
    new_dir: Path,
    mode: Literal["copy", "move"] = "copy",
) -> int:
    """
    Migra datos/, 01_Escaneos_Originales/ y 02_Actas_Con_Hash/ desde old_dir hacia new_dir.
    Retorna la cantidad de archivos trasladados.
    """
    old_resolved = Path(old_dir).resolve()
    new_resolved = Path(new_dir).resolve()
    if old_resolved == new_resolved:
        return 0

    new_resolved.mkdir(parents=True, exist_ok=True)
    move_flag = mode == "move"
    total = 0

    for folder_name in ("datos", "01_Escaneos_Originales", "02_Actas_Con_Hash"):
        src_folder = old_resolved / folder_name
        dst_folder = new_resolved / folder_name
        total += _merge_tree(src_folder, dst_folder, move=move_flag)

    return total
