import sys
import os
from PyQt6.QtWidgets import QApplication
from gandiva.main_window import MainWindow
from gandiva.themes import get_theme, DEFAULT_THEME, make_app_stylesheet


def main():
    # Prevent system Qt theme (GTK/GNOME/KDE) from overriding gandiva's own theme.
    # These must be cleared before QApplication is constructed.
    os.environ.pop("QT_STYLE_OVERRIDE", None)
    os.environ.pop("QT_QPA_PLATFORMTHEME", None)

    app = QApplication(sys.argv)
    app.setApplicationName("gandiva")
    app.setStyle("Fusion")
    app.setStyleSheet(make_app_stylesheet(get_theme(DEFAULT_THEME)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
