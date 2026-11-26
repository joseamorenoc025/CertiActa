"""
Pestaña 4: Ajustes del Sistema.
Permite configurar la Carpeta de Trabajo (con migración de datos) y la Bóveda Criptográfica opcional
(Contraseña Maestra, Frase Semilla de 12 palabras, archivo .key y protección de edición en PDFs).
"""

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

import src.config as cfg
from src.core.settings import AppSettings, migrate_work_dir, save_settings
from src.core.vault import VaultError, VaultManager
from src.repository.registry_repo import RegistryRepository


class TabSettings(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master,
        settings: AppSettings,
        vault: VaultManager,
        repository: RegistryRepository,
        on_work_dir_changed: Callable[[Path], None],
        on_vault_state_changed: Callable[[], None],
    ):
        super().__init__(master)
        self.settings = settings
        self.vault = vault
        self.repo = repository
        self.on_work_dir_changed = on_work_dir_changed
        self.on_vault_state_changed = on_vault_state_changed

        self._build_ui()
        self.refresh_state()

    def _build_ui(self) -> None:
        # 1. Tarjeta: Carpeta de Trabajo
        card_dir = ctk.CTkFrame(self, corner_radius=10)
        card_dir.pack(fill="x", padx=15, pady=(10, 10))

        ctk.CTkLabel(
            card_dir,
            text="1. Carpeta de Trabajo y Almacenamiento",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            card_dir,
            text="Define dónde se guardan las carpetas '01_Escaneos_Originales/', '02_Actas_Con_Hash/' y 'datos/'.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#8c9ba5",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        row_dir = ctk.CTkFrame(card_dir, fg_color="transparent")
        row_dir.pack(fill="x", padx=15, pady=(0, 14))

        self.entry_work_dir = ctk.CTkEntry(row_dir, font=ctk.CTkFont(size=12))
        self.entry_work_dir.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_work_dir.configure(state="readonly")

        self.btn_change_dir = ctk.CTkButton(
            row_dir,
            text="📁 Cambiar Carpeta...",
            width=155,
            command=self._on_change_work_dir,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_change_dir.pack(side="left", padx=(0, 8))

        self.btn_open_dir = ctk.CTkButton(
            row_dir,
            text="📂 Abrir",
            width=85,
            fg_color="#445566",
            hover_color="#2f3b47",
            command=self._on_open_work_dir,
        )
        self.btn_open_dir.pack(side="left")

        # 2. Tarjeta: Bóveda Criptográfica y Seguridad Opcional
        card_sec = ctk.CTkFrame(self, corner_radius=10)
        card_sec.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            card_sec,
            text="2. Bóveda Criptográfica y Protección Opcional",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            card_sec,
            text=(
                "Cifra la base de datos local con AES-256-GCM y genera una Frase Semilla de 12 palabras para recuperar el acceso. "
                "La pestaña 'Auditar / Verificar' siempre permanece disponible sin contraseña."
            ),
            font=ctk.CTkFont(size=12),
            text_color="#8c9ba5",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.lbl_vault_status = ctk.CTkLabel(
            card_sec,
            text="Estado: Desactivada",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_vault_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Contenedor dinámico según estado de la bóveda
        self.frame_vault_controls = ctk.CTkFrame(card_sec, fg_color="transparent")
        self.frame_vault_controls.pack(fill="x", padx=15, pady=(0, 14))

    def refresh_state(self) -> None:
        """Actualiza los controles visuales según la configuración y estado de la bóveda."""
        self.entry_work_dir.configure(state="normal")
        self.entry_work_dir.delete(0, "end")
        self.entry_work_dir.insert(0, str(cfg.BASE_DIR))
        self.entry_work_dir.configure(state="readonly")

        for w in self.frame_vault_controls.winfo_children():
            w.destroy()

        if self.settings.vault_enabled and self.vault.is_initialized():
            self.lbl_vault_status.configure(
                text="Estado: Activada y Desbloqueada (AES-256-GCM)",
                text_color="#2ea043",
            )

            self.var_pdf_protect = ctk.BooleanVar(value=self.settings.pdf_owner_protect)
            chk_pdf = ctk.CTkCheckBox(
                self.frame_vault_controls,
                text="Proteger PDFs generados contra edición (contraseña de propietario; lectura libre para Contraloría)",
                variable=self.var_pdf_protect,
                command=self._on_toggle_pdf_protect,
                font=ctk.CTkFont(size=12),
            )
            chk_pdf.pack(anchor="w", pady=(0, 12))

            row_btns = ctk.CTkFrame(self.frame_vault_controls, fg_color="transparent")
            row_btns.pack(fill="x")

            ctk.CTkButton(
                row_btns,
                text="🔑 Cambiar Contraseña",
                command=self._on_change_password,
                width=165,
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                row_btns,
                text="💾 Exportar Archivo Llave (.key)",
                command=self._on_export_key_file,
                width=200,
                fg_color="#334455",
                hover_color="#223344",
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                row_btns,
                text="🔓 Desactivar Cifrado",
                command=self._on_disable_vault,
                width=160,
                fg_color="#9e2a2b",
                hover_color="#781e1f",
            ).pack(side="left")
        else:
            self.lbl_vault_status.configure(
                text="Estado: Desactivada (registro local en texto plano JSON)",
                text_color="#d29922",
            )
            ctk.CTkButton(
                self.frame_vault_controls,
                text="🔒 Activar Contraseña Maestra y Frase Semilla...",
                command=self._on_enable_vault,
                height=38,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#1f6aa5",
                hover_color="#144d75",
            ).pack(anchor="w")

    def _on_open_work_dir(self) -> None:
        if cfg.BASE_DIR.exists():
            if sys.platform == "win32":
                subprocess.run(["explorer", str(cfg.BASE_DIR)])
            else:
                subprocess.run(["xdg-open", str(cfg.BASE_DIR)])

    def _on_change_work_dir(self) -> None:
        nueva = filedialog.askdirectory(
            title="Seleccionar nueva Carpeta de Trabajo para CertiActa",
            initialdir=str(cfg.BASE_DIR),
        )
        if not nueva:
            return

        old_dir = cfg.BASE_DIR.resolve()
        new_dir = Path(nueva).resolve()
        if new_dir == old_dir:
            return

        if old_dir in new_dir.parents:
            messagebox.showwarning(
                "Carpeta Inválida",
                "No seleccione una subcarpeta dentro de la carpeta actual de trabajo.",
            )
            return

        resp_migrar = messagebox.askyesnocancel(
            "Migrar Datos Existentes",
            f"Nueva carpeta seleccionada:\n{new_dir}\n\n"
            "¿Desea trasladar las actas y el registro existentes ('datos/', '01_Escaneos_Originales/', "
            "'02_Actas_Con_Hash/') hacia la nueva carpeta?\n\n"
            "• Sí: Traslada los datos existentes.\n"
            "• No: Inicia la nueva carpeta sin trasladar archivos.\n"
            "• Cancelar: Mantiene la carpeta actual.",
        )
        if resp_migrar is None:
            return

        try:
            moved_count = 0
            if resp_migrar:
                mover = messagebox.askyesno(
                    "Modo de Traslado",
                    "¿Desea MOVER los archivos (quitarlos de la carpeta anterior)?\n\n"
                    "• Sí = Mover archivos\n"
                    "• No = Copiar archivos (conserva respaldo en la carpeta anterior)",
                )
                moved_count = migrate_work_dir(old_dir, new_dir, mode="move" if mover else "copy")

            self.settings.work_dir = str(new_dir)
            save_settings(self.settings)
            cfg.apply_work_dir(new_dir)
            cfg.init_directories()
            self.vault.set_vault_path(cfg.FILE_VAULT)
            self.on_work_dir_changed(new_dir)
            self.refresh_state()

            msg = f"Carpeta de trabajo actualizada a:\n{new_dir}"
            if resp_migrar:
                msg += f"\n\nArchivos trasladados: {moved_count}"
            messagebox.showinfo("Carpeta Actualizada", msg)
        except Exception as e:
            messagebox.showerror("Error al Cambiar Carpeta", f"No se pudo completar el cambio:\n{str(e)}")

    def _on_toggle_pdf_protect(self) -> None:
        self.settings.pdf_owner_protect = bool(self.var_pdf_protect.get())
        save_settings(self.settings)

    def _on_enable_vault(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Activar Bóveda Criptográfica")
        dialog.geometry("430x290")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Configurar Contraseña Maestra",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(padx=20, pady=(16, 6))

        ctk.CTkLabel(
            dialog,
            text="Mínimo 6 caracteres. Se generará una Frase Semilla de 12 palabras para recuperación.",
            font=ctk.CTkFont(size=11),
            text_color="#8c9ba5",
            wraplength=380,
        ).pack(padx=20, pady=(0, 12))

        entry_pw1 = ctk.CTkEntry(dialog, show="*", placeholder_text="Nueva contraseña maestra...")
        entry_pw1.pack(fill="x", padx=25, pady=(0, 10))

        entry_pw2 = ctk.CTkEntry(dialog, show="*", placeholder_text="Confirmar contraseña maestra...")
        entry_pw2.pack(fill="x", padx=25, pady=(0, 16))

        def confirmar():
            p1 = entry_pw1.get()
            p2 = entry_pw2.get()
            if len(p1) < 6:
                messagebox.showwarning("Contraseña Corta", "Debe tener al menos 6 caracteres.", parent=dialog)
                return
            if p1 != p2:
                messagebox.showwarning("No Coincide", "Las contraseñas ingresadas no coinciden.", parent=dialog)
                return
            try:
                seed_phrase = self.vault.create_vault(p1)
                self.repo.migrate_to_encrypted()
                self.settings.vault_enabled = True
                save_settings(self.settings)
                dialog.destroy()
                self.refresh_state()
                self.on_vault_state_changed()
                self._show_seed_modal(seed_phrase)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo activar la bóveda:\n{str(e)}", parent=dialog)

        ctk.CTkButton(dialog, text="🔒 Activar Bóveda y Generar Semilla", command=confirmar, height=36).pack(
            fill="x", padx=25
        )
        entry_pw1.focus()

    def _show_seed_modal(self, seed_phrase: str) -> None:
        """Muestra la Frase Semilla de 12 palabras una única vez con opciones de copia y archivo .key."""
        modal = ctk.CTkToplevel(self)
        modal.title("Frase Semilla de Recuperación — ¡GUARDE EN LUGAR SEGURO!")
        modal.geometry("560x410")
        modal.resizable(False, False)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text="🔑 Tu Frase Semilla de Recuperación (12 palabras)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2ea043",
        ).pack(padx=20, pady=(16, 6))

        ctk.CTkLabel(
            modal,
            text=(
                "Anote estas 12 palabras en orden exacto en su Libro Físico o resguardo seguro. "
                "Permiten restablecer la contraseña sin perder ningún registro."
            ),
            font=ctk.CTkFont(size=12),
            wraplength=510,
        ).pack(padx=20, pady=(0, 12))

        words = seed_phrase.split()
        numbered = "\n".join(
            f"{i+1:02d}. {words[i]:<14}   {i+7:02d}. {words[i+6]}"
            for i in range(6)
        ) if len(words) == 12 else seed_phrase

        box = ctk.CTkTextbox(modal, height=145, font=ctk.CTkFont(family="Consolas", size=14, weight="bold"))
        box.pack(fill="x", padx=25, pady=(0, 14))
        box.insert("1.0", numbered)
        box.configure(state="disabled")

        hoja_txt = (
            "=== CERTIACTA | HOJA DE RECUPERACIÓN DE BÓVEDA ===\n"
            f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Carpeta de trabajo: {cfg.BASE_DIR}\n\n"
            "Frase Semilla (12 palabras en orden exacto):\n"
            f"{seed_phrase}\n\n"
            "Guarde esta hoja bajo llave o en su Libro Físico de Respaldo.\n"
            "===================================================\n"
        )

        row_actions = ctk.CTkFrame(modal, fg_color="transparent")
        row_actions.pack(fill="x", padx=25, pady=(0, 12))

        def copiar_hoja():
            self.clipboard_clear()
            self.clipboard_append(hoja_txt)
            self.update()
            messagebox.showinfo("Copiado", "Hoja de recuperación copiada al portapapeles.", parent=modal)

        def guardar_txt():
            ruta = filedialog.asksaveasfilename(
                parent=modal,
                title="Guardar Hoja de Recuperación",
                defaultextension=".txt",
                initialfile="CertiActa_Recuperacion_Semilla.txt",
                filetypes=[("Archivo de texto", "*.txt")],
            )
            if ruta:
                Path(ruta).write_text(hoja_txt, encoding="utf-8")
                messagebox.showinfo("Guardado", f"Hoja guardada en:\n{ruta}", parent=modal)

        ctk.CTkButton(row_actions, text="📋 Copiar Hoja", command=copiar_hoja, width=130).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row_actions, text="📄 Guardar (.txt)", command=guardar_txt, width=135).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row_actions,
            text="🔑 Exportar .key (Opcional)",
            command=self._on_export_key_file,
            width=180,
            fg_color="#334455",
            hover_color="#223344",
        ).pack(side="left")

        ctk.CTkButton(
            modal,
            text="✔ Ya anoté mi Frase Semilla en lugar seguro",
            command=modal.destroy,
            height=38,
            fg_color="#2b7842",
            hover_color="#1e542e",
        ).pack(fill="x", padx=25, pady=(4, 15))

    def _on_export_key_file(self) -> None:
        ruta = filedialog.asksaveasfilename(
            title="Exportar Archivo Llave de Recuperación (.key)",
            defaultextension=".key",
            initialfile="certiacta_recuperacion.key",
            filetypes=[("Archivo Llave CertiActa", "*.key")],
        )
        if not ruta:
            return
        try:
            self.vault.export_key_file(Path(ruta))
            messagebox.showinfo(
                "Archivo Llave Exportado",
                f"Se guardó el archivo llave en:\n{ruta}\n\nGuárdelo en un pendrive externo seguro.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el archivo llave:\n{str(e)}")

    def _on_change_password(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Cambiar Contraseña Maestra")
        dialog.geometry("420x310")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Cambiar Contraseña Maestra", font=ctk.CTkFont(size=15, weight="bold")).pack(
            pady=(16, 12)
        )
        e_curr = ctk.CTkEntry(dialog, show="*", placeholder_text="Contraseña actual...")
        e_curr.pack(fill="x", padx=25, pady=(0, 10))
        e_new1 = ctk.CTkEntry(dialog, show="*", placeholder_text="Nueva contraseña (mín. 6)...")
        e_new1.pack(fill="x", padx=25, pady=(0, 10))
        e_new2 = ctk.CTkEntry(dialog, show="*", placeholder_text="Confirmar nueva contraseña...")
        e_new2.pack(fill="x", padx=25, pady=(0, 16))

        def guardar():
            if e_new1.get() != e_new2.get():
                messagebox.showwarning("No Coincide", "Las contraseñas nuevas no coinciden.", parent=dialog)
                return
            try:
                ok = self.vault.change_password(e_curr.get(), e_new1.get())
                if not ok:
                    messagebox.showerror("Incorrecta", "La contraseña actual no es válida.", parent=dialog)
                    return
                dialog.destroy()
                messagebox.showinfo("Actualizada", "La contraseña maestra fue actualizada correctamente.")
            except VaultError as ve:
                messagebox.showwarning("Aviso", str(ve), parent=dialog)

        ctk.CTkButton(dialog, text="Guardar Nueva Contraseña", command=guardar, height=36).pack(fill="x", padx=25)
        e_curr.focus()

    def _on_disable_vault(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Desactivar Cifrado de Bóveda")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Confirme su contraseña para descifrar el registro a JSON plano:",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=370,
        ).pack(padx=20, pady=(18, 12))

        e_pw = ctk.CTkEntry(dialog, show="*", placeholder_text="Contraseña maestra actual...")
        e_pw.pack(fill="x", padx=25, pady=(0, 16))

        def confirmar():
            if not self.vault.unlock_with_password(e_pw.get()):
                messagebox.showerror("Incorrecta", "La contraseña ingresada no es válida.", parent=dialog)
                return
            try:
                self.repo.migrate_to_plaintext()
                self.vault.remove_vault()
                self.settings.vault_enabled = False
                self.settings.pdf_owner_protect = False
                save_settings(self.settings)
                dialog.destroy()
                self.refresh_state()
                self.on_vault_state_changed()
                messagebox.showinfo("Cifrado Desactivado", "El registro volvió a formato JSON estándar.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo desactivar el cifrado:\n{str(e)}", parent=dialog)

        ctk.CTkButton(
            dialog,
            text="Desactivar Cifrado",
            command=confirmar,
            fg_color="#9e2a2b",
            hover_color="#781e1f",
            height=36,
        ).pack(fill="x", padx=25)
        e_pw.focus()
