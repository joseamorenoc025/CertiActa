"""
Ventana Principal de la Aplicación de Escritorio.
Orquesta las 3 pestañas principales, el repositorio local y la navegación entre componentes.
"""

import customtkinter as ctk

from src.config import (
    APP_AUTHOR,
    APP_GEOMETRY,
    APP_MIN_SIZE,
    APP_TITLE,
    FILE_ICON,
    init_directories,
)
from src.repository.registry_repo import RegistryRepository
from src.ui.tab_records import TabRecords
from src.ui.tab_stamper import TabStamper
from src.ui.tab_verifier import TabVerifier


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicialización de carpetas requeridas del sistema
        init_directories()

        # Repositorio de datos
        self.repository = RegistryRepository()

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

        self._build_header()
        self._build_tabs()

    def _build_header(self) -> None:
        """Construye la barra superior con identidad visual y selector de modo oscuro/claro."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#182230")
        header_frame.pack(fill="x", side="top")

        # Contenedor de títulos
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_main = ctk.CTkLabel(
            title_box,
            text="🛡️ CertiActa — Verificador de Actas SHA-256",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        )
        lbl_main.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text=f"Creado por: {APP_AUTHOR}",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        lbl_sub.pack(anchor="w")

        # Selector de tema (Dark / Light)
        theme_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_box.pack(side="right", padx=20, pady=12)

        self.theme_switch = ctk.CTkOptionMenu(
            theme_box,
            values=["Oscuro", "Claro", "Sistema"],
            command=self._on_change_theme,
            width=110,
        )
        self.theme_switch.set("Oscuro")
        self.theme_switch.pack()

    def _build_tabs(self) -> None:
        """Construye el contenedor principal de pestañas."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        tab_names = ["Estampar y Registrar", "Auditar / Verificar", "Registro Local"]
        for name in tab_names:
            self.tabview.add(name)

        # 1. Pestaña: Estampar y Registrar
        self.tab_stamper = TabStamper(
            master=self.tabview.tab("Estampar y Registrar"),
            repository=self.repository,
            on_record_saved=self._on_record_saved,
        )
        self.tab_stamper.pack(fill="both", expand=True)

        # 2. Pestaña: Auditar / Verificar
        self.tab_verifier = TabVerifier(
            master=self.tabview.tab("Auditar / Verificar"),
            repository=self.repository,
        )
        self.tab_verifier.pack(fill="both", expand=True)

        # 3. Pestaña: Registro Local
        self.tab_records = TabRecords(
            master=self.tabview.tab("Registro Local"),
            repository=self.repository,
            on_load_in_verifier=self._on_load_in_verifier,
        )
        self.tab_records.pack(fill="both", expand=True)

    def _on_change_theme(self, choice: str) -> None:
        mapping = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}
        ctk.set_appearance_mode(mapping.get(choice, "dark"))

    def _on_record_saved(self) -> None:
        """Notificación disparada cuando se estampa y guarda una nueva acta."""
        self.tab_records.refresh_records()

    def _on_load_in_verifier(self, sha256_hash: str) -> None:
        """Carga el hash seleccionado desde el registro y activa la pestaña de auditoría."""
        self.tab_verifier.set_reference_hash(sha256_hash)
        self.tabview.set("Auditar / Verificar")
