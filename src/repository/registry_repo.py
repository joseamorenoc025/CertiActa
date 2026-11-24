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

from src.config import DIR_EXPORTACIONES, FILE_REGISTRO
from src.core.models import ActaRecord


class RegistryRepository:
    """Gestiona el almacenamiento local en JSON con soporte concurrente y atómico."""

    def __init__(self, json_path: Path = FILE_REGISTRO):
        self.json_path = Path(json_path)
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Asegura la existencia del archivo de registro."""
        if not self.json_path.parent.exists():
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.json_path.exists() or self.json_path.stat().st_size == 0:
            self.json_path.write_text("[]", encoding="utf-8")

    def get_all(self) -> list[ActaRecord]:
        """Obtiene todos los registros ordenados del más reciente al más antiguo."""
        with self._lock:
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    return []
                records = [ActaRecord.from_dict(item) for item in data]
                # Ordenar por fecha_registro descendente
                records.sort(key=lambda r: r.fecha_registro, reverse=True)
                return records
            except (json.JSONDecodeError, OSError):
                return []

    def add(self, record: ActaRecord) -> None:
        """
        Agrega un nuevo registro y guarda el archivo de forma atómica.
        Usa un archivo temporal y renombrado atómico para garantizar la integridad.
        """
        with self._lock:
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            except (json.JSONDecodeError, OSError):
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

            # Escritura atómica
            tmp_path = self.json_path.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Reemplazo atómico compatible con Windows
            os.replace(tmp_path, self.json_path)

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

        DIR_EXPORTACIONES.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = DIR_EXPORTACIONES / f"registro_actas_{timestamp}.csv"

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
