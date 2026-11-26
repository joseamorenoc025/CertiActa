"""
Ventana Principal de la Aplicación de Escritorio.
Orquesta las pestañas principales, el repositorio local, la bóveda criptográfica (Modo Dual) y los ajustes.
"""

from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk

import src.config as cfg
from src.config import APP_AUTHOR, APP_GEOMETRY, APP_MIN_SIZE, APP_TITLE, FILE_ICON
from src.core.settings import load_settings
from src.core.vault import VaultError, VaultManager
from src.repository.registry_repo import RegistryRepository
from src.ui.tab_records import TabRecords
from src.ui.tab_settings import TabSettings
from src.ui.tab_stamper import TabStamper
from src.ui.tab_verifier import TabVerifier


class _LockOverlay(ctk.CTkFrame):
    """Panel de bloqueo mostrado sobre pestañas protegidas cuando la bóveda está cerrada."""

    def __init__(self, master, on_unlock_attempt, on_recover_click):
        super().__init__(master, corner_radius=12)
        self.on_unlock_attempt = on_unlock_attempt

        box = ctk.CTkFrame(self, fg_color="transparent")
        box.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            box,
            text="🔒 Bóveda Protegida",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            box,
            text="Ingrese la Contraseña Maestra para acceder al estampado, registro y ajustes.\n"
                 "La pestaña 'Auditar / Verificar' sigue disponible libremente.",
            font=ctk.CTkFont(size=12),
            text_color="#8c9ba5",
            justify="center",
        ).pack(pady=(0, 16))

        self.entry_pw = ctk.CTkEntry(box, show="*", width=280, placeholder_text="Contraseña maestra...")
        self.entry_pw.pack(pady=(0, 10))
        self.entry_pw.bind("<Return>", lambda _e: self._submit())

        ctk.CTkButton(
            box,
            text="🔓 Desbloquear",
            width=280,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._submit,
        ).pack(pady=(0, 10))

        ctk.CTkButton(
            box,
            text="🗝 ¿Olvidaste la contraseña? Recuperar con Semilla o .key",
            fg_color="transparent",
            hover_color="#2a3441",
            text_color="#58a6ff",
            font=ctk.CTkFont(size=12, underline=True),
            command=on_recover_click,
        ).pack()

    def _submit(self) -> None:
        pw = self.entry_pw.get()
        self.entry_pw.delete(0, "end")
        self.on_unlock_attempt(pw)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Cargar preferencias y aplicar Carpeta de Trabajo activa
        self.settings = load_settings()
        cfg.apply_work_dir(self.settings.get_work_dir_path())
        cfg.init_directories()

        # Bóveda criptográfica y repositorio
        self.vault = VaultManager(cfg.FILE_VAULT)
        self.repository = RegistryRepository(vault=self.vault)

        # Configuración de apariencia y ventana
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.minsize(*APP_MIN_SIZE)

        if FILE_ICON.exists():
            try:
                self.iconbitmap(str(FILE_ICON))
            except Exception:
                pass

        self._lock_overlays: dict[str, _LockOverlay] = {}
        self._build_header()
        self._build_tabs()
        self._sync_lock_state()

    def _build_header(self) -> None:
        """Construye la barra superior con identidad visual y selector de modo oscuro/claro."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#182230")
        header_frame.pack(fill="x", side="top")

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            title_box,
            text="🛡️ CertiActa — Verificador de Actas SHA-256",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text=f"Creado por: {APP_AUTHOR}",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(anchor="w")

        theme_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_box.pack(side="right", padx=20, pady=12)

        self.btn_lock_app = ctk.CTkButton(
            theme_box,
            text="🔒 Bloquear",
            width=95,
            fg_color="#334455",
            hover_color="#223344",
            command=self._on_lock_app,
        )

        self.theme_switch = ctk.CTkOptionMenu(
            theme_box,
            values=["Oscuro", "Claro", "Sistema"],
            command=self._on_change_theme,
            width=110,
        )
        self.theme_switch.set("Oscuro")
        self.theme_switch.pack(side="right")

    def _build_tabs(self) -> None:
        """Construye el contenedor principal de pestañas."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        for name in ("Estampar y Registrar", "Auditar / Verificar", "Registro Local", "⚙ Ajustes"):
            self.tabview.add(name)

        self.tab_stamper = TabStamper(
            master=self.tabview.tab("Estampar y Registrar"),
            repository=self.repository,
            on_record_saved=self._on_record_saved,
            settings=self.settings,
            vault=self.vault,
        )
        self.tab_stamper.pack(fill="both", expand=True)

        self.tab_verifier = TabVerifier(
            master=self.tabview.tab("Auditar / Verificar"),
            repository=self.repository,
        )
        self.tab_verifier.pack(fill="both", expand=True)

        self.tab_records = TabRecords(
            master=self.tabview.tab("Registro Local"),
            repository=self.repository,
            on_load_in_verifier=self._on_load_in_verifier,
        )
        self.tab_records.pack(fill="both", expand=True)

        self.tab_settings = TabSettings(
            master=self.tabview.tab("⚙ Ajustes"),
            settings=self.settings,
            vault=self.vault,
            repository=self.repository,
            on_work_dir_changed=self._on_work_dir_changed,
            on_vault_state_changed=self._sync_lock_state,
        )
        self.tab_settings.pack(fill="both", expand=True)

    def _sync_lock_state(self) -> None:
        """Aplica Modo Dual: bloquea pestañas sensibles si la bóveda está activa y cerrada."""
        locked = self.settings.vault_enabled and self.vault.is_initialized() and not self.vault.is_unlocked()
        protected_tabs = {
            "Estampar y Registrar": self.tab_stamper,
            "Registro Local": self.tab_records,
            "⚙ Ajustes": self.tab_settings,
        }

        if locked:
            self.btn_lock_app.pack_forget()
            for tab_name, widget in protected_tabs.items():
                widget.pack_forget()
                if tab_name not in self._lock_overlays:
                    overlay = _LockOverlay(
                        self.tabview.tab(tab_name),
                        on_unlock_attempt=self._on_unlock_attempt,
                        on_recover_click=self._on_open_recovery_dialog,
                    )
                    self._lock_overlays[tab_name] = overlay
                self._lock_overlays[tab_name].pack(fill="both", expand=True)
        else:
            for tab_name, overlay in self._lock_overlays.items():
                overlay.pack_forget()
            for tab_name, widget in protected_tabs.items():
                widget.pack(fill="both", expand=True)
            self.tab_records.refresh_records()
            self.tab_settings.refresh_state()

            if self.settings.vault_enabled and self.vault.is_initialized():
                self.btn_lock_app.pack(side="left", padx=(0, 10))
            else:
                self.btn_lock_app.pack_forget()

    def _on_unlock_attempt(self, password: str) -> None:
        if not password:
            return
        if self.vault.unlock_with_password(password):
            self._sync_lock_state()
        else:
            messagebox.showerror("Contraseña Incorrecta", "La contraseña maestra ingresada no es válida.")

    def _on_lock_app(self) -> None:
        self.vault.lock()
        self._sync_lock_state()

    def _on_open_recovery_dialog(self) -> None:
        """Permite restablecer la contraseña usando la Frase Semilla de 12 palabras o un archivo .key."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Recuperar Acceso a la Bóveda")
        dialog.geometry("500x360")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Restablecer Contraseña Maestra",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(16, 6))

        ctk.CTkLabel(
            dialog,
            text="Pegue sus 12 palabras de Frase Semilla (separadas por espacios) o cargue su archivo .key:",
            font=ctk.CTkFont(size=12),
            text_color="#8c9ba5",
            wraplength=450,
        ).pack(padx=20, pady=(0, 10))

        e_seed = ctk.CTkTextbox(dialog, height=70, font=ctk.CTkFont(family="Consolas", size=12))
        e_seed.pack(fill="x", padx=25, pady=(0, 10))

        e_new1 = ctk.CTkEntry(dialog, show="*", placeholder_text="Nueva contraseña maestra (mín. 6)...")
        e_new1.pack(fill="x", padx=25, pady=(0, 8))
        e_new2 = ctk.CTkEntry(dialog, show="*", placeholder_text="Confirmar nueva contraseña...")
        e_new2.pack(fill="x", padx=25, pady=(0, 14))

        def validar_nuevas() -> str | None:
            p1, p2 = e_new1.get(), e_new2.get()
            if len(p1) < 6:
                messagebox.showwarning("Aviso", "La nueva contraseña debe tener al menos 6 caracteres.", parent=dialog)
                return None
            if p1 != p2:
                messagebox.showwarning("Aviso", "Las contraseñas nuevas no coinciden.", parent=dialog)
                return None
            return p1

        def recuperar_semilla():
            new_pw = validar_nuevas()
            if not new_pw:
                return
            seed = e_seed.get("1.0", "end").strip()
            try:
                if self.vault.recover_with_seed(seed, new_pw):
                    dialog.destroy()
                    self._sync_lock_state()
                    messagebox.showinfo("Acceso Recuperado", "Contraseña restablecida y bóveda desbloqueada.")
                else:
                    messagebox.showerror("Semilla Inválida", "La Frase Semilla ingresada no coincide.", parent=dialog)
            except VaultError as ve:
                messagebox.showerror("Error", str(ve), parent=dialog)

        def recuperar_key():
            new_pw = validar_nuevas()
            if not new_pw:
                return
            ruta = filedialog.askopenfilename(
                parent=dialog,
                title="Seleccionar Archivo Llave (.key)",
                filetypes=[("Archivo Llave CertiActa", "*.key")],
            )
            if not ruta:
                return
            try:
                if self.vault.recover_with_key_file(Path(ruta), new_pw):
                    dialog.destroy()
                    self._sync_lock_state()
                    messagebox.showinfo("Acceso Recuperado", "Contraseña restablecida mediante archivo .key.")
                else:
                    messagebox.showerror("Archivo Inválido", "El archivo .key no corresponde a esta bóveda.", parent=dialog)
            except VaultError as ve:
                messagebox.showerror("Error", str(ve), parent=dialog)

        row_btns = ctk.CTkFrame(dialog, fg_color="transparent")
        row_btns.pack(fill="x", padx=25)
        ctk.CTkButton(row_btns, text="✔ Recuperar con Semilla", command=recuperar_semilla, width=215).pack(
            side="left", padx=(0, 10)
        )
        ctk.CTkButton(
            row_btns,
            text="🔑 Cargar Archivo .key",
            command=recuperar_key,
            width=215,
            fg_color="#334455",
            hover_color="#223344",
        ).pack(side="left")

    def _on_work_dir_changed(self, _new_dir: Path) -> None:
        self.tab_records.refresh_records()

    def _on_change_theme(self, choice: str) -> None:
        mapping = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}
        mode = mapping.get(choice, "dark")
        ctk.set_appearance_mode(mode)
        self.tab_records.apply_treeview_theme(mode)

    def _on_record_saved(self) -> None:
        """Notificación disparada cuando se estampa y guarda una nueva acta."""
        self.tab_records.refresh_records()

    def _on_load_in_verifier(self, sha256_hash: str) -> None:
        """Carga el hash seleccionado desde el registro y activa la pestaña de auditoría."""
        self.tab_verifier.set_reference_hash(sha256_hash)
        self.tabview.set("Auditar / Verificar")
