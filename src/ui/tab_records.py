"""
Pestaña 3: Registro Local.
Permite visualizar, buscar en tiempo real, filtrar, copiar hashes,
enviar al verificador y exportar a CSV los registros guardados.
"""

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional
import zipfile

import customtkinter as ctk

import src.config as cfg
from src.config import TIPOS_SESION
from src.core.models import ActaRecord
from src.repository.registry_repo import RegistryRepository


class TabRecords(ctk.CTkFrame):
    def __init__(
        self,
        master,
        repository: RegistryRepository,
        on_load_in_verifier: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(master)
        self.repo = repository
        self.on_load_in_verifier = on_load_in_verifier

        self.registros_actuales: list[ActaRecord] = []
        self.registro_seleccionado: Optional[ActaRecord] = None

        self._build_ui()
        self.refresh_records()

    def _build_ui(self) -> None:
        # 1. Barra Superior de Búsqueda y Estadísticas
        bar_top = ctk.CTkFrame(self, corner_radius=10)
        bar_top.pack(fill="x", padx=15, pady=(10, 8))

        lbl_search = ctk.CTkLabel(
            bar_top,
            text="🔎 Buscar en tiempo real:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_search.pack(side="left", padx=(15, 10), pady=10)

        self.entry_search = ctk.CTkEntry(
            bar_top,
            placeholder_text="Escriba tipo, número, fecha, nombre de archivo o hash...",
            font=ctk.CTkFont(size=12),
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=10)
        self.entry_search.bind("<KeyRelease>", self._on_search_key)

        self.combo_filter_tipo = ctk.CTkComboBox(
            bar_top,
            values=["Todos"] + TIPOS_SESION,
            state="readonly",
            width=140,
            command=self._on_filter_change,
        )
        self.combo_filter_tipo.set("Todos")
        self.combo_filter_tipo.pack(side="left", padx=(0, 8), pady=10)

        self.btn_clear_search = ctk.CTkButton(
            bar_top,
            text="Limpiar",
            width=70,
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_clear_search,
        )
        self.btn_clear_search.pack(side="left", padx=(0, 10), pady=10)

        self.lbl_count = ctk.CTkLabel(
            bar_top,
            text="0 registros",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8c9ba5",
        )
        self.lbl_count.pack(side="right", padx=(0, 15), pady=10)

        # 2. Contenedor de la Tabla (Treeview con scrollbars)
        frame_table = ctk.CTkFrame(self, corner_radius=10)
        frame_table.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        # Estilo para ttk.Treeview (sincronizado con el tema)
        self._tree_style = ttk.Style()
        self._tree_style.theme_use("clam")
        self.apply_treeview_theme("dark")

        columns = ("num", "tipo", "fecha", "archivo", "pags", "fecha_reg", "sha256")
        self.tree = ttk.Treeview(
            frame_table,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Actas.Treeview",
        )

        # Configurar encabezados y anchos
        self.tree.heading("num", text="N.° Sesión")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("fecha", text="Fecha Sesión")
        self.tree.heading("archivo", text="Archivo Original")
        self.tree.heading("pags", text="Págs")
        self.tree.heading("fecha_reg", text="Fecha Registro")
        self.tree.heading("sha256", text="SHA-256 (Original)")

        self.tree.column("num", width=95, anchor="center")
        self.tree.column("tipo", width=110, anchor="w")
        self.tree.column("fecha", width=95, anchor="center")
        self.tree.column("archivo", width=180, anchor="w")
        self.tree.column("pags", width=55, anchor="center")
        self.tree.column("fecha_reg", width=135, anchor="center")
        self.tree.column("sha256", width=220, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame_table.grid_rowconfigure(0, weight=1)
        frame_table.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # 3. Panel de Detalle del Registro Seleccionado
        self.frame_detail = ctk.CTkFrame(self, corner_radius=10)
        self.frame_detail.pack(fill="x", padx=15, pady=(0, 8))

        # Hash del PDF Generado (el principal para verificación)
        row_det_gen = ctk.CTkFrame(self.frame_detail, fg_color="transparent")
        row_det_gen.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            row_det_gen,
            text="SHA-256 PDF Generado (_CON_HASH.pdf):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2ea043",
        ).pack(side="left")
        self.lbl_full_hash_gen = ctk.CTkEntry(
            row_det_gen,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="Seleccione un registro...",
        )
        self.lbl_full_hash_gen.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.lbl_full_hash_gen.configure(state="readonly")

        # Hash del original
        row_det1 = ctk.CTkFrame(self.frame_detail, fg_color="transparent")
        row_det1.pack(fill="x", padx=12, pady=(4, 4))

        ctk.CTkLabel(row_det1, text="SHA-256 Escaneo Original:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        self.lbl_full_hash = ctk.CTkEntry(
            row_det1,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="Seleccione un registro para ver el hash completo...",
        )
        self.lbl_full_hash.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.lbl_full_hash.configure(state="readonly")

        row_det2 = ctk.CTkFrame(self.frame_detail, fg_color="transparent")
        row_det2.pack(fill="x", padx=12, pady=(0, 8))
        self.lbl_detail_extra = ctk.CTkLabel(
            row_det2,
            text="Observación: Ningún registro seleccionado.",
            font=ctk.CTkFont(size=11),
            text_color="#8c9ba5",
            anchor="w",
        )
        self.lbl_detail_extra.pack(fill="x")

        # 4. Barra Inferior de Botones de Acción
        bar_actions = ctk.CTkFrame(self, fg_color="transparent")
        bar_actions.pack(fill="x", padx=15, pady=(0, 10))

        self.btn_copy_hash = ctk.CTkButton(
            bar_actions,
            text="📋 Copiar Hash",
            command=self._on_copy_hash,
            width=120,
            state="disabled",
        )
        self.btn_copy_hash.pack(side="left", padx=(0, 8))

        self.btn_load_verifier = ctk.CTkButton(
            bar_actions,
            text="🔍 Cargar en Verificador",
            command=self._on_load_in_verifier,
            width=150,
            state="disabled",
            fg_color="#1f6aa5",
            hover_color="#144d75",
        )
        self.btn_load_verifier.pack(side="left", padx=(0, 8))

        self.btn_open_pdf = ctk.CTkButton(
            bar_actions,
            text="👁 Abrir PDF con Hash",
            command=self._on_open_pdf,
            width=150,
            state="disabled",
            fg_color="#2b7842",
            hover_color="#1e542e",
        )
        self.btn_open_pdf.pack(side="left", padx=(0, 8))

        self.btn_copy_ficha = ctk.CTkButton(
            bar_actions,
            text="📖 Ficha Libro Físico",
            command=self._on_copy_ficha,
            width=145,
            state="disabled",
            fg_color="#6b4c9a",
            hover_color="#523878",
        )
        self.btn_copy_ficha.pack(side="left", padx=(0, 8))

        self.btn_export_csv = ctk.CTkButton(
            bar_actions,
            text="📊 Exportar a CSV",
            command=self._on_export_csv,
            width=125,
            fg_color="#334455",
            hover_color="#223344",
        )
        self.btn_export_csv.pack(side="left", padx=(0, 8))

        self.btn_backup_zip = ctk.CTkButton(
            bar_actions,
            text="💾 Respaldo ZIP",
            command=self._on_backup_zip,
            width=125,
            fg_color="#4a5568",
            hover_color="#2d3748",
        )
        self.btn_backup_zip.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            bar_actions,
            text="🔄 Refrescar",
            command=self.refresh_records,
            width=90,
            fg_color="#555555",
            hover_color="#444444",
        )
        self.btn_refresh.pack(side="right")

    def apply_treeview_theme(self, mode: str) -> None:
        """Sincroniza los colores del Treeview con el modo de apariencia actual."""
        resolved = mode.lower()
        if resolved == "system":
            resolved = ctk.get_appearance_mode().lower()

        if resolved == "light":
            bg, fg, head_bg, head_fg = "#ffffff", "#1f2328", "#e2e8f0", "#1f2328"
        else:
            bg, fg, head_bg, head_fg = "#1e1e1e", "#f0f0f0", "#2d3748", "#ffffff"

        self._tree_style.configure(
            "Actas.Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=26,
            font=("Segoe UI", 10),
        )
        self._tree_style.configure(
            "Actas.Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        self._tree_style.map(
            "Actas.Treeview",
            background=[("selected", "#1f6aa5")],
            foreground=[("selected", "#ffffff")],
        )

    def refresh_records(self) -> None:
        """Carga y renderiza los registros en la tabla."""
        query = self.entry_search.get().strip() if hasattr(self, "entry_search") else ""
        if query:
            records = self.repo.search(query)
        else:
            records = self.repo.get_all()

        tipo_filtro = self.combo_filter_tipo.get() if hasattr(self, "combo_filter_tipo") else "Todos"
        if tipo_filtro and tipo_filtro != "Todos":
            records = [r for r in records if r.tipo_sesion.strip().lower() == tipo_filtro.strip().lower()]

        self.registros_actuales = records

        # Limpiar filas existentes
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Poblar filas
        for idx, rec in enumerate(self.registros_actuales):
            hash_display = f"{rec.sha256_original[:12]}...{rec.sha256_original[-8:]}"
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    rec.num_sesion,
                    rec.tipo_sesion,
                    rec.fecha_sesion,
                    rec.nombre_archivo_original,
                    rec.total_paginas,
                    rec.fecha_registro,
                    hash_display,
                ),
            )

        total = len(self.registros_actuales)
        self.lbl_count.configure(text=f"{total} registro{'s' if total != 1 else ''}")
        self._clear_selection()

    def _on_search_key(self, event=None) -> None:
        self.refresh_records()

    def _on_filter_change(self, choice: str = "Todos") -> None:
        self.refresh_records()

    def _on_clear_search(self) -> None:
        self.entry_search.delete(0, "end")
        if hasattr(self, "combo_filter_tipo"):
            self.combo_filter_tipo.set("Todos")
        self.refresh_records()

    def _on_row_select(self, event=None) -> None:
        selected_items = self.tree.selection()
        if not selected_items:
            self._clear_selection()
            return

        idx = int(selected_items[0])
        if 0 <= idx < len(self.registros_actuales):
            self.registro_seleccionado = self.registros_actuales[idx]

            # Actualizar panel de detalle — Hash del PDF Generado
            self.lbl_full_hash_gen.configure(state="normal")
            self.lbl_full_hash_gen.delete(0, "end")
            hash_gen = self.registro_seleccionado.sha256_con_hash or "(no disponible — registro anterior)"
            self.lbl_full_hash_gen.insert(0, hash_gen)
            self.lbl_full_hash_gen.configure(state="readonly")

            # Actualizar panel de detalle — Hash del Original
            self.lbl_full_hash.configure(state="normal")
            self.lbl_full_hash.delete(0, "end")
            self.lbl_full_hash.insert(0, self.registro_seleccionado.sha256_original)
            self.lbl_full_hash.configure(state="readonly")

            obs_txt = self.registro_seleccionado.observacion or "Sin observaciones registradas."
            self.lbl_detail_extra.configure(
                text=f"Observación: {obs_txt} | Archivo generado: {self.registro_seleccionado.nombre_archivo_con_hash}",
                text_color="#d0d7de",
            )

            # Habilitar botones de acción
            self.btn_copy_hash.configure(state="normal")
            self.btn_load_verifier.configure(state="normal")
            self.btn_open_pdf.configure(state="normal")
            self.btn_copy_ficha.configure(state="normal")

    def _clear_selection(self) -> None:
        self.registro_seleccionado = None
        self.lbl_full_hash_gen.configure(state="normal")
        self.lbl_full_hash_gen.delete(0, "end")
        self.lbl_full_hash_gen.configure(state="readonly")
        self.lbl_full_hash.configure(state="normal")
        self.lbl_full_hash.delete(0, "end")
        self.lbl_full_hash.configure(state="readonly")
        self.lbl_detail_extra.configure(
            text="Observación: Ningún registro seleccionado.",
            text_color="#8c9ba5",
        )
        self.btn_copy_hash.configure(state="disabled")
        self.btn_load_verifier.configure(state="disabled")
        self.btn_open_pdf.configure(state="disabled")
        self.btn_copy_ficha.configure(state="disabled")

    def _on_double_click(self, event=None) -> None:
        self._on_open_pdf()

    def _on_copy_hash(self) -> None:
        if self.registro_seleccionado:
            # Preferir el hash del PDF generado si existe (es el verificable)
            h = self.registro_seleccionado.sha256_con_hash or self.registro_seleccionado.sha256_original
            self.clipboard_clear()
            self.clipboard_append(h)
            self.update()
            tipo = "PDF Generado" if self.registro_seleccionado.sha256_con_hash else "Original"
            messagebox.showinfo("Copiado", f"Hash ({tipo}) copiado al portapapeles:\n\n{h}")

    def _on_copy_ficha(self) -> None:
        if self.registro_seleccionado:
            ficha = self.registro_seleccionado.format_ficha_libro_fisico()
            self.clipboard_clear()
            self.clipboard_append(ficha)
            self.update()
            messagebox.showinfo(
                "Ficha Copiada",
                f"Se copió la ficha de la sesión {self.registro_seleccionado.num_sesion} para asentar en el Libro Físico.",
            )

    def _on_load_in_verifier(self) -> None:
        if self.registro_seleccionado and self.on_load_in_verifier:
            # Cargar el hash del PDF generado si existe (verificación directa e inmediata)
            h = self.registro_seleccionado.sha256_con_hash or self.registro_seleccionado.sha256_original
            self.on_load_in_verifier(h)

    def _on_open_pdf(self) -> None:
        if not self.registro_seleccionado:
            return

        ruta = Path(self.registro_seleccionado.ruta_archivo_con_hash)
        if not ruta.exists():
            messagebox.showerror(
                "Archivo no encontrado",
                f"No se encontró el archivo con hash en la ruta:\n{ruta}",
            )
            return

        if sys.platform == "win32":
            os.startfile(str(ruta))
        else:
            subprocess.run(["xdg-open", str(ruta)])

    def _on_export_csv(self) -> None:
        try:
            ruta_csv = self.repo.export_to_csv(self.registros_actuales)
            resp = messagebox.askyesno(
                "Exportación Exitosa",
                f"Se han exportado {len(self.registros_actuales)} registros a CSV con codificación UTF-8 para Excel:\n\n"
                f"{ruta_csv.name}\n\n"
                f"¿Desea abrir el archivo ahora?",
            )
            if resp:
                if sys.platform == "win32":
                    os.startfile(str(ruta_csv))
                else:
                    subprocess.run(["xdg-open", str(ruta_csv)])
        except Exception as e:
            messagebox.showerror("Error al Exportar", f"No se pudo completar la exportación a CSV:\n{str(e)}")

    def _on_backup_zip(self) -> None:
        """Genera un archivo ZIP de respaldo preventivo con registro y carpetas de actas."""
        try:
            zip_path = self.crear_respaldo_zip()
            resp = messagebox.askyesno(
                "Respaldo ZIP Generado",
                f"Se creó exitosamente el respaldo preventivo:\n\n"
                f"• Archivo: {zip_path.name}\n"
                f"• Ubicación: {zip_path.parent}\n\n"
                f"¿Desea abrir la carpeta de exportaciones?",
            )
            if resp:
                if sys.platform == "win32":
                    subprocess.run(["explorer", str(zip_path.parent)])
                else:
                    subprocess.run(["xdg-open", str(zip_path.parent)])
        except Exception as e:
            messagebox.showerror("Error de Respaldo", f"No se pudo crear el respaldo ZIP:\n{str(e)}")

    @staticmethod
    def crear_respaldo_zip(output_dir: Optional[Path] = None) -> Path:
        """Empaqueta el registro (JSON o cifrado) y las carpetas de PDFs en un archivo ZIP."""
        dest_dir = Path(output_dir) if output_dir else cfg.DIR_EXPORTACIONES
        dest_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = dest_dir / f"respaldo_certiacta_{timestamp}.zip"

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for data_file in (cfg.FILE_REGISTRO, cfg.FILE_REGISTRO_ENC, cfg.FILE_VAULT):
                if data_file.exists():
                    zf.write(data_file, arcname=f"datos/{data_file.name}")

            for folder_name, folder_path in (
                ("01_Escaneos_Originales", cfg.DIR_ORIGINALES),
                ("02_Actas_Con_Hash", cfg.DIR_CON_HASH),
            ):
                if folder_path.exists():
                    for file_path in folder_path.rglob("*"):
                        if file_path.is_file():
                            rel = file_path.relative_to(folder_path)
                            zf.write(file_path, arcname=f"{folder_name}/{rel}")

        return zip_path
