"""
Bóveda criptográfica opcional para CertiActa.
Implementa cifrado AES-256-GCM y envoltura de llaves (Key Wrapping) con:
- Contraseña Maestra (derivada con PBKDF2-HMAC-SHA256)
- Frase Semilla de 12 palabras en español para recuperación sin pérdida de datos
- Archivo llave opcional (.key) para respaldo externo en pendrive
"""

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000
ENC_MAGIC = b"CAENC1"
VAULT_CHECK_PLAIN = b"CERTIACTA_VAULT_OK"

# Lista de 256 palabras en español claras y sin tildes ambiguas para Frase Semilla
SPANISH_WORDLIST: tuple[str, ...] = (
    "acta", "acero", "acuerdo", "agua", "aire", "aldea", "alerta", "alivio",
    "altura", "amparo", "ancla", "anillo", "apoyo", "arado", "arbol", "archivo",
    "arco", "arena", "arma", "aroma", "arte", "asiento", "astro", "atlas",
    "auditor", "aula", "aurora", "aval", "avena", "aviso", "ayuda", "azotea",
    "bahia", "balanza", "banco", "bandera", "barco", "barra", "base", "baston",
    "batalla", "baul", "bloque", "boca", "bodega", "boleto", "bolsa", "borde",
    "bosque", "boton", "brillo", "brisa", "broche", "bronce", "brujula", "bucle",
    "buque", "buzon", "cabina", "cable", "cadena", "caja", "calle", "calma",
    "camara", "cambio", "camino", "campo", "canal", "candado", "canto", "capa",
    "capital", "carbon", "carga", "cargo", "carta", "casa", "casco", "cauce",
    "cedro", "celda", "censo", "centro", "cerca", "cerro", "cesta", "ciclo",
    "cielo", "cifra", "cima", "cinta", "circulo", "cita", "ciudad", "clave",
    "clima", "codigo", "cofre", "colina", "color", "columna", "cometa", "compra",
    "concejo", "constancia", "control", "copia", "coral", "corona", "correo", "corte",
    "costa", "cresta", "cristal", "cruce", "cuadro", "cuarto", "cubierta", "cuerda",
    "cumbre", "cupula", "curso", "datos", "debate", "decreto", "defensa", "delta",
    "derecho", "despacho", "destino", "diario", "dictamen", "diente", "diploma", "disco",
    "doblez", "doctrina", "domo", "dorado", "dorsal", "duelo", "duque", "eco",
    "edificio", "editor", "eje", "ejemplo", "emblema", "enlace", "ensayo", "entrada",
    "envio", "epoca", "equipo", "escala", "escudo", "esfera", "espacio", "espejo",
    "espiga", "estado", "estante", "estrella", "estudio", "etapa", "examen", "exito",
    "faro", "fecha", "feria", "fianza", "ficha", "fiel", "figura", "fila",
    "filtro", "firma", "fisico", "flota", "flujo", "folio", "fondo", "forma",
    "foro", "fortaleza", "franja", "fuente", "fuerza", "funda", "futuro", "gaceta",
    "gala", "galeria", "garantia", "gema", "gestion", "giro", "globo", "gloria",
    "gobernador", "grado", "grafica", "grano", "grito", "grupo", "guarda", "guia",
    "hacha", "hallazgo", "harina", "haz", "hecho", "heraldo", "hierro", "hilo",
    "himno", "historia", "hito", "hoja", "honor", "hora", "horno", "huella",
    "icono", "idea", "imagen", "impulso", "indice", "informe", "ingreso", "inicio",
    "insignia", "isla", "jardin", "jefe", "jornada", "juez", "juicio", "junta",
    "jurado", "justicia", "lacre", "lado", "lago", "lamina", "lanza", "lazo",
)


def _derive_kek(secret: str, salt: bytes) -> bytes:
    """Deriva una llave de 32 bytes desde una contraseña o frase semilla usando PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(secret.encode("utf-8"))


def normalize_seed_phrase(phrase: str) -> str:
    """Normaliza espacios y mayúsculas en la frase semilla."""
    return " ".join(phrase.strip().lower().split())


def generate_seed_phrase(word_count: int = 12) -> str:
    """Genera una frase semilla criptográficamente aleatoria en español."""
    return " ".join(secrets.choice(SPANISH_WORDLIST) for _ in range(word_count))


def _wrap_dek(dek: bytes, secret: str) -> dict:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    kek = _derive_kek(secret, salt)
    ct = AESGCM(kek).encrypt(nonce, dek, None)
    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }


def _unwrap_dek(wrapped: dict, secret: str) -> bytes:
    salt = base64.b64decode(wrapped["salt"])
    nonce = base64.b64decode(wrapped["nonce"])
    ct = base64.b64decode(wrapped["ct"])
    kek = _derive_kek(secret, salt)
    return AESGCM(kek).decrypt(nonce, ct, None)


class VaultError(Exception):
    """Excepción para errores de la bóveda criptográfica."""


class VaultManager:
    """Administra el cifrado de la base de datos y la recuperación por contraseña, semilla o archivo .key."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self._dek: Optional[bytes] = None

    def set_vault_path(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)

    def is_initialized(self) -> bool:
        return self.vault_path.exists()

    def is_unlocked(self) -> bool:
        return self._dek is not None

    def lock(self) -> None:
        self._dek = None

    def _save_vault_data(self, data: dict) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.vault_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.vault_path)

    def _load_vault_data(self) -> dict:
        if not self.vault_path.exists():
            raise VaultError("La bóveda aún no ha sido inicializada.")
        return json.loads(self.vault_path.read_text(encoding="utf-8"))

    def create_vault(self, password: str) -> str:
        """
        Inicializa una nueva bóveda con Contraseña Maestra y Frase Semilla de 12 palabras.
        Retorna la frase semilla generada (debe mostrarse al usuario una sola vez).
        """
        if len(password) < 6:
            raise VaultError("La contraseña maestra debe tener al menos 6 caracteres.")

        dek = os.urandom(32)
        seed_phrase = generate_seed_phrase(12)

        check_nonce = os.urandom(12)
        check_ct = AESGCM(dek).encrypt(check_nonce, VAULT_CHECK_PLAIN, None)

        vault_data = {
            "version": 1,
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": PBKDF2_ITERATIONS,
            "wrapped_password": _wrap_dek(dek, password),
            "wrapped_seed": _wrap_dek(dek, normalize_seed_phrase(seed_phrase)),
            "key_check": {
                "nonce": base64.b64encode(check_nonce).decode("ascii"),
                "ct": base64.b64encode(check_ct).decode("ascii"),
            },
        }
        self._save_vault_data(vault_data)
        self._dek = dek
        return seed_phrase

    def unlock_with_password(self, password: str) -> bool:
        """Intenta desbloquear la bóveda con la contraseña maestra."""
        data = self._load_vault_data()
        try:
            dek = _unwrap_dek(data["wrapped_password"], password)
            self._verify_dek(data, dek)
            self._dek = dek
            return True
        except (InvalidTag, KeyError, ValueError):
            return False

    def change_password(self, current_password: str, new_password: str) -> bool:
        """Cambia la contraseña maestra verificando la actual sin re-cifrar los datos."""
        if len(new_password) < 6:
            raise VaultError("La nueva contraseña debe tener al menos 6 caracteres.")
        data = self._load_vault_data()
        try:
            dek = _unwrap_dek(data["wrapped_password"], current_password)
            self._verify_dek(data, dek)
        except (InvalidTag, KeyError, ValueError):
            return False

        data["wrapped_password"] = _wrap_dek(dek, new_password)
        self._save_vault_data(data)
        self._dek = dek
        return True

    def recover_with_seed(self, seed_phrase: str, new_password: str) -> bool:
        """Restablece la contraseña maestra usando la Frase Semilla de 12 palabras."""
        if len(new_password) < 6:
            raise VaultError("La nueva contraseña debe tener al menos 6 caracteres.")
        data = self._load_vault_data()
        try:
            dek = _unwrap_dek(data["wrapped_seed"], normalize_seed_phrase(seed_phrase))
            self._verify_dek(data, dek)
        except (InvalidTag, KeyError, ValueError):
            return False

        data["wrapped_password"] = _wrap_dek(dek, new_password)
        self._save_vault_data(data)
        self._dek = dek
        return True

    def export_key_file(self, key_path: Path) -> Path:
        """Exporta un archivo llave .key opcional para recuperación desde pendrive."""
        if not self._dek:
            raise VaultError("Debe desbloquear la bóveda antes de exportar el archivo llave.")
        out = Path(key_path)
        payload = {
            "format": "certiacta-key-v1",
            "key_b64": base64.b64encode(self._dek).decode("ascii"),
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out

    def recover_with_key_file(self, key_path: Path, new_password: str) -> bool:
        """Restablece la contraseña maestra usando un archivo llave .key."""
        if len(new_password) < 6:
            raise VaultError("La nueva contraseña debe tener al menos 6 caracteres.")
        data = self._load_vault_data()
        try:
            raw = json.loads(Path(key_path).read_text(encoding="utf-8"))
            if raw.get("format") != "certiacta-key-v1":
                return False
            dek = base64.b64decode(raw["key_b64"])
            self._verify_dek(data, dek)
        except (InvalidTag, KeyError, ValueError, OSError, json.JSONDecodeError):
            return False

        data["wrapped_password"] = _wrap_dek(dek, new_password)
        self._save_vault_data(data)
        self._dek = dek
        return True

    @staticmethod
    def _verify_dek(data: dict, dek: bytes) -> None:
        check = data["key_check"]
        nonce = base64.b64decode(check["nonce"])
        ct = base64.b64decode(check["ct"])
        plain = AESGCM(dek).decrypt(nonce, ct, None)
        if plain != VAULT_CHECK_PLAIN:
            raise InvalidTag("Verificación de llave inválida.")

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        if not self._dek:
            raise VaultError("La bóveda está bloqueada.")
        nonce = os.urandom(12)
        ct = AESGCM(self._dek).encrypt(nonce, plaintext, None)
        return ENC_MAGIC + nonce + ct

    def decrypt_bytes(self, blob: bytes) -> bytes:
        if not self._dek:
            raise VaultError("La bóveda está bloqueada.")
        if not blob.startswith(ENC_MAGIC) or len(blob) < len(ENC_MAGIC) + 12:
            raise VaultError("Formato de archivo cifrado no reconocido.")
        offset = len(ENC_MAGIC)
        nonce = blob[offset:offset + 12]
        ct = blob[offset + 12:]
        return AESGCM(self._dek).decrypt(nonce, ct, None)

    def derive_pdf_owner_password(self) -> str:
        """Deriva una contraseña fuerte de propietario para proteger PDFs contra edición."""
        if not self._dek:
            raise VaultError("La bóveda está bloqueada.")
        return hmac.new(self._dek, b"CERTIACTA_PDF_OWNER", hashlib.sha256).hexdigest()[:24]

    def remove_vault(self) -> None:
        """Elimina el archivo vault.json y bloquea la instancia (usar tras descifrar el registro)."""
        self._dek = None
        if self.vault_path.exists():
            self.vault_path.unlink()
