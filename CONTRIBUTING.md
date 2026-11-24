# Guía de Contribución a CertiActa

¡Gracias por tu interés en contribuir a **CertiActa**! Este proyecto nació para modernizar y asegurar la integridad documental de las actas legislativas y municipales mediante verificación criptográfica offline (SHA-256).

## Cómo Contribuir

1. Haz un **Fork** del repositorio y crea una rama descriptiva (`git checkout -b feature/mejora-ejemplo`).
2. Mantén la separación de responsabilidades de la arquitectura (`src/core/`, `src/repository/`, `src/ui/`).
3. Asegúrate de preservar siempre la **regla fundamental de inmutabilidad**: el PDF escaneado original nunca debe ser alterado.
4. Ejecuta todas las pruebas automatizadas antes de enviar tu Pull Request:
   ```powershell
   python -m pytest tests/ -v
   ```
5. Si modificas documentación o flujos de usuario, recuerda regenerar el manual PDF con:
   ```powershell
   python scripts/build_manual_pdf.py
   ```
6. Envía un **Pull Request** explicando claramente el problema resuelto y los cambios realizados.
