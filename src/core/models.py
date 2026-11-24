"""
Modelos de dominio para el registro y auditoría de actas.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import uuid


@dataclass
class ActaRecord:
    """Representa el registro inmutable de un acta procesada y sellada con hash."""
    
    id: str
    fecha_registro: str
    tipo_sesion: str
    num_sesion: str
    fecha_sesion: str
    observacion: str
    nombre_archivo_original: str
    ruta_archivo_original: str
    nombre_archivo_con_hash: str
    ruta_archivo_con_hash: str
    sha256_original: str
    total_paginas: int
    sha256_con_hash: str = ""

    @classmethod
    def create(
        cls,
        tipo_sesion: str,
        num_sesion: str,
        fecha_sesion: str,
        observacion: str,
        nombre_archivo_original: str,
        ruta_archivo_original: str,
        nombre_archivo_con_hash: str,
        ruta_archivo_con_hash: str,
        sha256_original: str,
        total_paginas: int,
        sha256_con_hash: str = "",
    ) -> "ActaRecord":
        """Factory method con generación de ID y marca de tiempo."""
        return cls(
            id=str(uuid.uuid4()),
            fecha_registro=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tipo_sesion=tipo_sesion.strip(),
            num_sesion=num_sesion.strip(),
            fecha_sesion=fecha_sesion.strip(),
            observacion=observacion.strip(),
            nombre_archivo_original=nombre_archivo_original,
            ruta_archivo_original=ruta_archivo_original,
            nombre_archivo_con_hash=nombre_archivo_con_hash,
            ruta_archivo_con_hash=ruta_archivo_con_hash,
            sha256_original=sha256_original.strip().lower(),
            total_paginas=total_paginas,
            sha256_con_hash=sha256_con_hash.strip().lower(),
        )

    def to_dict(self) -> dict:
        """Serializa a diccionario para exportar a JSON."""
        return asdict(self)

    def format_ficha_libro_fisico(self) -> str:
        """Genera un bloque de texto estructurado para asentar en el Libro Físico de Respaldo."""
        lineas = [
            "=== CERTIACTA | ASIENTO PARA LIBRO FÍSICO DE RESPALDO ===",
            f"Sesión: {self.tipo_sesion} | N.°: {self.num_sesion} | Fecha: {self.fecha_sesion}",
            f"Archivo: {self.nombre_archivo_con_hash} ({self.total_paginas} págs.)",
            f"Fecha de Registro: {self.fecha_registro}",
            f"SHA-256 Original (impreso al pie): {self.sha256_original}",
            f"SHA-256 PDF Generado: {self.sha256_con_hash or 'N/A'}",
        ]
        if self.observacion:
            lineas.append(f"Observación: {self.observacion}")
        lineas.append("=======================================================")
        return "\n".join(lineas)

    @classmethod
    def from_dict(cls, data: dict) -> "ActaRecord":
        """Deserializa desde un diccionario JSON."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            fecha_registro=data.get("fecha_registro", ""),
            tipo_sesion=data.get("tipo_sesion", ""),
            num_sesion=str(data.get("num_sesion", "")),
            fecha_sesion=data.get("fecha_sesion", ""),
            observacion=data.get("observacion", ""),
            nombre_archivo_original=data.get("nombre_archivo_original", ""),
            ruta_archivo_original=data.get("ruta_archivo_original", ""),
            nombre_archivo_con_hash=data.get("nombre_archivo_con_hash", ""),
            ruta_archivo_con_hash=data.get("ruta_archivo_con_hash", ""),
            sha256_original=data.get("sha256_original", "").lower(),
            total_paginas=int(data.get("total_paginas", 0)),
            sha256_con_hash=data.get("sha256_con_hash", "").lower(),
        )
