"""
Pruebas unitarias para el estampado de PDFs, garantía de inmutabilidad del original
y validación del sistema de doble huella SHA-256.
"""

from pathlib import Path
import fitz
from src.core.hasher import calcular_sha256, verificar_sha256
from src.core.pdf_stamper import estampar_acta_pdf


def test_estampar_pdf_integridad_original(tmp_path: Path):
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
