"""
Módulo de estampado de pie de página y metadatos en documentos PDF usando PyMuPDF (fitz).
Garantiza que el PDF escaneado original nunca sea alterado ni sobrescrito.
"""

from pathlib import Path
import shutil
from typing import Optional
import fitz  # PyMuPDF

from src.config import DIR_CON_HASH, DIR_ORIGINALES
from src.core.hasher import calcular_sha256


class PDFStampError(Exception):
    """Excepción para errores ocurridos durante el proceso de estampado de PDFs."""
    pass


def estampar_acta_pdf(
    ruta_original: Path,
    tipo_sesion: str,
    num_sesion: str,
    fecha_sesion: str,
    guardar_copia_en_originales: bool = True,
    hash_precalculado: Optional[str] = None,
    es_sustitucion: bool = False,
) -> tuple[Path, str, str, int, Path]:
    """
    Procesa un PDF original escaneado:
    1. Calcula su hash SHA-256 intacto.
    2. Opcionalmente guarda una copia idéntica e intacta en `01_Escaneos_Originales/`.
    3. Genera un nuevo PDF en `02_Actas_Con_Hash/` con el sufijo `_CON_HASH.pdf`.
    4. En cada página estampa el pie de página con fondo blanco de seguridad y las dos líneas requeridas.
    5. Inyecta el hash original en los metadatos del nuevo PDF para auditoría forense.
    6. Calcula el hash SHA-256 del PDF generado para verificación posterior.

    Returns:
        Tupla: (ruta_pdf_con_hash, sha256_original, sha256_con_hash, total_paginas, ruta_resguardo_original)
    """
    path_orig = Path(ruta_original).resolve()
    if not path_orig.is_file():
        raise FileNotFoundError(f"El archivo original no existe: {path_orig}")

    if path_orig.suffix.lower() != ".pdf":
        raise PDFStampError(f"El archivo no es un documento PDF válido: {path_orig.name}")

    # 1. Cálculo del hash del archivo original 100% intacto
    sha256_hash = hash_precalculado or calcular_sha256(path_orig)

    # 2. Resguardo inmutable en 01_Escaneos_Originales si se solicita y no está ya allí
    DIR_ORIGINALES.mkdir(parents=True, exist_ok=True)
    DIR_CON_HASH.mkdir(parents=True, exist_ok=True)

    ruta_resguardo = DIR_ORIGINALES / path_orig.name
    # Si la ruta seleccionada no es ya la que está en DIR_ORIGINALES, copiamos
    if guardar_copia_en_originales and path_orig != ruta_resguardo:
        try:
            if ruta_resguardo.exists():
                # Si ya existe un archivo con ese nombre pero distinto hash, usamos un sufijo seguro
                existente_hash = calcular_sha256(ruta_resguardo)
                if existente_hash != sha256_hash:
                    stem = path_orig.stem
                    ruta_resguardo = DIR_ORIGINALES / f"{stem}_{sha256_hash[:8]}.pdf"
                    shutil.copy2(path_orig, ruta_resguardo)
            else:
                shutil.copy2(path_orig, ruta_resguardo)
        except PermissionError as pe:
            raise PDFStampError(
                "El archivo PDF de destino está abierto en otro programa (Adobe Reader, Edge, etc.). "
                "Ciérrelo e intente nuevamente."
            ) from pe
    elif not guardar_copia_en_originales:
        ruta_resguardo = path_orig

    # 3. Definir nombre y ruta de salida en 02_Actas_Con_Hash (con prevención de colisiones)
    nombre_base = path_orig.stem
    nombre_salida = f"{nombre_base}_CON_HASH.pdf"
    ruta_salida = DIR_CON_HASH / nombre_salida
    if ruta_salida.exists() and not es_sustitucion:
        ruta_salida = DIR_CON_HASH / f"{nombre_base}_{sha256_hash[:8]}_CON_HASH.pdf"

    doc = None
    try:
        # Abrimos el original en modo lectura
        doc = fitz.open(str(path_orig))

        if doc.is_encrypted:
            doc.close()
            doc = None
            raise PDFStampError(
                "El archivo PDF está encriptado o protegido con contraseña. "
                "Desbloquéelo antes de procesarlo."
            )

        total_paginas = len(doc)

        if total_paginas == 0:
            doc.close()
            doc = None
            raise PDFStampError("El archivo PDF está vacío o no contiene páginas legibles.")

        # Recorremos cada página para estampar la leyenda
        for num_pagina, pagina in enumerate(doc, start=1):
            rect = pagina.rect  # Dimensiones de la página (x0, y0, x1, y1)
            ancho = rect.width
            alto = rect.height

            # Altura de la barra del pie de página (32 puntos tipográficos)
            alto_pie = 32.0
            margen_horizontal = 25.0
            
            y_base = alto - alto_pie
            rect_fondo = fitz.Rect(0, y_base, ancho, alto)

            # Dibujamos una franja de fondo blanco con línea divisoria superior sutil
            # para evitar que artefactos del escáner hagan ilegible el texto
            forma = pagina.new_shape()
            forma.draw_rect(rect_fondo)
            forma.finish(
                fill=(1, 1, 1),           # Fondo blanco sólido
                color=(0.82, 0.84, 0.86), # Borde superior gris claro tenue
                width=0.75,
                fill_opacity=0.96         # Ligera opacidad para máxima nitidez
            )
            forma.commit()

            # Textos a estampar
            linea_1 = (
                f"Sesión: {tipo_sesion} | N.°: {num_sesion} | "
                f"Fecha: {fecha_sesion} | Pág. {num_pagina} de {total_paginas}"
            )
            linea_2 = (
                f"Esta acta es verificable mediante el siguiente código hash SHA-256 "
                f"(escaneo original): {sha256_hash}"
            )

            # Ajuste dinámico de tamaño de fuente según el ancho de página
            ancho_disponible = ancho - (2 * margen_horizontal)

            len_1 = fitz.get_text_length(linea_1, fontname="helv", fontsize=8.0)
            font_size_1 = 8.0 if len_1 <= ancho_disponible else max(6.0, 8.0 * (ancho_disponible / len_1))

            len_2 = fitz.get_text_length(linea_2, fontname="helv", fontsize=7.2)
            font_size_2 = 7.2 if len_2 <= ancho_disponible else max(5.5, 7.2 * (ancho_disponible / len_2))

            # Inserción de Línea 1 (Metadatos de sesión y página)
            pagina.insert_text(
                point=(margen_horizontal, alto - 19),
                text=linea_1,
                fontsize=font_size_1,
                fontname="helv",
                color=(0.12, 0.15, 0.18), # Azul marino muy oscuro
            )

            # Inserción de Línea 2 (Leyenda de verificación y hash)
            pagina.insert_text(
                point=(margen_horizontal, alto - 8),
                text=linea_2,
                fontsize=font_size_2,
                fontname="helv",
                color=(0.18, 0.22, 0.25),
            )

        # Inyectar metadatos forenses en el PDF resultante
        meta = doc.metadata.copy() if doc.metadata else {}
        meta["keywords"] = f"SHA256_ORIGINAL:{sha256_hash}; SESION:{tipo_sesion}-{num_sesion}"
        meta["producer"] = "Verificador de Actas - Hash SHA-256 (PyMuPDF Engine)"
        doc.set_metadata(meta)

        # Guardar en nuevo archivo con compresión y linearización
        try:
            doc.save(
                str(ruta_salida),
                garbage=4,
                deflate=True,
                clean=True,
            )
        except PermissionError as pe:
            raise PDFStampError(
                "El archivo PDF de destino está abierto en otro programa (Adobe Reader, Edge, etc.). "
                "Ciérrelo e intente nuevamente."
            ) from pe
        finally:
            if doc is not None:
                doc.close()
                doc = None

    except Exception as e:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
        if isinstance(e, PDFStampError):
            raise
        raise PDFStampError(f"Ocurrió un error al procesar el PDF con PyMuPDF: {str(e)}") from e

    # 6. Calcular el hash SHA-256 del PDF generado (con la leyenda ya estampada)
    sha256_generado = calcular_sha256(ruta_salida)

    return ruta_salida, sha256_hash, sha256_generado, total_paginas, ruta_resguardo
