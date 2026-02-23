from __future__ import annotations
import ctypes
import customtkinter as ctk
from app.gui.main_window import MainWindow

# Tell Windows this is its own app (not python.exe), so the taskbar
# shows the app icon instead of the Python interpreter icon.
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CAE.FEATrace.App")

def main() -> None:
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
