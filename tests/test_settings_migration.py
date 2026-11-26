"""
Pruebas unitarias para preferencias persistentes (settings.json) y migración de Carpeta de Trabajo.
"""

from pathlib import Path
import src.config as cfg
from src.core.settings import AppSettings, load_settings, migrate_work_dir, save_settings


def test_settings_guardar_y_cargar(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    s = AppSettings(work_dir=str(tmp_path / "Boveda"), vault_enabled=True, pdf_owner_protect=True)
    save_settings(s, settings_path=settings_file)

    loaded = load_settings(settings_path=settings_file)
    assert loaded.work_dir == str(tmp_path / "Boveda")
    assert loaded.vault_enabled is True
    assert loaded.pdf_owner_protect is True


def test_migrar_carpeta_trabajo_copia_y_movimiento(tmp_path: Path):
    old_dir = tmp_path / "origen"
    new_dir = tmp_path / "destino"

    for sub in ("datos", "01_Escaneos_Originales", "02_Actas_Con_Hash"):
        (old_dir / sub).mkdir(parents=True)

    (old_dir / "datos" / "registro_actas.json").write_text('[{"id":"1"}]', encoding="utf-8")
    (old_dir / "01_Escaneos_Originales" / "acta.pdf").write_bytes(b"orig")
    (old_dir / "02_Actas_Con_Hash" / "acta_CON_HASH.pdf").write_bytes(b"hash")

    # 1. Modo copia: conserva origen y replica en destino
    copied = migrate_work_dir(old_dir, new_dir, mode="copy")
    assert copied == 3
    assert (old_dir / "01_Escaneos_Originales" / "acta.pdf").exists()
    assert (new_dir / "01_Escaneos_Originales" / "acta.pdf").read_bytes() == b"orig"
    assert (new_dir / "02_Actas_Con_Hash" / "acta_CON_HASH.pdf").read_bytes() == b"hash"

    # 2. Modo movimiento hacia una tercera carpeta
    third_dir = tmp_path / "destino_final"
    moved = migrate_work_dir(new_dir, third_dir, mode="move")
    assert moved == 3
    assert (third_dir / "datos" / "registro_actas.json").exists()
    assert not (new_dir / "01_Escaneos_Originales" / "acta.pdf").exists()


def test_apply_work_dir_actualiza_rutas(tmp_path: Path):
    prev = cfg.BASE_DIR
    try:
        custom = tmp_path / "Clebda_Archivo"
        cfg.apply_work_dir(custom)
        assert cfg.BASE_DIR == custom.resolve()
        assert cfg.DIR_ORIGINALES == custom.resolve() / "01_Escaneos_Originales"
        assert cfg.FILE_VAULT == custom.resolve() / "datos" / "vault.json"
    finally:
        cfg.apply_work_dir(prev)
