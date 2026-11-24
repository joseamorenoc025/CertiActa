"""
Pestaña 1: Estampar y Registrar.
Permite seleccionar un PDF escaneado original, calcular su SHA-256, ingresar metadatos,
generar el nuevo PDF con el sello al pie y persistir el registro.
"""

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from src.config import TIPOS_SESION
from src.core.hasher import calcular_sha256
from src.core.models import ActaRecord
from src.core.pdf_stamper import PDFStampError, estampar_acta_pdf
from src.repository.registry_repo import RegistryRepository


class TabStamper(ctk.CTkScrollableFrame):
    def __init__(self, master, repository: RegistryRepository, on_record_saved: Optional[Callable] = None):
        super().__init__(master)
        self.repo = repository
        self.on_record_saved = on_record_saved

        self.archivo_seleccionado: Optional[Path] = None
        self.hash_actual: str = ""
        self.hash_generado: str = ""
        self.ultimo_pdf_generado: Optional[Path] = None
        self.ultimo_registro: Optional[ActaRecord] = None

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Tarjeta Selección de Archivo
        card_file = ctk.CTkFrame(self, corner_radius=10)
        card_file.pack(fill="x", padx=15, pady=(10, 10))

        lbl_section1 = ctk.CTkLabel(
            card_file,
            text="1. Selección de PDF Escaneado Original",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        lbl_section1.pack(anchor="w", padx=15, pady=(12, 6))

        desc_rule = ctk.CTkLabel(
            card_file,
            text="Regla de integridad: El archivo escaneado original nunca será modificado ni sobrescrito.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#8c9ba5",
        )
        desc_rule.pack(anchor="w", padx=15, pady=(0, 10))

        row_file = ctk.CTkFrame(card_file, fg_color="transparent")
        row_file.pack(fill="x", padx=15, pady=(0, 12))

        self.btn_select_file = ctk.CTkButton(
            row_file,
            text="📁 Seleccionar PDF...",
            command=self._on_select_file,
            width=160,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_select_file.pack(side="left", padx=(0, 10))

        self.entry_file_path = ctk.CTkEntry(
            row_file,
            placeholder_text="Ningún archivo seleccionado...",
            font=ctk.CTkFont(size=12),
        )
        self.entry_file_path.pack(side="left", fill="x", expand=True)
        self.entry_file_path.configure(state="readonly")

        # Fila del Hash Calculado
        row_hash = ctk.CTkFrame(card_file, fg_color="transparent")
        row_hash.pack(fill="x", padx=15, pady=(0, 12))

        lbl_hash = ctk.CTkLabel(
            row_hash,
            text="Huella SHA-256:",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            anchor="w",
        )
        lbl_hash.pack(side="left")

        self.entry_hash = ctk.CTkEntry(
            row_hash,
            font=ctk.CTkFont(family="Consolas", size=12),
            placeholder_text="Seleccione un archivo PDF para calcular automáticamente su hash...",
        )
        self.entry_hash.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_hash.configure(state="readonly")

        self.btn_copy_hash = ctk.CTkButton(
            row_hash,
            text="📋 Copiar Hash",
            command=self._on_copy_hash,
            width=110,
            state="disabled",
        )
        self.btn_copy_hash.pack(side="left")

        # 2. Tarjeta Datos de la Sesión
        card_meta = ctk.CTkFrame(self, corner_radius=10)
        card_meta.pack(fill="x", padx=15, pady=(0, 10))

        lbl_section2 = ctk.CTkLabel(
            card_meta,
            text="2. Datos Oficiales de la Sesión",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        lbl_section2.pack(anchor="w", padx=15, pady=(12, 10))

        # Cuadrícula de campos
        grid_fields = ctk.CTkFrame(card_meta, fg_color="transparent")
        grid_fields.pack(fill="x", padx=15, pady=(0, 12))
        grid_fields.grid_columnconfigure((0, 1, 2), weight=1)

        # Campo: Tipo de Sesión
        ctk.CTkLabel(grid_fields, text="Tipo de Sesión *", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=5, pady=(0, 4)
        )
        self.combo_tipo = ctk.CTkComboBox(
            grid_fields,
            values=TIPOS_SESION,
            state="readonly",
        )
        self.combo_tipo.set(TIPOS_SESION[0])
        self.combo_tipo.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))

        # Campo: N.° de Sesión
        ctk.CTkLabel(grid_fields, text="N.° de Sesión *", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=5, pady=(0, 4)
        )
        self.entry_num_sesion = ctk.CTkEntry(
            grid_fields,
            placeholder_text="Ej: 004-2026",
        )
        self.entry_num_sesion.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))

        # Campo: Fecha de Sesión
        ctk.CTkLabel(grid_fields, text="Fecha de Sesión (DD/MM/AAAA) *", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=2, sticky="w", padx=5, pady=(0, 4)
        )
        hoy = datetime.now().strftime("%d/%m/%Y")
        self.entry_fecha = ctk.CTkEntry(
            grid_fields,
            placeholder_text=hoy,
        )
        self.entry_fecha.insert(0, hoy)
        self.entry_fecha.grid(row=1, column=2, sticky="ew", padx=5, pady=(0, 10))

        # Campo: Observación
        ctk.CTkLabel(grid_fields, text="Observación (Opcional)", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 4)
        )
        self.entry_obs = ctk.CTkEntry(
            grid_fields,
            placeholder_text="Anotaciones relevantes sobre el acta, firmas o contenido...",
        )
        self.entry_obs.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 10))

        # Checkbox Resguardo
        self.chk_backup_var = ctk.BooleanVar(value=True)
        self.chk_backup = ctk.CTkCheckBox(
            card_meta,
            text="Guardar copia intacta de resguardo en carpeta '01_Escaneos_Originales/'",
            variable=self.chk_backup_var,
            font=ctk.CTkFont(size=12),
        )
        self.chk_backup.pack(anchor="w", padx=20, pady=(0, 14))

        # 3. Tarjeta de Ejecución y Estado
        card_action = ctk.CTkFrame(self, corner_radius=10)
        card_action.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_procesar = ctk.CTkButton(
            card_action,
            text="⚡ Generar PDF con Hash al pie y guardar registro",
            command=self._on_procesar,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
        )
        self.btn_procesar.pack(fill="x", padx=15, pady=(15, 8))

        self.lbl_status = ctk.CTkLabel(
            card_action,
            text="Listo para procesar.",
            font=ctk.CTkFont(size=12),
            text_color="#8c9ba5",
        )
        self.lbl_status.pack(padx=15, pady=(0, 8))

        # Barra de progreso
        self.progressbar = ctk.CTkProgressBar(card_action)
        self.progressbar.pack(fill="x", padx=15, pady=(0, 12))
        self.progressbar.set(0)

        # Fila de botones posteriores al éxito
        self.frame_post_actions = ctk.CTkFrame(card_action, fg_color="transparent")
        self.btn_open_pdf = ctk.CTkButton(
            self.frame_post_actions,
            text="👁 Ver PDF Generado",
            command=self._on_open_generated_pdf,
            fg_color="#2b7842",
            hover_color="#1e542e",
        )
        self.btn_open_folder = ctk.CTkButton(
            self.frame_post_actions,
            text="📂 Abrir Carpeta de Destino",
            command=self._on_open_destination_folder,
            fg_color="#445566",
            hover_color="#2f3b47",
        )
        self.btn_copy_ficha = ctk.CTkButton(
            self.frame_post_actions,
            text="📖 Copiar Ficha para Libro Físico",
            command=self._on_copy_ficha_libro,
            fg_color="#6b4c9a",
            hover_color="#523878",
        )
        self.btn_open_pdf.pack(side="left", padx=(0, 10))
        self.btn_open_folder.pack(side="left", padx=(0, 10))
        self.btn_copy_ficha.pack(side="left")

        # 4. Tarjeta de Resultado de Hashes (oculta hasta completar el proceso)
        self.card_hashes_result = ctk.CTkFrame(self, corner_radius=10)

        lbl_hashes_title = ctk.CTkLabel(
            self.card_hashes_result,
            text="Resultado: Doble Huella SHA-256",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        lbl_hashes_title.pack(anchor="w", padx=15, pady=(12, 6))

        lbl_hashes_desc = ctk.CTkLabel(
            self.card_hashes_result,
            text="Ambos hashes quedan registrados. Use el hash del PDF Generado para verificar el archivo distribuido.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#8c9ba5",
        )
        lbl_hashes_desc.pack(anchor="w", padx=15, pady=(0, 10))

        # Hash del original
        row_h_orig = ctk.CTkFrame(self.card_hashes_result, fg_color="transparent")
        row_h_orig.pack(fill="x", padx=15, pady=(0, 6))

        ctk.CTkLabel(
            row_h_orig, text="SHA-256 Escaneo Original (impreso al pie):",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")

        self.entry_result_hash_orig = ctk.CTkEntry(
            row_h_orig,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="—",
        )
        self.entry_result_hash_orig.pack(fill="x", pady=(2, 0))
        self.entry_result_hash_orig.configure(state="readonly")

        # Hash del generado
        row_h_gen = ctk.CTkFrame(self.card_hashes_result, fg_color="transparent")
        row_h_gen.pack(fill="x", padx=15, pady=(6, 6))

        ctk.CTkLabel(
            row_h_gen, text="SHA-256 PDF Generado (_CON_HASH.pdf) — para verificación:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2ea043",
        ).pack(anchor="w")

        row_h_gen_entry = ctk.CTkFrame(row_h_gen, fg_color="transparent")
        row_h_gen_entry.pack(fill="x", pady=(2, 0))

        self.entry_result_hash_gen = ctk.CTkEntry(
            row_h_gen_entry,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="—",
        )
        self.entry_result_hash_gen.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_result_hash_gen.configure(state="readonly")

        self.btn_copy_hash_gen = ctk.CTkButton(
            row_h_gen_entry,
            text="📋 Copiar Hash Generado",
            command=self._on_copy_hash_generado,
            width=170,
            fg_color="#2b7842",
            hover_color="#1e542e",
        )
        self.btn_copy_hash_gen.pack(side="left")

        lbl_hashes_note = ctk.CTkLabel(
            self.card_hashes_result,
            text="Nota: El hash del PDF Generado es el que debe usarse para verificar la integridad del archivo _CON_HASH.pdf distribuido.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#6e7681",
            wraplength=900,
            justify="left",
        )
        lbl_hashes_note.pack(anchor="w", padx=15, pady=(4, 12))

    def _on_select_file(self) -> None:
        """Abre el diálogo para seleccionar un PDF y calcula su hash en segundo plano."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar acta escaneada original",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return

        path = Path(ruta)
        self.archivo_seleccionado = path

        self.entry_file_path.configure(state="normal")
        self.entry_file_path.delete(0, "end")
        self.entry_file_path.insert(0, str(path))
        self.entry_file_path.configure(state="readonly")

        self.lbl_status.configure(text=f"Calculando huella SHA-256 de '{path.name}'...", text_color="#3b8ed0")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()

        # Cálculo asíncrono para no bloquear la interfaz
        threading.Thread(target=self._async_calc_hash, args=(path,), daemon=True).start()

    def _async_calc_hash(self, path: Path) -> None:
        try:
            h = calcular_sha256(path)
            self.hash_actual = h

            def update_ui():
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                self.progressbar.set(1.0)

                self.entry_hash.configure(state="normal")
                self.entry_hash.delete(0, "end")
                self.entry_hash.insert(0, h)
                self.entry_hash.configure(state="readonly")
                self.btn_copy_hash.configure(state="normal")

                self.lbl_status.configure(
                    text=f"Hash calculado exitosamente ({len(h)} caracteres). Listo para estampar.",
                    text_color="#2ea043",
                )

            self.after(0, update_ui)
        except Exception as e:
            err_msg = str(e)

            def err_ui(msg: str = err_msg):
                self.progressbar.stop()
                self.progressbar.set(0)
                self.lbl_status.configure(text=f"Error al calcular hash: {msg}", text_color="#cf222e")
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{msg}")

            self.after(0, err_ui)

    def _on_copy_hash(self) -> None:
        """Copia el hash del original al portapapeles del sistema."""
        if self.hash_actual:
            self.clipboard_clear()
            self.clipboard_append(self.hash_actual)
            self.update()
            self.lbl_status.configure(text="¡Hash del original copiado al portapapeles!", text_color="#2ea043")

    def _on_copy_hash_generado(self) -> None:
        """Copia el hash del PDF generado al portapapeles del sistema."""
        if self.hash_generado:
            self.clipboard_clear()
            self.clipboard_append(self.hash_generado)
            self.update()
            self.lbl_status.configure(text="¡Hash del PDF Generado copiado al portapapeles!", text_color="#2ea043")

    def _on_copy_ficha_libro(self) -> None:
        """Copia la ficha actualizada (sesión, fecha y hashes) para asentar en el Libro Físico."""
        if self.ultimo_registro:
            ficha = self.ultimo_registro.format_ficha_libro_fisico()
            self.clipboard_clear()
            self.clipboard_append(ficha)
            self.update()
            self.lbl_status.configure(
                text=f"¡Ficha de sesión {self.ultimo_registro.num_sesion} copiada para Libro Físico!",
                text_color="#2ea043",
            )

    def _on_procesar(self) -> None:
        """Valida campos e inicia el proceso de estampado y registro en un hilo de trabajo."""
        if not self.archivo_seleccionado or not self.archivo_seleccionado.exists():
            messagebox.showwarning("Atención", "Debe seleccionar un archivo PDF escaneado original.")
            return

        tipo_sesion = self.combo_tipo.get().strip()
        num_sesion = self.entry_num_sesion.get().strip()
        fecha_sesion = self.entry_fecha.get().strip()
        obs = self.entry_obs.get().strip()

        if not num_sesion:
            messagebox.showwarning("Campo obligatorio", "Por favor indique el N.° de sesión (ej: 001-2026).")
            self.entry_num_sesion.focus()
            return

        if not fecha_sesion:
            messagebox.showwarning("Campo obligatorio", "Por favor indique la fecha de la sesión.")
            self.entry_fecha.focus()
            return

        # Deshabilitar botón durante procesamiento
        self.btn_procesar.configure(state="disabled")
        self.btn_select_file.configure(state="disabled")
        self.frame_post_actions.pack_forget()
        self.card_hashes_result.pack_forget()
        self.lbl_status.configure(text="Estampando leyenda de verificación y procesando páginas...", text_color="#3b8ed0")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()

        threading.Thread(
            target=self._async_stamp,
            args=(self.archivo_seleccionado, tipo_sesion, num_sesion, fecha_sesion, obs, self.chk_backup_var.get()),
            daemon=True,
        ).start()

    def _async_stamp(
        self,
        orig_path: Path,
        tipo_sesion: str,
        num_sesion: str,
        fecha_sesion: str,
        observacion: str,
        backup: bool,
    ) -> None:
        try:
            ruta_con_hash, sha_original, sha_generado, total_pags, ruta_resguardo = estampar_acta_pdf(
                ruta_original=orig_path,
                tipo_sesion=tipo_sesion,
                num_sesion=num_sesion,
                fecha_sesion=fecha_sesion,
                guardar_copia_en_originales=backup,
                hash_precalculado=self.hash_actual or None,
            )

            self.hash_generado = sha_generado

            # Crear y guardar registro
            record = ActaRecord.create(
                tipo_sesion=tipo_sesion,
                num_sesion=num_sesion,
                fecha_sesion=fecha_sesion,
                observacion=observacion,
                nombre_archivo_original=orig_path.name,
                ruta_archivo_original=str(ruta_resguardo),
                nombre_archivo_con_hash=ruta_con_hash.name,
                ruta_archivo_con_hash=str(ruta_con_hash),
                sha256_original=sha_original,
                total_paginas=total_pags,
                sha256_con_hash=sha_generado,
            )
            self.repo.add(record)
            self.ultimo_pdf_generado = ruta_con_hash
            self.ultimo_registro = record

            def success_ui():
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                self.progressbar.set(1.0)
                self.btn_procesar.configure(state="normal")
                self.btn_select_file.configure(state="normal")
                self.lbl_status.configure(
                    text=f"¡Completado! {total_pags} páginas selladas en '{ruta_con_hash.name}'",
                    text_color="#2ea043",
                )
                self.frame_post_actions.pack(padx=15, pady=(0, 12))

                # Mostrar tarjeta de doble hash
                self.card_hashes_result.pack(fill="x", padx=15, pady=(0, 15))

                self.entry_result_hash_orig.configure(state="normal")
                self.entry_result_hash_orig.delete(0, "end")
                self.entry_result_hash_orig.insert(0, sha_original)
                self.entry_result_hash_orig.configure(state="readonly")

                self.entry_result_hash_gen.configure(state="normal")
                self.entry_result_hash_gen.delete(0, "end")
                self.entry_result_hash_gen.insert(0, sha_generado)
                self.entry_result_hash_gen.configure(state="readonly")

                if self.on_record_saved:
                    self.on_record_saved()

                messagebox.showinfo(
                    "Operación Exitosa",
                    f"El acta se procesó correctamente:\n\n"
                    f"• Páginas selladas: {total_pags}\n"
                    f"• Archivo generado: {ruta_con_hash.name}\n"
                    f"• Ubicación: 02_Actas_Con_Hash/\n\n"
                    f"Se registraron ambos hashes SHA-256:\n"
                    f"• Original (impreso al pie): {sha_original[:16]}...\n"
                    f"• PDF Generado (para verificar): {sha_generado[:16]}...\n\n"
                    f"El escaneo original permanece 100% intacto.",
                )

            self.after(0, success_ui)

        except PDFStampError as pe:
            err_msg = str(pe)

            def err_stamp(msg: str = err_msg):
                self.progressbar.stop()
                self.progressbar.set(0)
                self.btn_procesar.configure(state="normal")
                self.btn_select_file.configure(state="normal")
                self.lbl_status.configure(text=f"Error: {msg}", text_color="#cf222e")
                messagebox.showerror("Error al Estampar PDF", msg)

            self.after(0, err_stamp)
        except Exception as e:
            err_msg = str(e)

            def err_general(msg: str = err_msg):
                self.progressbar.stop()
                self.progressbar.set(0)
                self.btn_procesar.configure(state="normal")
                self.btn_select_file.configure(state="normal")
                self.lbl_status.configure(text=f"Error inesperado: {msg}", text_color="#cf222e")
                messagebox.showerror("Error Inesperado", f"Ocurrió una falla:\n{msg}")

            self.after(0, err_general)

    def _on_open_generated_pdf(self) -> None:
        """Abre el archivo PDF generado en el visor predeterminado del sistema operativo."""
        if self.ultimo_pdf_generado and self.ultimo_pdf_generado.exists():
            if sys.platform == "win32":
                os.startfile(str(self.ultimo_pdf_generado))
            else:
                subprocess.run(["xdg-open", str(self.ultimo_pdf_generado)])

    def _on_open_destination_folder(self) -> None:
        """Abre la carpeta 02_Actas_Con_Hash en el explorador de Windows."""
        if self.ultimo_pdf_generado and self.ultimo_pdf_generado.parent.exists():
            if sys.platform == "win32":
                subprocess.run(["explorer", str(self.ultimo_pdf_generado.parent)])
            else:
                subprocess.run(["xdg-open", str(self.ultimo_pdf_generado.parent)])
