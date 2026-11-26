"""
Generador reproducible del Manual de Usuario oficial de CertiActa en PDF.
Produce docs/Manual_de_Usuario.pdf usando PyMuPDF (fitz) con portada,
diagramas vectoriales, tablas y secciones diferenciadas por rol institucional.
"""

from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"

NAVY = (0.094, 0.133, 0.188)       # #182230
ROYAL = (0.122, 0.416, 0.647)      # #1f6aa5
EMERALD = (0.169, 0.471, 0.259)    # #2b7842
EMERALD_BG = (0.91, 0.97, 0.92)
BLUE_BG = (0.92, 0.95, 0.99)
AMBER_BG = (0.99, 0.96, 0.89)
AMBER_BORDER = (0.78, 0.55, 0.10)
GRAY_BG = (0.95, 0.96, 0.97)
BORDER = (0.82, 0.85, 0.88)
TEXT_DARK = (0.12, 0.14, 0.17)
TEXT_MUTED = (0.38, 0.43, 0.49)
WHITE = (1.0, 1.0, 1.0)


class ManualPDFBuilder:
    """Constructor de páginas Carta (612 x 792 pt) con control automático de saltos."""

    def __init__(self):
        self.doc = fitz.open()
        self.width = 612.0
        self.height = 792.0
        self.margin_x = 52.0
        self.top_y = 66.0
        self.bottom_y = 738.0
        self.content_w = self.width - 2 * self.margin_x
        self.page = None
        self.y = self.top_y

    def new_page(self, with_chrome: bool = True) -> None:
        self.page = self.doc.new_page(width=self.width, height=self.height)
        self.y = self.top_y if with_chrome else 48.0

    def ensure_space(self, needed_h: float) -> None:
        if self.y + needed_h > self.bottom_y:
            self.new_page(with_chrome=True)

    def draw_cover(self, logo_path: Path) -> None:
        self.new_page(with_chrome=False)
        p = self.page

        # Banda superior azul marino
        s = p.new_shape()
        s.draw_rect(fitz.Rect(0, 0, self.width, 210))
        s.finish(fill=NAVY, color=NAVY)
        s.commit()

        # Línea de acento esmeralda
        s2 = p.new_shape()
        s2.draw_rect(fitz.Rect(0, 210, self.width, 216))
        s2.finish(fill=EMERALD, color=EMERALD)
        s2.commit()

        # Logo centrado sobre la transición
        if logo_path.exists():
            logo_rect = fitz.Rect(self.width / 2 - 58, 128, self.width / 2 + 58, 244)
            p.insert_image(logo_rect, filename=str(logo_path))

        # Título principal en la banda superior
        p.insert_textbox(
            fitz.Rect(40, 46, self.width - 40, 95),
            "CertiActa",
            fontsize=32,
            fontname="hebo",
            color=WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        p.insert_textbox(
            fitz.Rect(50, 88, self.width - 50, 125),
            "Sistema Local de Integridad Documental y Verificación Criptográfica SHA-256",
            fontsize=12,
            fontname="helv",
            color=(0.82, 0.89, 0.96),
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Título del Manual
        p.insert_textbox(
            fitz.Rect(55, 272, self.width - 55, 345),
            "MANUAL DE USUARIO Y PROTOCOLO\nDE CONTROL DOCUMENTAL",
            fontsize=20,
            fontname="hebo",
            color=NAVY,
            align=fitz.TEXT_ALIGN_CENTER,
        )

        p.insert_textbox(
            fitz.Rect(70, 345, self.width - 70, 395),
            "Guía institucional dirigida a Diputados, Concejales, Legisladores,\n"
            "Secretarios de Cámara, Operadores y Auditores de Contraloría",
            fontsize=11.5,
            fontname="helv",
            color=TEXT_MUTED,
            align=fitz.TEXT_ALIGN_CENTER,
        )

        # Tarjeta de perfiles (3 columnas visuales)
        card_y = 420
        col_w = (self.content_w - 20) / 3
        perfiles = [
            ("Legisladores", "Comprensión clara de la\ninalterabilidad de actas\nfirmadas y selladas."),
            ("Secretaría y Operación", "Estampado, registro local\ny asiento en Libro Físico\nde Respaldo."),
            ("Contraloría y Auditoría", "Verificación matemática\ndoble huella y auditoría\nautónoma en Windows."),
        ]
        for idx, (titulo, desc) in enumerate(perfiles):
            x0 = self.margin_x + idx * (col_w + 10)
            rect = fitz.Rect(x0, card_y, x0 + col_w, card_y + 92)
            sh = p.new_shape()
            sh.draw_rect(rect, radius=0.08)
            sh.finish(fill=BLUE_BG, color=ROYAL, width=1)
            sh.commit()
            p.insert_textbox(
                fitz.Rect(x0 + 8, card_y + 10, x0 + col_w - 8, card_y + 32),
                titulo,
                fontsize=10.5,
                fontname="hebo",
                color=ROYAL,
                align=fitz.TEXT_ALIGN_CENTER,
            )
            p.insert_textbox(
                fitz.Rect(x0 + 8, card_y + 34, x0 + col_w - 8, card_y + 86),
                desc,
                fontsize=9,
                fontname="helv",
                color=TEXT_DARK,
                align=fitz.TEXT_ALIGN_CENTER,
            )

        # Ficha técnica y autoría al pie de portada
        ficha_rect = fitz.Rect(self.margin_x, 560, self.width - self.margin_x, 718)
        sf = p.new_shape()
        sf.draw_rect(ficha_rect, radius=0.05)
        sf.finish(fill=GRAY_BG, color=BORDER, width=1)
        sf.commit()

        ficha_texto = (
            "FICHA TÉCNICA Y AUTORÍA DEL PROYECTO\n\n"
            "- Aplicación: CertiActa v1.0.0 - Código Abierto (Licencia MIT)\n"
            "- Operación: 100% Local en Windows 10/11 (sin internet ni servidores externos)\n"
            "- Estándar Criptográfico: SHA-256 (256 bits) + PyMuPDF\n"
            "- Creado por: José Moreno - Secretario de Cámara del Consejo Legislativo\n"
            "  del Estado Bolivariano Delta Amacuro"
        )
        p.insert_textbox(
            fitz.Rect(self.margin_x + 16, 574, self.width - self.margin_x - 16, 708),
            ficha_texto,
            fontsize=10,
            fontname="helv",
            color=TEXT_DARK,
        )

    def add_chapter_title(self, num: str, title: str, audience: str) -> None:
        self.ensure_space(68)
        # Banda de capítulo
        rect = fitz.Rect(self.margin_x, self.y, self.width - self.margin_x, self.y + 48)
        sh = self.page.new_shape()
        sh.draw_rect(rect, radius=0.08)
        sh.finish(fill=NAVY, color=NAVY)
        sh.commit()

        self.page.insert_textbox(
            fitz.Rect(self.margin_x + 14, self.y + 7, self.width - self.margin_x - 14, self.y + 28),
            f"{num}. {title}",
            fontsize=13.5,
            fontname="hebo",
            color=WHITE,
        )
        self.page.insert_textbox(
            fitz.Rect(self.margin_x + 14, self.y + 27, self.width - self.margin_x - 14, self.y + 44),
            f"Dirigido a: {audience}",
            fontsize=9.5,
            fontname="helv",
            color=(0.74, 0.84, 0.94),
        )
        self.y += 60

    def add_subtitle(self, text: str) -> None:
        self.ensure_space(28)
        self.page.insert_text(
            fitz.Point(self.margin_x, self.y + 12),
            text,
            fontsize=11.5,
            fontname="hebo",
            color=ROYAL,
        )
        sh = self.page.new_shape()
        sh.draw_line(
            fitz.Point(self.margin_x, self.y + 16),
            fitz.Point(self.width - self.margin_x, self.y + 16),
        )
        sh.finish(color=BORDER, width=0.8)
        sh.commit()
        self.y += 24

    def add_paragraph(self, text: str, fontsize: float = 10.0, bold: bool = False, space_after: float = 8.0) -> None:
        font = "hebo" if bold else "helv"
        # Estimar líneas necesarias de forma conservadora
        chars_per_line = int(self.content_w / (fontsize * 0.48))
        lines = 0
        for raw_line in text.split("\n"):
            lines += max(1, (len(raw_line) // max(1, chars_per_line)) + 1)
        est_h = lines * (fontsize * 1.38) + 4
        self.ensure_space(est_h)

        rect = fitz.Rect(self.margin_x, self.y, self.width - self.margin_x, self.y + est_h + 12)
        rc = self.page.insert_textbox(
            rect,
            text,
            fontsize=fontsize,
            fontname=font,
            color=TEXT_DARK,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        # Calcular altura real consumida
        if rc >= 0:
            used_h = (est_h + 12) - rc
        else:
            used_h = est_h + 12
        self.y += max(used_h, fontsize * 1.4) + space_after

    def add_callout(self, title: str, body: str, kind: str = "blue") -> None:
        bg, border = {
            "blue": (BLUE_BG, ROYAL),
            "green": (EMERALD_BG, EMERALD),
            "amber": (AMBER_BG, AMBER_BORDER),
        }.get(kind, (BLUE_BG, ROYAL))

        chars_per_line = int((self.content_w - 28) / 4.8)
        lines = sum(max(1, (len(ln) // max(1, chars_per_line)) + 1) for ln in body.split("\n"))
        box_h = 28 + lines * 13.5 + 10
        self.ensure_space(box_h + 8)

        rect = fitz.Rect(self.margin_x, self.y, self.width - self.margin_x, self.y + box_h)
        sh = self.page.new_shape()
        sh.draw_rect(rect, radius=0.05)
        sh.finish(fill=bg, color=border, width=1.1)
        sh.commit()

        self.page.insert_text(
            fitz.Point(self.margin_x + 12, self.y + 18),
            title,
            fontsize=10,
            fontname="hebo",
            color=border,
        )
        self.page.insert_textbox(
            fitz.Rect(self.margin_x + 12, self.y + 24, self.width - self.margin_x - 12, self.y + box_h - 6),
            body,
            fontsize=9.5,
            fontname="helv",
            color=TEXT_DARK,
        )
        self.y += box_h + 10

    def add_diagram_comparative(self) -> None:
        """Diagrama vectorial comparando el método físico lento vs. el flujo ágil CertiActa."""
        box_h = 112
        self.ensure_space(box_h + 12)
        y0 = self.y

        # Fila 1: Proceso tradicional
        r_trad = fitz.Rect(self.margin_x, y0, self.width - self.margin_x, y0 + 48)
        s1 = self.page.new_shape()
        s1.draw_rect(r_trad, radius=0.08)
        s1.finish(fill=(0.98, 0.93, 0.93), color=(0.75, 0.25, 0.25), width=0.9)
        s1.commit()
        self.page.insert_text(fitz.Point(self.margin_x + 12, y0 + 16), "MÉTODO TRADICIONAL (LENTO):", fontsize=9, fontname="hebo", color=(0.70, 0.15, 0.15))
        self.page.insert_text(
            fitz.Point(self.margin_x + 12, y0 + 34),
            "Sesión  -->  Transcripción manual a libro físico (horas/días)  -->  Firmas  -->  Difícil verificación posterior",
            fontsize=9, fontname="helv", color=TEXT_DARK,
        )

        # Fila 2: Proceso CertiActa
        r_cert = fitz.Rect(self.margin_x, y0 + 58, self.width - self.margin_x, y0 + 108)
        s2 = self.page.new_shape()
        s2.draw_rect(r_cert, radius=0.08)
        s2.finish(fill=EMERALD_BG, color=EMERALD, width=1.1)
        s2.commit()
        self.page.insert_text(fitz.Point(self.margin_x + 12, y0 + 74), "FLUJO CON CERTIACTA (ÁGIL E INMUTABLE):", fontsize=9, fontname="hebo", color=EMERALD)
        self.page.insert_text(
            fitz.Point(self.margin_x + 12, y0 + 92),
            "Sesión y Aprobación  -->  Escaneo + Sello SHA-256 (segundos)  -->  Asiento breve en Libro Físico  -->  Auditoría Matemática",
            fontsize=8.8, fontname="helv", color=TEXT_DARK,
        )
        self.y += box_h + 8

    def add_diagram_footer_sample(self) -> None:
        """Diagrama que muestra cómo luce el pie de página estampado en el PDF."""
        box_h = 68
        self.ensure_space(box_h + 10)
        rect = fitz.Rect(self.margin_x, self.y, self.width - self.margin_x, self.y + box_h)
        sh = self.page.new_shape()
        sh.draw_rect(rect, radius=0.04)
        sh.finish(fill=WHITE, color=NAVY, width=1.2)
        sh.commit()

        # Simulación del pie de página real
        sh_line = self.page.new_shape()
        sh_line.draw_line(
            fitz.Point(self.margin_x + 10, self.y + 22),
            fitz.Point(self.width - self.margin_x - 10, self.y + 22),
        )
        sh_line.finish(color=BORDER, width=0.8)
        sh_line.commit()

        self.page.insert_text(
            fitz.Point(self.margin_x + 12, self.y + 14),
            "EJEMPLO VISUAL DEL PIE DE PÁGINA ESTAMPADO EN CADA HOJA DEL ACTA:",
            fontsize=8, fontname="hebo", color=ROYAL,
        )
        self.page.insert_text(
            fitz.Point(self.margin_x + 12, self.y + 38),
            "Sesión: Ordinaria | N.°: 012-2026 | Fecha: 24/11/2026 | Pág. 1 de 4",
            fontsize=8.5, fontname="helv", color=TEXT_DARK,
        )
        self.page.insert_text(
            fitz.Point(self.margin_x + 12, self.y + 54),
            "Esta acta es verificable mediante el siguiente código hash SHA-256 (escaneo original): 8ee6e98c1b800e9ff588238ec76f64...",
            fontsize=7.3, fontname="helv", color=TEXT_MUTED,
        )
        self.y += box_h + 10

    def add_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> None:
        row_h = 26
        total_h = row_h * (len(rows) + 1)
        self.ensure_space(total_h + 10)

        # Encabezado
        x = self.margin_x
        for h, w in zip(headers, col_widths):
            rect = fitz.Rect(x, self.y, x + w, self.y + row_h)
            sh = self.page.new_shape()
            sh.draw_rect(rect)
            sh.finish(fill=NAVY, color=WHITE, width=0.6)
            sh.commit()
            self.page.insert_textbox(
                fitz.Rect(x + 4, self.y + 6, x + w - 4, self.y + row_h - 3),
                h,
                fontsize=8.5,
                fontname="hebo",
                color=WHITE,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            x += w
        self.y += row_h

        # Filas
        for r_idx, row in enumerate(rows):
            bg = GRAY_BG if r_idx % 2 == 1 else WHITE
            x = self.margin_x
            for cell, w in zip(row, col_widths):
                rect = fitz.Rect(x, self.y, x + w, self.y + row_h)
                sh = self.page.new_shape()
                sh.draw_rect(rect)
                sh.finish(fill=bg, color=BORDER, width=0.6)
                sh.commit()
                self.page.insert_textbox(
                    fitz.Rect(x + 4, self.y + 5, x + w - 4, self.y + row_h - 3),
                    cell,
                    fontsize=8.0,
                    fontname="helv",
                    color=TEXT_DARK,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                x += w
            self.y += row_h
        self.y += 10

    def add_chrome_to_all_pages(self) -> None:
        total = len(self.doc)
        for idx in range(1, total):  # Omitir portada (índice 0)
            p = self.doc[idx]
            # Encabezado sutil
            p.insert_text(
                fitz.Point(self.margin_x, 36),
                "CertiActa - Manual de Usuario Institucional",
                fontsize=8.5,
                fontname="hebo",
                color=TEXT_MUTED,
            )
            p.insert_text(
                fitz.Point(self.width - self.margin_x - 95, 36),
                "Integridad SHA-256",
                fontsize=8.5,
                fontname="helv",
                color=ROYAL,
            )
            sh = p.new_shape()
            sh.draw_line(fitz.Point(self.margin_x, 44), fitz.Point(self.width - self.margin_x, 44))
            sh.draw_line(fitz.Point(self.margin_x, 750), fitz.Point(self.width - self.margin_x, 750))
            sh.finish(color=BORDER, width=0.7)
            sh.commit()

            # Pie de página
            p.insert_text(
                fitz.Point(self.margin_x, 765),
                "Creado por José Moreno - Secretario de Cámara CLEBDA | Software Libre (MIT)",
                fontsize=8,
                fontname="helv",
                color=TEXT_MUTED,
            )
            p.insert_text(
                fitz.Point(self.width - self.margin_x - 58, 765),
                f"Pág. {idx} de {total - 1}",
                fontsize=8,
                fontname="hebo",
                color=TEXT_MUTED,
            )

    def save(self, out_path: Path) -> None:
        self.add_chrome_to_all_pages()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.set_metadata({
            "title": "CertiActa — Manual de Usuario Institucional",
            "author": "José Moreno — Secretario de Cámara CLEBDA",
            "subject": "Guía operativa y de auditoría SHA-256 para actas legislativas",
            "creator": "CertiActa Manual Builder (PyMuPDF)",
        })
        self.doc.save(str(out_path), garbage=4, deflate=True)
        self.doc.close()


def build_manual() -> Path:
    b = ManualPDFBuilder()

    # 1. Portada
    b.draw_cover(ASSETS_DIR / "logo.png")

    # 2. Capítulo 1: Introducción y Justificación del Proyecto
    b.new_page()
    b.add_chapter_title(
        "CAPÍTULO 1",
        "Introducción y Justificación del Proyecto",
        "Todas las autoridades, personal de Secretaría y Contraloría",
    )
    b.add_subtitle("1.1 ¿Por qué nace CertiActa?")
    b.add_paragraph(
        "Tradicionalmente, el resguardo oficial de las actas de sesiones en los Consejos Legislativos "
        "y Concejos Municipales ha dependido de la transcripción física manual en libros empastados. "
        "Este procedimiento demanda decenas de horas de trabajo operativo por cada sesión, genera cuellos "
        "de botella administrativos y retrasa la disponibilidad formal del acta entre su aprobación y su archivo."
    )
    b.add_paragraph(
        "CertiActa nace para modernizar ese proceso dejando atrás la transcripción física extensa de los "
        "libros de actas. A partir del escaneo íntegro del acta ya aprobada, firmada y sellada, el sistema "
        "genera una huella criptográfica matemática (SHA-256) y la estampa al pie de todas sus páginas, "
        "logrando una fluidez inmediata entre la sesión, la aprobación del acta y su verificación futura. "
        "En términos administrativos, esto libera decenas de horas de trabajo secretarial por período, acelera "
        "la entrega de copias certificadas a legisladores y comisiones, y garantiza trazabilidad inmediata para Contraloría."
    )
    b.add_diagram_comparative()

    b.add_subtitle("1.2 Modelo Híbrido con Libro Físico de Respaldo")
    b.add_paragraph(
        "Para combinar la agilidad digital con la seguridad jurídica institucional, el sistema contempla el uso "
        "de un Libro Físico de Respaldo (Libro de Control de Actas). En lugar de transcribir páginas completas "
        "a mano, la Secretaría solo asienta en ese libro foliado los datos clave de cada sesión: fecha, tipo, "
        "número de sesión y los códigos hash SHA-256 generados. De este modo, el libro físico actúa como un "
        "testigo material incorruptible ante cualquier auditoría externa."
    )

    # 3. Capítulo 2: Para Diputados, Concejales y Legisladores
    b.add_chapter_title(
        "CAPÍTULO 2",
        "Guía Conceptual para Legisladores",
        "Diputados, Concejales, Presidentes de Cámara y Legisladores",
    )
    b.add_subtitle("2.1 ¿Qué es un código Hash SHA-256 en palabras sencillas?")
    b.add_paragraph(
        "Un código SHA-256 funciona exactamente igual que un 'ADN digital único' o un sello lacrado matemático "
        "de 64 caracteres. Cuando CertiActa analiza un PDF escaneado con las firmas y sellos originales, "
        "calcula una firma matemática irrepetible que identifica a ese documento exacto."
    )
    b.add_callout(
        "GARANTÍA DE INALTERABILIDAD ABSOLUTA",
        "Si alguien modificara una sola letra, una cifra presupuestaria, una fecha o incluso un píxel de una firma "
        "en el documento, el código SHA-256 cambiaría por completo de forma inmediata e irreversible. Es "
        "matemáticamente imposible falsificar un documento manteniendo el mismo código hash.",
        kind="green",
    )
    b.add_subtitle("2.2 ¿Cómo leer un acta certificada?")
    b.add_paragraph(
        "Toda acta procesada por CertiActa conserva intacto su contenido original y muestra al pie de cada una "
        "de sus páginas una franja blanca legible con los datos de la sesión, la paginación y el código hash "
        "del escaneo original:"
    )
    b.add_diagram_footer_sample()

    # 4. Capítulo 3: Para Secretarios de Cámara y Operadores
    b.new_page()
    b.add_chapter_title(
        "CAPÍTULO 3",
        "Manual Operativo y Libro Físico de Respaldo",
        "Secretarios de Cámara, Asistentes y Operadores del Sistema",
    )
    b.add_subtitle("3.1 Estructura automática de carpetas (100% offline)")
    b.add_paragraph(
        "CertiActa funciona sin internet en Windows 10 y 11. Al iniciar (python main.py o CertiActa.exe), "
        "crea automáticamente las siguientes carpetas de trabajo en su directorio:"
    )
    b.add_table(
        ["Carpeta / Archivo", "Función Institucional"],
        [
            ["01_Escaneos_Originales/", "Resguardo intacto del PDF original firmado y sellado (nunca se altera)."],
            ["02_Actas_Con_Hash/", "Copia oficial generada con sufijo _CON_HASH.pdf y leyenda al pie."],
            ["datos/registro_actas.json", "Base de datos local con escritura atómica segura ante cortes de luz."],
            ["datos/exportaciones/", "Reportes exportados en formato CSV listos para abrir en Microsoft Excel."],
        ],
        [175, 333],
    )

    b.add_subtitle("3.2 Paso a paso en la pestaña 'Estampar y Registrar'")
    b.add_paragraph(
        "1. Haga clic en 'Seleccionar PDF...' y elija el archivo PDF del acta escaneada ya firmada y sellada.\n"
        "2. El sistema calculará automáticamente la huella SHA-256 del original.\n"
        "3. Complete: Tipo de Sesión (Ordinaria, Extraordinaria, Especial, Solemne), N.° de Sesión, Fecha y Observación.\n"
        "4. Presione 'Generar PDF con Hash al pie y guardar registro'. El sistema creará el nuevo PDF en "
        "02_Actas_Con_Hash/ y mostrará en pantalla ambos códigos hash (Original y PDF Generado)."
    )

    b.add_subtitle("3.3 Asiento en el Libro Físico de Respaldo")
    b.add_paragraph(
        "Tras generar el acta, utilice el botón 'Copiar Ficha para Libro Físico' (disponible tanto al finalizar "
        "el estampado como en la pestaña 'Registro Local') para obtener un resumen limpio y exacto de los datos "
        "a asentar en el Libro Físico foliado de Secretaría:"
    )
    b.add_table(
        ["Fecha Sesión", "Tipo / N.° Sesión", "Págs.", "SHA-256 Original (Pie)", "SHA-256 PDF Generado"],
        [
            ["24/11/2026", "Ordinaria 012-2026", "4", "8ee6e98c...35d23a51d", "4f92a11b...99c10e4a"],
            ["28/11/2026", "Especial 003-2026", "2", "a1c40f92...77b8210c", "d308e441...12fa09b3"],
        ],
        [72, 108, 40, 144, 144],
    )
    b.add_callout(
        "BUENA PRÁCTICA DE RESPALDO PREVENTIVO",
        "Realice copias periódicas de las carpetas 'datos/' y '01_Escaneos_Originales/' hacia un disco externo o "
        "pendrive institucional bajo custodia de Secretaría.",
        kind="amber",
    )

    # 5. Capítulo 4: Para Auditores de Contraloría
    b.new_page()
    b.add_chapter_title(
        "CAPÍTULO 4",
        "Protocolo de Auditoría y Control Posterior",
        "Auditores Internos, Contraloría General y Comisiones de Revisión",
    )
    b.add_subtitle("4.1 Esquema de Doble Huella SHA-256")
    b.add_paragraph(
        "Por principio matemático, un archivo PDF no puede contener su propio hash SHA-256 final impreso en su "
        "interior (porque al escribir el texto cambian los bytes del archivo). Por ello, CertiActa registra dos "
        "huellas complementarias para cada acta:\n"
        "- SHA-256 Original: Huella del escaneo intacto antes de estampar (impresa al pie de cada página).\n"
        "- SHA-256 PDF Generado: Huella exacta del archivo distribuido (_CON_HASH.pdf)."
    )

    b.add_subtitle("4.2 Verificación dentro de CertiActa ('Auditar / Verificar')")
    b.add_paragraph(
        "1. En 'Registro Local', seleccione el acta a auditar y pulse 'Cargar en Verificador' (o pegue manualmente "
        "el hash obtenido del Libro Físico de Respaldo).\n"
        "2. Seleccione el archivo PDF recibido en la computadora del auditor y pulse 'Verificar Coincidencia'.\n"
        "3. Lectura del resultado:\n"
        "   - VERDE (COINCIDE / VERIFICADO): El archivo es matemáticamente idéntico byte a byte y no ha sufrido "
        "ninguna alteración desde su emisión.\n"
        "   - ROJO (NO COINCIDE): El documento fue modificado, dañado o no corresponde al acta registrada."
    )

    b.add_subtitle("4.3 Verificación Autónoma sin usar CertiActa (Herramientas de Windows)")
    b.add_paragraph(
        "Cualquier auditor externo puede comprobar la autenticidad de un archivo de forma independiente usando "
        "las herramientas integradas en Windows, sin depender de este programa:"
    )
    b.add_callout(
        "COMANDOS NATIVOS DE AUDITORÍA EN WINDOWS",
        "- En PowerShell:\n"
        "  Get-FileHash \"ruta\\al\\Acta_CON_HASH.pdf\" -Algorithm SHA256\n\n"
        "- En Símbolo del Sistema (CMD):\n"
        "  certutil -hashfile \"ruta\\al\\Acta_CON_HASH.pdf\" SHA256\n\n"
        "Compare el código resultante con el SHA-256 registrado en el Libro Físico o en el reporte CSV.",
        kind="blue",
    )

    # 6. Capítulo 5: Preguntas Frecuentes
    b.add_chapter_title(
        "CAPÍTULO 5",
        "Preguntas Frecuentes y Adopción Institucional",
        "Operadores y Administradores de Tecnología",
    )
    b.add_paragraph(
        "- ¿El programa requiere conexión a internet?\n"
        "  No. Toda operación criptográfica y de almacenamiento ocurre exclusivamente en el equipo local.\n\n"
        "- ¿Qué hago si aparece un error al guardar un PDF ya existente?\n"
        "  Verifique que el archivo _CON_HASH.pdf no esté abierto en Adobe Reader, Edge u otro visor PDF.\n\n"
        "- ¿Cómo realizo un respaldo preventivo rápido?\n"
        "  En 'Registro Local', presione 'Respaldo ZIP' para empaquetar en un clic el registro JSON y todos los PDFs.\n\n"
        "- ¿Pueden otros Consejos Legislativos o Concejos Municipales utilizar CertiActa?\n"
        "  Sí. El proyecto se distribuye bajo Licencia MIT de código abierto, conservando el reconocimiento a su "
        "autor original: José Moreno, Secretario de Cámara del Consejo Legislativo del Estado Bolivariano Delta Amacuro.",
        space_after=4,
    )

    out_pdf = DOCS_DIR / "Manual_de_Usuario.pdf"
    b.save(out_pdf)
    print(f"Manual generado exitosamente en: {out_pdf} ({len(fitz.open(str(out_pdf)))} páginas)")
    return out_pdf


if __name__ == "__main__":
    build_manual()
