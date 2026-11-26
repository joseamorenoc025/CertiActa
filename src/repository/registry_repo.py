"""
Repositorio para la persistencia de registros de actas en JSON local y exportación a CSV.
Implementa operaciones atómicas de escritura para prevenir corrupción de archivos.
"""

import csv
from datetime import datetime
import json
import os
from pathlib import Path
import threading
from typing import Optional

import src.config as cfg
from src.core.models import ActaRecord
from src.core.vault import VaultManager


class RegistryRepository:
    """Gestiona el almacenamiento local en JSON (o .enc cifrado) con soporte concurrente y atómico."""

    def __init__(self, json_path: Optional[Path] = None, vault: Optional[VaultManager] = None):
        self._custom_path = Path(json_path) if json_path is not None else None
        self.vault = vault
        self._lock = threading.Lock()
        self._ensure_file()

    @property
    def json_path(self) -> Path:
        return self._custom_path if self._custom_path is not None else cfg.FILE_REGISTRO

    @property
    def enc_path(self) -> Path:
        if self._custom_path is not None:
            return self._custom_path.with_suffix(".enc")
        return cfg.FILE_REGISTRO_ENC

    def _use_encrypted(self) -> bool:
        return self.vault is not None and self.vault.is_initialized()

    def _ensure_file(self) -> None:
        """Asegura la existencia del archivo de registro."""
        jp = self.json_path
        if not jp.parent.exists():
            jp.parent.mkdir(parents=True, exist_ok=True)
        if not self._use_encrypted() and (not jp.exists() or jp.stat().st_size == 0):
            jp.write_text("[]", encoding="utf-8")

    def _read_raw_list(self) -> list[dict]:
        """Lee la lista de diccionarios desde .enc (si bóveda activa) o .json."""
        if self._use_encrypted():
            if self.enc_path.exists() and self.vault and self.vault.is_unlocked():
                plain = self.vault.decrypt_bytes(self.enc_path.read_bytes())
                data = json.loads(plain.decode("utf-8"))
                return data if isinstance(data, list) else []
            if not self.enc_path.exists() and self.json_path.exists():
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            return []

        if not self.json_path.exists():
            return []
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_raw_list(self, data: list[dict]) -> None:
        """Persiste de forma atómica en .enc (si bóveda activa) o .json."""
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if self._use_encrypted() and self.vault and self.vault.is_unlocked():
            self.enc_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.enc_path.with_suffix(".tmp")
            tmp.write_bytes(self.vault.encrypt_bytes(payload))
            os.replace(tmp, self.enc_path)
            return

        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.json_path.with_suffix(".tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, self.json_path)

    def migrate_to_encrypted(self) -> None:
        """Cifra registro_actas.json hacia registro_actas.enc y elimina el plano."""
        with self._lock:
            if not (self.vault and self.vault.is_unlocked()):
                raise RuntimeError("La bóveda debe estar desbloqueada para cifrar el registro.")
            data = []
            if self.json_path.exists():
                try:
                    raw = json.loads(self.json_path.read_text(encoding="utf-8"))
                    if isinstance(raw, list):
                        data = raw
                except (json.JSONDecodeError, OSError):
                    data = []
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            tmp = self.enc_path.with_suffix(".tmp")
            tmp.write_bytes(self.vault.encrypt_bytes(payload))
            os.replace(tmp, self.enc_path)
            if self.json_path.exists():
                self.json_path.unlink()

    def migrate_to_plaintext(self) -> None:
        """Descifra registro_actas.enc hacia registro_actas.json y elimina el cifrado."""
        with self._lock:
            if not (self.vault and self.vault.is_unlocked()):
                raise RuntimeError("La bóveda debe estar desbloqueada para descifrar el registro.")
            data = []
            if self.enc_path.exists():
                plain = self.vault.decrypt_bytes(self.enc_path.read_bytes())
                raw = json.loads(plain.decode("utf-8"))
                if isinstance(raw, list):
                    data = raw
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            tmp = self.json_path.with_suffix(".tmp")
            tmp.write_bytes(payload)
            os.replace(tmp, self.json_path)
            if self.enc_path.exists():
                self.enc_path.unlink()

    def get_all(self) -> list[ActaRecord]:
        """Obtiene todos los registros ordenados del más reciente al más antiguo."""
        with self._lock:
            try:
                data = self._read_raw_list()
                records = [ActaRecord.from_dict(item) for item in data]
                records.sort(key=lambda r: r.fecha_registro, reverse=True)
                return records
            except Exception:
                return []

    def add(self, record: ActaRecord) -> None:
        """
        Agrega un nuevo registro y guarda el archivo de forma atómica.
        Usa un archivo temporal y renombrado atómico para garantizar la integridad.
        """
        with self._lock:
            try:
                data = self._read_raw_list()
            except Exception:
                data = []

            # Si ya existe un registro con el mismo hash original o con el mismo
            # (tipo_sesion, num_sesion), se actualiza silenciosamente con los nuevos datos/hashes
            norm_tipo = record.tipo_sesion.strip().lower()
            norm_num = record.num_sesion.strip().lower()
            existing_index = next(
                (
                    i for i, item in enumerate(data)
                    if (
                        item.get("sha256_original") == record.sha256_original
                        or (
                            str(item.get("tipo_sesion", "")).strip().lower() == norm_tipo
                            and str(item.get("num_sesion", "")).strip().lower() == norm_num
                            and norm_num != ""
                        )
                    )
                ),
                None,
            )

            if existing_index is not None:
                data[existing_index] = record.to_dict()
            else:
                data.insert(0, record.to_dict())

            self._write_raw_list(data)

    def find_by_sesion(self, tipo_sesion: str, num_sesion: str) -> Optional[ActaRecord]:
        """Busca un registro existente por tipo y número de sesión (case-insensitive)."""
        norm_tipo = tipo_sesion.strip().lower()
        norm_num = num_sesion.strip().lower()
        if not norm_num:
            return None
        for r in self.get_all():
            if (
                r.tipo_sesion.strip().lower() == norm_tipo
                and r.num_sesion.strip().lower() == norm_num
            ):
                return r
        return None

    def find_by_hash(self, sha256_hash: str) -> Optional[ActaRecord]:
        """Busca un registro por su hash SHA-256 (original o generado)."""
        sha_limpio = sha256_hash.strip().lower()
        records = self.get_all()
        for r in records:
            if r.sha256_original.lower() == sha_limpio:
                return r
            if r.sha256_con_hash and r.sha256_con_hash.lower() == sha_limpio:
                return r
        return None

    def search(self, query: str) -> list[ActaRecord]:
        """
        Búsqueda en tiempo real por coincidencia en cualquiera de los campos.
        """
        q = query.strip().lower()
        all_records = self.get_all()
        if not q:
            return all_records

        return [
            r for r in all_records
            if (
                q in r.tipo_sesion.lower()
                or q in r.num_sesion.lower()
                or q in r.fecha_sesion.lower()
                or q in r.nombre_archivo_original.lower()
                or q in r.nombre_archivo_con_hash.lower()
                or q in r.sha256_original.lower()
                or q in r.sha256_con_hash.lower()
                or q in r.observacion.lower()
                or q in r.fecha_registro.lower()
            )
        ]

    def export_to_csv(self, records: Optional[list[ActaRecord]] = None, output_path: Optional[Path] = None) -> Path:
        """
        Exporta los registros a un archivo CSV con codificación UTF-8-SIG para Excel.
        """
        if records is None:
            records = self.get_all()

        cfg.DIR_EXPORTACIONES.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = cfg.DIR_EXPORTACIONES / f"registro_actas_{timestamp}.csv"

        headers = [
            "ID Registro",
            "Fecha Registro",
            "Tipo Sesión",
            "N.° Sesión",
            "Fecha Sesión",
            "Observación",
            "Archivo Original",
            "Ruta Original",
            "Archivo Con Hash",
            "Ruta Con Hash",
            "Páginas",
            "SHA-256 Original",
            "SHA-256 PDF Generado",
        ]

        with output_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            for r in records:
                writer.writerow([
                    r.id,
                    r.fecha_registro,
                    r.tipo_sesion,
                    r.num_sesion,
                    r.fecha_sesion,
                    r.observacion,
                    r.nombre_archivo_original,
                    r.ruta_archivo_original,
                    r.nombre_archivo_con_hash,
                    r.ruta_archivo_con_hash,
                    r.total_paginas,
                    r.sha256_original,
                    r.sha256_con_hash,
                ])

        return output_path
