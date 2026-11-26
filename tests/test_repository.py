"""
Pruebas unitarias para el repositorio de registros con soporte de doble huella.
"""

from pathlib import Path
from src.core.models import ActaRecord
from src.repository.registry_repo import RegistryRepository


def test_repositorio_crud_y_busqueda(tmp_path: Path):
    json_path = tmp_path / "test_registro.json"
    repo = RegistryRepository(json_path)

    # 1. Al inicio está vacío
    assert repo.get_all() == []

    # 2. Agregar registro con doble huella
    record1 = ActaRecord.create(
        tipo_sesion="Ordinaria",
        num_sesion="014-2026",
        fecha_sesion="24/11/2026",
        observacion="Aprobación de presupuesto",
        nombre_archivo_original="acta_014.pdf",
        ruta_archivo_original="/ruta/acta_014.pdf",
        nombre_archivo_con_hash="acta_014_CON_HASH.pdf",
        ruta_archivo_con_hash="/ruta/acta_014_CON_HASH.pdf",
        sha256_original="a" * 64,
        total_paginas=3,
        sha256_con_hash="b" * 64,
    )
    repo.add(record1)

    todos = repo.get_all()
    assert len(todos) == 1
    assert todos[0].num_sesion == "014-2026"
    assert todos[0].sha256_original == "a" * 64
    assert todos[0].sha256_con_hash == "b" * 64

    # 3. Buscar por hash original
    encontrado = repo.find_by_hash("A" * 64)  # Case insensitive
    assert encontrado is not None
    assert encontrado.id == record1.id

    # 4. Buscar por hash del generado
    encontrado_gen = repo.find_by_hash("B" * 64)  # Case insensitive
    assert encontrado_gen is not None
    assert encontrado_gen.id == record1.id

    # 5. Búsqueda de texto en tiempo real (incluye sha256_con_hash)
    assert len(repo.search("presupuesto")) == 1
    assert len(repo.search("014")) == 1
    assert len(repo.search("bbb")) == 1  # Búsqueda parcial en sha256_con_hash
    assert len(repo.search("inexistente")) == 0

    # 6. Exportar a CSV con ambas columnas de hash
    csv_salida = tmp_path / "export_test.csv"
    repo.export_to_csv(output_path=csv_salida)
    assert csv_salida.exists()
    contenido_csv = csv_salida.read_text(encoding="utf-8-sig")
    assert "014-2026" in contenido_csv
    assert "Aprobación de presupuesto" in contenido_csv
    assert "SHA-256 Original" in contenido_csv
    assert "SHA-256 PDF Generado" in contenido_csv
    assert "b" * 64 in contenido_csv


def test_compatibilidad_registros_antiguos_sin_sha256_con_hash(tmp_path: Path):
    """Verifica que registros previos sin sha256_con_hash se lean correctamente."""
    import json

    json_path = tmp_path / "legacy_registro.json"
    legacy_data = [{
        "id": "legacy-001",
        "fecha_registro": "2026-01-01 10:00:00",
        "tipo_sesion": "Extraordinaria",
        "num_sesion": "001-2026",
        "fecha_sesion": "01/01/2026",
        "observacion": "Registro antiguo sin sha256_con_hash",
        "nombre_archivo_original": "acta_001.pdf",
        "ruta_archivo_original": "/ruta/acta_001.pdf",
        "nombre_archivo_con_hash": "acta_001_CON_HASH.pdf",
        "ruta_archivo_con_hash": "/ruta/acta_001_CON_HASH.pdf",
        "sha256_original": "c" * 64,
        "total_paginas": 5,
        # NO incluye sha256_con_hash — simulando un registro guardado antes de esta actualización
    }]
    json_path.write_text(json.dumps(legacy_data, ensure_ascii=False), encoding="utf-8")

    repo = RegistryRepository(json_path)
    registros = repo.get_all()
    assert len(registros) == 1
    assert registros[0].sha256_con_hash == ""  # Valor por defecto vacío
    assert registros[0].sha256_original == "c" * 64
    assert registros[0].observacion == "Registro antiguo sin sha256_con_hash"

    # Buscar por hash original debe seguir funcionando
    encontrado = repo.find_by_hash("C" * 64)
    assert encontrado is not None
    assert encontrado.id == "legacy-001"


def test_sobrescritura_silenciosa_por_sesion_y_ficha_libro_fisico(tmp_path: Path):
    """
    Si se vuelve a estampar la misma sesión (ej. Ordinaria 12-2026) con un archivo modificado
    y hashes nuevos, el registro debe actualizarse silenciosamente sin duplicarse.
    """
    json_path = tmp_path / "upsert_registro.json"
    repo = RegistryRepository(json_path)

    rec_marzo = ActaRecord.create(
        tipo_sesion="Ordinaria",
        num_sesion="12-2026",
        fecha_sesion="15/03/2026",
        observacion="Versión inicial marzo",
        nombre_archivo_original="acta_12.pdf",
        ruta_archivo_original="/ruta/acta_12.pdf",
        nombre_archivo_con_hash="acta_12_CON_HASH.pdf",
        ruta_archivo_con_hash="/ruta/acta_12_CON_HASH.pdf",
        sha256_original="1" * 64,
        total_paginas=4,
        sha256_con_hash="2" * 64,
    )
    repo.add(rec_marzo)
    assert len(repo.get_all()) == 1

    # En abril se corrige y se vuelve a estampar la misma sesión (Ordinaria 12-2026)
    rec_abril = ActaRecord.create(
        tipo_sesion="ordinaria",
        num_sesion=" 12-2026 ",
        fecha_sesion="15/03/2026",
        observacion="Versión corregida abril",
        nombre_archivo_original="acta_12_corregida.pdf",
        ruta_archivo_original="/ruta/acta_12_corregida.pdf",
        nombre_archivo_con_hash="acta_12_corregida_CON_HASH.pdf",
        ruta_archivo_con_hash="/ruta/acta_12_corregida_CON_HASH.pdf",
        sha256_original="3" * 64,
        total_paginas=5,
        sha256_con_hash="4" * 64,
    )
    repo.add(rec_abril)

    todos = repo.get_all()
    assert len(todos) == 1, "No debe duplicar la sesión al sobrescribirse"
    actualizado = todos[0]
    assert actualizado.sha256_original == "3" * 64
    assert actualizado.sha256_con_hash == "4" * 64
    assert actualizado.total_paginas == 5

    # Verificar ficha para Libro Físico con los hashes actualizados
    ficha = actualizado.format_ficha_libro_fisico()
    assert "12-2026" in ficha
    assert "3" * 64 in ficha
    assert "4" * 64 in ficha


def test_find_by_sesion(tmp_path: Path):
    """Verifica búsqueda exacta por tipo y número de sesión (insensible a mayúsculas/espacios)."""
    repo = RegistryRepository(tmp_path / "sesion_lookup.json")
    rec = ActaRecord.create(
        tipo_sesion="Extraordinaria",
        num_sesion="007-2026",
        fecha_sesion="20/04/2026",
        observacion="",
        nombre_archivo_original="ext_007.pdf",
        ruta_archivo_original="/r/ext_007.pdf",
        nombre_archivo_con_hash="ext_007_CON_HASH.pdf",
        ruta_archivo_con_hash="/r/ext_007_CON_HASH.pdf",
        sha256_original="e" * 64,
        total_paginas=2,
        sha256_con_hash="f" * 64,
    )
    repo.add(rec)

    assert repo.find_by_sesion("extraordinaria", " 007-2026 ") is not None
    assert repo.find_by_sesion("Ordinaria", "007-2026") is None
    assert repo.find_by_sesion("Extraordinaria", "") is None


def test_backup_zip(tmp_path: Path, monkeypatch):
    """Verifica la generación del archivo ZIP de respaldo preventivo."""
    import zipfile
    import src.ui.tab_records as tab_rec_mod

    file_reg = tmp_path / "datos" / "registro_actas.json"
    dir_orig = tmp_path / "01_Escaneos_Originales"
    dir_hash = tmp_path / "02_Actas_Con_Hash"
    dir_exp = tmp_path / "datos" / "exportaciones"

    file_reg.parent.mkdir(parents=True)
    dir_orig.mkdir()
    dir_hash.mkdir()

    file_reg.write_text("[]", encoding="utf-8")
    (dir_orig / "orig_01.pdf").write_bytes(b"orig")
    (dir_hash / "orig_01_CON_HASH.pdf").write_bytes(b"hash")

    monkeypatch.setattr(tab_rec_mod, "FILE_REGISTRO", file_reg)
    monkeypatch.setattr(tab_rec_mod, "DIR_ORIGINALES", dir_orig)
    monkeypatch.setattr(tab_rec_mod, "DIR_CON_HASH", dir_hash)

    zip_path = tab_rec_mod.TabRecords.crear_respaldo_zip(output_dir=dir_exp)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert "datos/registro_actas.json" in names
        assert "01_Escaneos_Originales/orig_01.pdf" in names
        assert "02_Actas_Con_Hash/orig_01_CON_HASH.pdf" in names
