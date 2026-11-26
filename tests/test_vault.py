"""
Pruebas unitarias para la Bóveda Criptográfica (AES-256-GCM, Frase Semilla, archivo .key)
y persistencia cifrada en RegistryRepository.
"""

from pathlib import Path
import pytest

from src.core.models import ActaRecord
from src.core.vault import VaultError, VaultManager
from src.repository.registry_repo import RegistryRepository


def test_vault_creacion_desbloqueo_y_semilla(tmp_path: Path):
    vault_path = tmp_path / "vault.json"
    vault = VaultManager(vault_path)

    assert not vault.is_initialized()
    assert not vault.is_unlocked()

    seed = vault.create_vault("ClaveSecreta2026")
    assert len(seed.split()) == 12
    assert vault.is_initialized()
    assert vault.is_unlocked()

    # Bloquear y probar contraseña incorrecta / correcta
    vault.lock()
    assert not vault.is_unlocked()
    assert vault.unlock_with_password("Incorrecta") is False
    assert vault.unlock_with_password("ClaveSecreta2026") is True
    assert vault.is_unlocked()

    # Recuperar con Frase Semilla (incluso con espacios extra y mayúsculas)
    vault.lock()
    seed_sucia = f"  {seed.upper().replace(' ', '   ')}  "
    assert vault.recover_with_seed("palabra1 palabra2 invalida", "NuevaClave99") is False
    assert vault.recover_with_seed(seed_sucia, "NuevaClave99") is True

    # La contraseña anterior ya no sirve; la nueva sí
    vault.lock()
    assert vault.unlock_with_password("ClaveSecreta2026") is False
    assert vault.unlock_with_password("NuevaClave99") is True


def test_vault_archivo_key_y_repositorio_cifrado(tmp_path: Path):
    vault_path = tmp_path / "datos" / "vault.json"
    json_path = tmp_path / "datos" / "registro_actas.json"
    key_path = tmp_path / "usb_respaldo.key"

    vault = VaultManager(vault_path)
    repo = RegistryRepository(json_path=json_path, vault=vault)

    # Agregar registro en texto plano primero
    rec = ActaRecord.create(
        tipo_sesion="Ordinaria",
        num_sesion="050-2026",
        fecha_sesion="26/11/2026",
        observacion="Prueba bóveda",
        nombre_archivo_original="acta_50.pdf",
        ruta_archivo_original="/r/acta_50.pdf",
        nombre_archivo_con_hash="acta_50_CON_HASH.pdf",
        ruta_archivo_con_hash="/r/acta_50_CON_HASH.pdf",
        sha256_original="a" * 64,
        total_paginas=3,
        sha256_con_hash="b" * 64,
    )
    repo.add(rec)
    assert json_path.exists()

    # Activar bóveda y migrar a .enc
    vault.create_vault("MiClaveFuerte")
    repo.migrate_to_encrypted()
    assert not json_path.exists()
    assert repo.enc_path.exists()

    # Exportar archivo .key
    vault.export_key_file(key_path)
    assert key_path.exists()

    # Bloquear y recuperar con archivo .key
    vault.lock()
    assert repo.get_all() == []  # Bloqueada no expone registros
    assert vault.recover_with_key_file(key_path, "ClaveRecuperada123") is True

    # Verificar que el registro sobrevivió intacto al cambio de contraseña vía .key
    registros = repo.get_all()
    assert len(registros) == 1
    assert registros[0].num_sesion == "050-2026"

    # Desactivar cifrado vuelve a JSON plano sin perder datos
    repo.migrate_to_plaintext()
    vault.remove_vault()
    assert json_path.exists()
    assert not repo.enc_path.exists()
    assert len(repo.get_all()) == 1


def test_vault_rechaza_clave_corta(tmp_path: Path):
    vault = VaultManager(tmp_path / "vault.json")
    with pytest.raises(VaultError):
        vault.create_vault("123")
