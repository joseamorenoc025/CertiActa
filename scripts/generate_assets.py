"""
Genera el logotipo institucional de CertiActa en alta resolución (assets/logo.png)
y el icono multi-resolución para Windows (assets/icon.ico) usando PyMuPDF + Pillow.
"""

from pathlib import Path
import fitz
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


def build_logo() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logo_path = ASSETS_DIR / "logo.png"
    icon_path = ASSETS_DIR / "icon.ico"

    # Renderizado vectorial en lienzo cuadrado 512x512 con zoom 2x -> 1024x1024
    doc = fitz.open()
    page = doc.new_page(width=512, height=512)

    navy = (0.094, 0.133, 0.188)       # #182230
    royal = (0.122, 0.416, 0.647)      # #1f6aa5
    light_blue = (0.88, 0.93, 0.98)    # #e0edf9
    white = (1.0, 1.0, 1.0)
    emerald = (0.180, 0.627, 0.263)    # #2ea043
    slate = (0.55, 0.62, 0.70)

    # 1. Fondo circular/escudo redondeado institucional
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(24, 24, 488, 488), radius=0.22)
    shape.finish(fill=navy, color=royal, width=8)
    shape.commit()

    # 2. Documento / Acta estilizada en el centro-izquierda
    doc_rect = fitz.Rect(118, 92, 344, 392)
    s_doc = page.new_shape()
    s_doc.draw_rect(doc_rect, radius=0.06)
    s_doc.finish(fill=white, color=light_blue, width=3)
    s_doc.commit()

    # Encabezado azul del acta
    header_rect = fitz.Rect(118, 92, 344, 146)
    s_hdr = page.new_shape()
    s_hdr.draw_rect(header_rect, radius=0.06)
    s_hdr.finish(fill=royal, color=royal, width=1)
    s_hdr.commit()

    # Líneas simulando texto oficial del acta
    s_lines = page.new_shape()
    for idx, y in enumerate([178, 208, 238, 268, 298]):
        x_end = 312 if idx != 4 else 255
        s_lines.draw_line(fitz.Point(150, y), fitz.Point(x_end, y))
    s_lines.finish(color=slate, width=8, lineCap=1)
    s_lines.commit()

    # Franja inferior simulando el pie de hash SHA-256
    s_hash = page.new_shape()
    s_hash.draw_rect(fitz.Rect(146, 338, 316, 364), radius=0.2)
    s_hash.finish(fill=light_blue, color=royal, width=1.5)
    s_hash.commit()

    # 3. Escudo / Sello esmeralda de verificación en esquina inferior derecha
    cx, cy, r = 344, 348, 86
    s_badge_bg = page.new_shape()
    s_badge_bg.draw_circle(fitz.Point(cx, cy), r + 10)
    s_badge_bg.finish(fill=navy, color=navy)
    s_badge_bg.commit()

    s_badge = page.new_shape()
    s_badge.draw_circle(fitz.Point(cx, cy), r)
    s_badge.finish(fill=emerald, color=white, width=5)
    s_badge.commit()

    # Checkmark blanco nítido dentro del sello
    s_chk = page.new_shape()
    s_chk.draw_polyline([
        fitz.Point(cx - 34, cy + 2),
        fitz.Point(cx - 8, cy + 28),
        fitz.Point(cx + 38, cy - 26),
    ])
    s_chk.finish(color=white, width=16, lineCap=1, lineJoin=1)
    s_chk.commit()

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=True)
    pix.save(str(logo_path))
    doc.close()

    # Generar .ico multi-resolución para Windows
    img = Image.open(logo_path).convert("RGBA")
    img.save(
        icon_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Assets generados: {logo_path} y {icon_path}")


if __name__ == "__main__":
    build_logo()
