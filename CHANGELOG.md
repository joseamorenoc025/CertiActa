# Registro de Cambios (Changelog)

Todos los cambios notables de **CertiActa** se documentan en este archivo siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-24

### Agregado
- Aplicación nativa de escritorio **CertiActa — Verificador de Actas SHA-256** (100% offline para Windows).
- **Doble Huella SHA-256**: cálculo y registro tanto del escaneo original intacto (`sha256_original`) como del PDF sellado generado (`sha256_con_hash`).
- **Pestaña Estampar y Registrar**: resguardo inmutable en `01_Escaneos_Originales/`, estampado de pie de página legible con fondo protector en `02_Actas_Con_Hash/`, cálculo asíncrono y botón **"Copiar Ficha para Libro Físico"**.
- **Pestaña Auditar / Verificar**: verificación en tiempo constante (`hmac.compare_digest`) y validación cruzada contra el registro local.
- **Pestaña Registro Local**: búsqueda en tiempo real, actualización silenciosa por sesión, exportación a CSV (`UTF-8-SIG` para Excel) y copia de ficha para Libro Físico.
- **Identidad y Documentación**: logotipo vectorial (`assets/logo.png`, `assets/icon.ico`), **Manual de Usuario institucional en PDF** (`docs/Manual_de_Usuario.pdf`), licencia **MIT** con Copyright de **José Moreno** (Secretario de Cámara CLEBDA), plantillas de GitHub e integración CI con `pytest`.
