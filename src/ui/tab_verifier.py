"""
Pestaña 2: Auditar / Verificar.
Permite comparar un hash de referencia (o traído del registro) contra un archivo PDF,
mostrando en tiempo real si coincide (verde) o no (rojo), junto a ambos hashes legibles.
Implementa validación cruzada con el registro local para soportar el esquema de doble huella.
"""

import hmac
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from src.core.hasher import calcular_sha256, verificar_sha256
from src.repository.registry_repo import RegistryRepository


class TabVerifier(ctk.CTkScrollableFrame):
    def __init__(self, master, repository: RegistryRepository):
        super().__init__(master)
        self.repo = repository

        self.archivo_a_verificar: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Tarjeta: Hash de Referencia
        card_ref = ctk.CTkFrame(self, corner_radius=10)
        card_ref.pack(fill="x", padx=15, pady=(10, 10))

        lbl_ref_title = ctk.CTkLabel(
            card_ref,
            text="1. Hash SHA-256 de Referencia (Esperado)",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        lbl_ref_title.pack(anchor="w", padx=15, pady=(12, 6))

        lbl_ref_desc = ctk.CTkLabel(
            card_ref,
            text="Pegue el hash a auditar o cárguelo directamente desde la pestaña 'Registro Local'. Acepta tanto el hash del original como el del PDF generado.",
            font=ctk.CTkFont(size=12),
            text_color="#8c9ba5",
            wraplength=900,
            justify="left",
        )
        lbl_ref_desc.pack(anchor="w", padx=15, pady=(0, 10))

        row_ref = ctk.CTkFrame(card_ref, fg_color="transparent")
        row_ref.pack(fill="x", padx=15, pady=(0, 14))

        self.entry_ref_hash = ctk.CTkEntry(
            row_ref,
            placeholder_text="Pegue aquí el hash SHA-256 de 64 caracteres...",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.entry_ref_hash.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_paste = ctk.CTkButton(
            row_ref,
            text="📋 Pegar",
            width=90,
            command=self._on_paste_ref_hash,
        )
        self.btn_paste.pack(side="left", padx=(0, 6))

        self.btn_clear_ref = ctk.CTkButton(
            row_ref,
            text="🧹 Limpiar",
            width=90,
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_clear_ref_hash,
        )
        self.btn_clear_ref.pack(side="left")

        # 2. Tarjeta: Selección de Archivo a Auditar
        card_file = ctk.CTkFrame(self, corner_radius=10)
        card_file.pack(fill="x", padx=15, pady=(0, 10))

        lbl_file_title = ctk.CTkLabel(
            card_file,
            text="2. Archivo PDF a Auditar",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        lbl_file_title.pack(anchor="w", padx=15, pady=(12, 6))

        row_audit = ctk.CTkFrame(card_file, fg_color="transparent")
        row_audit.pack(fill="x", padx=15, pady=(0, 14))

        self.btn_select_audit = ctk.CTkButton(
            row_audit,
            text="📁 Seleccionar PDF...",
            width=160,
            command=self._on_select_audit_file,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_select_audit.pack(side="left", padx=(0, 10))

        self.entry_audit_path = ctk.CTkEntry(
            row_audit,
            placeholder_text="Seleccione el archivo que desea auditar...",
            font=ctk.CTkFont(size=12),
        )
        self.entry_audit_path.pack(side="left", fill="x", expand=True)
        self.entry_audit_path.configure(state="readonly")

        # 3. Botón de Acción Principal
        self.btn_verificar = ctk.CTkButton(
            self,
            text="🔍 Verificar Coincidencia de Integridad",
            command=self._on_verificar,
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
        )
        self.btn_verificar.pack(fill="x", padx=15, pady=(5, 12))

        # 4. Tarjeta de Resultado de Auditoría
        self.card_result = ctk.CTkFrame(self, corner_radius=10)
        self.card_result.pack(fill="x", padx=15, pady=(0, 15))

        self.lbl_verdict_banner = ctk.CTkLabel(
            self.card_result,
            text="Esperando verificación...",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=8,
            height=40,
        )
        self.lbl_verdict_banner.pack(fill="x", padx=15, pady=(15, 12))

        # Comparador de hashes
        frame_hashes = ctk.CTkFrame(self.card_result, fg_color="transparent")
        frame_hashes.pack(fill="x", padx=15, pady=(0, 12))

        # Hash 1: Referencia
        ctk.CTkLabel(frame_hashes, text="Hash de Referencia:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.entry_res_ref = ctk.CTkEntry(
            frame_hashes,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="—",
        )
        self.entry_res_ref.pack(fill="x", pady=(2, 8))
        self.entry_res_ref.configure(state="readonly")

        # Hash 2: Calculado
        ctk.CTkLabel(frame_hashes, text="Hash Calculado del Archivo Analizado:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.entry_res_calc = ctk.CTkEntry(
            frame_hashes,
            font=ctk.CTkFont(family="Consolas", size=11),
            placeholder_text="—",
        )
        self.entry_res_calc.pack(fill="x", pady=(2, 8))
        self.entry_res_calc.configure(state="readonly")

        # Mensaje de inspección inteligente adicional
        self.lbl_smart_note = ctk.CTkLabel(
            self.card_result,
            text="",
            font=ctk.CTkFont(size=12, slant="italic"),
            wraplength=800,
            justify="left",
        )
        self.lbl_smart_note.pack(anchor="w", padx=15, pady=(0, 12))

    def set_reference_hash(self, sha256_hash: str) -> None:
        """Carga programáticamente un hash desde otra pestaña."""
        self.entry_ref_hash.delete(0, "end")
        self.entry_ref_hash.insert(0, sha256_hash.strip())

    def _on_paste_ref_hash(self) -> None:
        try:
            texto = self.clipboard_get().strip()
            if texto:
                self.entry_ref_hash.delete(0, "end")
                self.entry_ref_hash.insert(0, texto)
        except Exception:
            pass

    def _on_clear_ref_hash(self) -> None:
        self.entry_ref_hash.delete(0, "end")

    def _on_select_audit_file(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo a auditar",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return

        path = Path(ruta)
        self.archivo_a_verificar = path

        self.entry_audit_path.configure(state="normal")
        self.entry_audit_path.delete(0, "end")
        self.entry_audit_path.insert(0, str(path))
        self.entry_audit_path.configure(state="readonly")

    def _on_verificar(self) -> None:
        ref_hash = self.entry_ref_hash.get().strip().lower()
        if not ref_hash:
            messagebox.showwarning("Falta Hash", "Por favor ingrese o pegue el hash de referencia a comparar.")
            self.entry_ref_hash.focus()
            return

        if len(ref_hash) != 64:
            messagebox.showwarning(
                "Hash Inválido",
                f"El hash SHA-256 debe tener exactamente 64 caracteres hexadecimales.\nLongitud actual: {len(ref_hash)}"
            )
            return

        if not self.archivo_a_verificar or not self.archivo_a_verificar.exists():
            messagebox.showwarning("Falta Archivo", "Por favor seleccione el archivo PDF que desea auditar.")
            return

        self.btn_verificar.configure(state="disabled")
        self.lbl_verdict_banner.configure(
            text="Auditando documento y calculando huella criptográfica...",
            fg_color="#334455",
            text_color="#ffffff",
        )

        threading.Thread(target=self._async_verify, args=(self.archivo_a_verificar, ref_hash), daemon=True).start()

    def _async_verify(self, file_path: Path, expected_hash: str) -> None:
        try:
            # 1. Comparación directa byte a byte
            coincide_directo, hash_calc = verificar_sha256(file_path, expected_hash)

            # 2. Validación cruzada contra el registro local
            coincide_cruzado = False
            tipo_coincidencia = ""  # "directo", "generado_por_hash_original", "original_por_hash_generado"
            record_encontrado = None

            if coincide_directo:
                tipo_coincidencia = "directo"
            else:
                # Buscar el hash de referencia en el registro local
                record_encontrado = self.repo.find_by_hash(expected_hash)

                if record_encontrado:
                    # Caso A: El usuario pegó sha256_original y el archivo es el _CON_HASH.pdf
                    if (
                        hmac.compare_digest(expected_hash, record_encontrado.sha256_original)
                        and record_encontrado.sha256_con_hash
                        and hmac.compare_digest(hash_calc, record_encontrado.sha256_con_hash)
                    ):
                        coincide_cruzado = True
                        tipo_coincidencia = "generado_por_hash_original"

                    # Caso B: El usuario pegó sha256_con_hash y el archivo es el original
                    elif (
                        hmac.compare_digest(expected_hash, record_encontrado.sha256_con_hash)
                        and hmac.compare_digest(hash_calc, record_encontrado.sha256_original)
                    ):
                        coincide_cruzado = True
                        tipo_coincidencia = "original_por_hash_generado"

            def update_ui():
                self.btn_verificar.configure(state="normal")

                # Actualizar campos de texto
                self.entry_res_ref.configure(state="normal")
                self.entry_res_ref.delete(0, "end")
                self.entry_res_ref.insert(0, expected_hash)
                self.entry_res_ref.configure(state="readonly")

                self.entry_res_calc.configure(state="normal")
                self.entry_res_calc.delete(0, "end")
                self.entry_res_calc.insert(0, hash_calc)
                self.entry_res_calc.configure(state="readonly")

                if coincide_directo:
                    self.lbl_verdict_banner.configure(
                        text="✔ COINCIDE EXACTAMENTE: EL DOCUMENTO ES AUTÉNTICO E ÍNTEGRO",
                        fg_color="#1b5e20",
                        text_color="#ffffff",
                    )
                    self.lbl_smart_note.configure(
                        text="El archivo analizado es matemáticamente idéntico byte a byte al documento registrado.",
                        text_color="#2ea043",
                    )
                elif coincide_cruzado:
                    if tipo_coincidencia == "generado_por_hash_original":
                        self.lbl_verdict_banner.configure(
                            text="✔ VERIFICADO: EL PDF GENERADO (_CON_HASH) ESTÁ ÍNTEGRO",
                            fg_color="#1b5e20",
                            text_color="#ffffff",
                        )
                        self.lbl_smart_note.configure(
                            text=(
                                f"Validación cruzada exitosa contra el registro local.\n\n"
                                f"El hash de referencia ({expected_hash[:16]}...) corresponde al escaneo original.\n"
                                f"El hash del archivo analizado ({hash_calc[:16]}...) coincide exactamente con "
                                f"el SHA-256 del PDF Generado registrado.\n\n"
                                f"Conclusión: El archivo _CON_HASH.pdf no ha sido alterado desde su emisión."
                            ),
                            text_color="#2ea043",
                        )
                    elif tipo_coincidencia == "original_por_hash_generado":
                        self.lbl_verdict_banner.configure(
                            text="✔ VERIFICADO: EL ESCANEO ORIGINAL ESTÁ ÍNTEGRO",
                            fg_color="#1b5e20",
                            text_color="#ffffff",
                        )
                        self.lbl_smart_note.configure(
                            text=(
                                f"Validación cruzada exitosa contra el registro local.\n\n"
                                f"El hash de referencia ({expected_hash[:16]}...) corresponde al PDF generado.\n"
                                f"El hash del archivo analizado ({hash_calc[:16]}...) coincide exactamente con "
                                f"el SHA-256 del escaneo original registrado.\n\n"
                                f"Conclusión: El escaneo original no ha sido alterado."
                            ),
                            text_color="#2ea043",
                        )
                else:
                    self.lbl_verdict_banner.configure(
                        text="✖ NO COINCIDE: LA HUELLA NO CORRESPONDE AL ARCHIVO",
                        fg_color="#b71c1c",
                        text_color="#ffffff",
                    )
                    texto_nota = "El archivo analizado NO es idéntico al documento esperado (ha sido modificado o es otro documento)."
                    if record_encontrado:
                        texto_nota += (
                            f"\n\nSe encontró un registro en la base local para el hash de referencia, pero el hash "
                            f"calculado del archivo ({hash_calc[:16]}...) no coincide con ninguna de las huellas "
                            f"registradas (ni original ni generado)."
                        )
                    self.lbl_smart_note.configure(text=texto_nota, text_color="#f85149")

            self.after(0, update_ui)

        except Exception as e:
            err_msg = str(e)

            def err_ui(msg: str = err_msg):
                self.btn_verificar.configure(state="normal")
                self.lbl_verdict_banner.configure(
                    text="Error durante la auditoría",
                    fg_color="#b71c1c",
                    text_color="#ffffff",
                )
                messagebox.showerror("Error de Verificación", f"No se pudo completar la verificación:\n{msg}")

            self.after(0, err_ui)
