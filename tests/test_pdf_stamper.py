"""
Pruebas unitarias para el estampado de PDFs, garantía de inmutabilidad del original
y validación del sistema de doble huella SHA-256.
"""

from pathlib import Path
import fitz
import pytest

import src.core.pdf_stamper as pdf_stamper_mod
from src.core.hasher import calcular_sha256, verificar_sha256
from src.core.pdf_stamper import PDFStampError, estampar_acta_pdf


def test_estampar_pdf_integridad_original(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pdf_stamper_mod, "DIR_ORIGINALES", tmp_path / "01_Escaneos_Originales")
    monkeypatch.setattr(pdf_stamper_mod, "DIR_CON_HASH", tmp_path / "02_Actas_Con_Hash")

    # 1. Crear un PDF de prueba de 2 páginas simulando un acta escaneada
    pdf_original = tmp_path / "acta_escaneada_original.pdf"
    doc_creado = fitz.open()
    
    # Página 1
    p1 = doc_creado.new_page(width=595, height=842) # A4
    p1.insert_text((50, 100), "Acta de Sesión Ordinaria N° 01/2026", fontsize=14)
    p1.insert_text((50, 200), "Página de acuerdos y firmas...", fontsize=11)
    
    # Página 2
    p2 = doc_creado.new_page(width=595, height=842)
    p2.insert_text((50, 100), "Segunda página de firmas y sellos oficiales.", fontsize=11)
    
    doc_creado.save(str(pdf_original))
    doc_creado.close()

    # 2. Tomar el hash del original antes de estampar
    hash_antes = calcular_sha256(pdf_original)

    # 3. Estampar acta
    ruta_con_hash, sha_original, sha_generado, total_pags, ruta_resguardo = estampar_acta_pdf(
        ruta_original=pdf_original,
        tipo_sesion="Ordinaria",
        num_sesion="001-2026",
        fecha_sesion="24/11/2026",
        guardar_copia_en_originales=True,
    )

    # 4. REGLA FUNDAMENTAL: El original NUNCA debe modificarse
    hash_despues = calcular_sha256(pdf_original)
    assert hash_antes == hash_despues, "¡El archivo original fue alterado!"
    assert sha_original == hash_antes

    # 5. Comprobar que el archivo resultante existe y tiene el contenido esperado
    assert ruta_con_hash.exists()
    assert ruta_con_hash.name == "acta_escaneada_original_CON_HASH.pdf"
    assert total_pags == 2

    # El hash del nuevo archivo debe ser diferente al original (porque tiene el sello impreso)
    hash_nuevo = calcular_sha256(ruta_con_hash)
    assert hash_nuevo != hash_antes

    # 6. DOBLE HUELLA: sha256_con_hash debe coincidir con el hash real del PDF generado
    assert len(sha_generado) == 64
    assert sha_generado == hash_nuevo, (
        "El sha256_con_hash reportado no coincide con el hash real del archivo generado"
    )
    assert sha_generado != sha_original, (
        "sha256_con_hash debe ser distinto de sha256_original"
    )

    # 7. Verificación directa: el hash del generado debe verificar contra sí mismo
    coincide, h = verificar_sha256(ruta_con_hash, sha_generado)
    assert coincide is True, "El PDF generado no verifica contra su propio hash reportado"

    # 8. Inspeccionar el nuevo PDF con PyMuPDF
    doc_verif = fitz.open(str(ruta_con_hash))
    assert len(doc_verif) == 2
    for num, pag in enumerate(doc_verif, start=1):
        texto = pag.get_text()
        assert "Sesión: Ordinaria" in texto
        assert "N.°: 001-2026" in texto
        assert f"Pág. {num} de 2" in texto
        assert hash_antes in texto
    
    # Comprobar metadatos forenses inyectados
    assert "SHA256_ORIGINAL" in doc_verif.metadata.get("keywords", "")
    doc_verif.close()


def test_collision_prevention_con_hash(tmp_path: Path, monkeypatch):
    """Dos PDFs distintos con el mismo nombre (ej. escaner_001.pdf) no deben sobrescribirse."""
    dir_orig = tmp_path / "01_Escaneos_Originales"
    dir_hash = tmp_path / "02_Actas_Con_Hash"
    monkeypatch.setattr(pdf_stamper_mod, "DIR_ORIGINALES", dir_orig)
    monkeypatch.setattr(pdf_stamper_mod, "DIR_CON_HASH", dir_hash)

    pdf1 = tmp_path / "lote1" / "escaner_001.pdf"
    pdf2 = tmp_path / "lote2" / "escaner_001.pdf"
    pdf1.parent.mkdir()
    pdf2.parent.mkdir()

    for idx, p in enumerate((pdf1, pdf2), start=1):
        d = fitz.open()
        page = d.new_page()
        page.insert_text((50, 100), f"Contenido exclusivo del acta {idx}", fontsize=12)
        d.save(str(p))
        d.close()

    out1, sha1, _, _, _ = estampar_acta_pdf(pdf1, "Ordinaria", "001-2026", "10/03/2026")
    out2, sha2, _, _, _ = estampar_acta_pdf(pdf2, "Ordinaria", "002-2026", "11/03/2026")

    assert out1.exists()
    assert out2.exists()
    assert out1 != out2
    assert out1.name == "escaner_001_CON_HASH.pdf"
    assert out2.name == f"escaner_001_{sha2[:8]}_CON_HASH.pdf"


def test_encrypted_pdf_rejection(tmp_path: Path, monkeypatch):
    """Un PDF protegido con contraseña debe ser rechazado con PDFStampError."""
    monkeypatch.setattr(pdf_stamper_mod, "DIR_ORIGINALES", tmp_path / "orig")
    monkeypatch.setattr(pdf_stamper_mod, "DIR_CON_HASH", tmp_path / "hash")

    pdf_enc = tmp_path / "protegido.pdf"
    d = fitz.open()
    d.new_page().insert_text((50, 100), "Secreto")
    d.save(
        str(pdf_enc),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner123",
        user_pw="user123",
    )
    d.close()

    with pytest.raises(PDFStampError, match="encriptado"):
        estampar_acta_pdf(pdf_enc, "Especial", "005-2026", "12/03/2026")


def test_rotated_page_stamping(tmp_path: Path, monkeypatch):
    """El estampado debe funcionar correctamente en páginas con rotación de 90 grados."""
    monkeypatch.setattr(pdf_stamper_mod, "DIR_ORIGINALES", tmp_path / "orig")
    monkeypatch.setattr(pdf_stamper_mod, "DIR_CON_HASH", tmp_path / "hash")

    pdf_rot = tmp_path / "rotado.pdf"
    d = fitz.open()
    page = d.new_page(width=595, height=842)
    page.set_rotation(90)
    page.insert_text((50, 100), "Acta en orientación horizontal")
    d.save(str(pdf_rot))
    d.close()

    out_path, sha_orig, sha_gen, total_pags, _ = estampar_acta_pdf(
        pdf_rot, "Solemne", "009-2026", "15/03/2026"
    )
    assert out_path.exists()
    assert total_pags == 1
    assert len(sha_gen) == 64

    verif = fitz.open(str(out_path))
    assert sha_orig in verif[0].get_text()
    verif.close()


def test_pdf_owner_protection_lectura_libre_sin_edicion(tmp_path: Path, monkeypatch):
    """Con owner_password, el PDF se abre sin clave para lectura, pero bloquea edición."""
    monkeypatch.setattr(pdf_stamper_mod, "DIR_ORIGINALES", tmp_path / "orig")
    monkeypatch.setattr(pdf_stamper_mod, "DIR_CON_HASH", tmp_path / "hash")

    pdf_in = tmp_path / "acta_protegida.pdf"
    d = fitz.open()
    d.new_page().insert_text((50, 100), "Contenido oficial")
    d.save(str(pdf_in))
    d.close()

    out_path, _, sha_gen, _, _ = estampar_acta_pdf(
        pdf_in,
        "Ordinaria",
        "020-2026",
        "26/11/2026",
        owner_password="OwnerSecretPassword123",
    )

    doc_out = fitz.open(str(out_path))
    assert doc_out.needs_pass == 0  # Lectura libre para legisladores y Contraloría
    assert (doc_out.permissions & fitz.PDF_PERM_MODIFY) == 0
    assert doc_out.authenticate("OwnerSecretPassword123") > 0
    assert (doc_out.permissions & fitz.PDF_PERM_MODIFY) != 0
    doc_out.close()

    ok, _ = verificar_sha256(out_path, sha_gen)
    assert ok is True
