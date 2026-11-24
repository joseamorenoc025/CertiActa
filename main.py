"""
Punto de entrada principal de la aplicación:
Verificador de Actas - Hash SHA-256
"""

import sys
import ctypes

def enable_windows_dpi_awareness() -> None:
    """Habilita la nitidez de fuentes en pantallas de alta resolución (DPI scaling) en Windows."""
    if sys.platform == "win32":
        try:
            # Per-monitor DPI aware (Windows 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                # System DPI aware fallback (Windows Vista+)
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main() -> None:
    enable_windows_dpi_awareness()

    from src.ui.app import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
