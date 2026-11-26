# Registro de Cambios (Changelog)

Todos los cambios notables de **CertiActa** se documentan en este archivo siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y [Versionado Semántico](https://semver.org/lang/es/).

## [1.2.0] - 2026-11-26

### Agregado
- **Pestaña `⚙ Ajustes`**: configuración de **Carpeta de Trabajo** personalizada (`settings.json`) con asistente para copiar o mover datos existentes (`datos/`, `01_Escaneos_Originales/`, `02_Actas_Con_Hash/`).
- **Bóveda Criptográfica Opcional (`AES-256-GCM`)**: cifrado local del registro (`registro_actas.enc`) con Contraseña Maestra, **Frase Semilla de 12 palabras en español** (copiable/guardable para imprimir) y exportación opcional de archivo llave **`.key`**.
- **Modo Dual de Acceso**: la pestaña **Auditar / Verificar** permanece siempre libre sin contraseña, mientras que las pestañas operativas se protegen cuando la bóveda está activada.
- **Protección Opcional de Edición en PDFs**: contraseña de propietario (`AES-256`) en los PDFs generados manteniendo lectura libre para legisladores y Contraloría.
- **Empaquetado Portátil Windows**: script `scripts/build_exe.py` con PyInstaller para generar `CertiActa.exe` y paquete ZIP para GitHub Releases.

## [1.1.0] - 2026-11-26

### Agregado y Mejorado
- Soporte de rutas congeladas (`sys.frozen` / `_MEIPASS`) en `src/config.py`.
- Blindaje de `pdf_stamper.py`: rechazo de PDFs encriptados o vacíos, prevención de colisiones en `02_Actas_Con_Hash/` y mensajes claros ante `PermissionError`.
- Confirmación explícita antes de sustituir una sesión existente, validación de fecha `DD/MM/AAAA`, filtro por tipo de sesión, tema sincronizado en `Treeview` y **Respaldo ZIP** en un clic.

## [1.0.0] - 2026-11-24

### Agregado
- Aplicación nativa de escritorio **CertiActa — Verificador de Actas SHA-256** (100% offline para Windows).
- **Doble Huella SHA-256**: cálculo y registro tanto del escaneo original intacto (`sha256_original`) como del PDF sellado generado (`sha256_con_hash`).
- **Pestaña Estampar y Registrar**: resguardo inmutable en `01_Escaneos_Originales/`, estampado de pie de página legible con fondo protector en `02_Actas_Con_Hash/`, cálculo asíncrono y botón **"Copiar Ficha para Libro Físico"**.
- **Pestaña Auditar / Verificar**: verificación en tiempo constante (`hmac.compare_digest`) y validación cruzada contra el registro local.
- **Pestaña Registro Local**: búsqueda en tiempo real, actualización silenciosa por sesión, exportación a CSV (`UTF-8-SIG` para Excel) y copia de ficha para Libro Físico.
- **Identidad y Documentación**: logotipo vectorial (`assets/logo.png`, `assets/icon.ico`), **Manual de Usuario institucional en PDF** (`docs/Manual_de_Usuario.pdf`), licencia **MIT** con Copyright de **José Moreno** (Secretario de Cámara CLEBDA), plantillas de GitHub e integración CI con `pytest`.
