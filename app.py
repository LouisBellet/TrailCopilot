import os
import sys
import traceback

# 1. Neutraliser les erreurs de handshake SSL et de certificats de QtWebEngine
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--ignore-certificate-errors "
    "--disable-features=AudioServiceOutOfProcess "
    "--log-level=3"
)

# 2. Gestionnaire d'exception sécurisé (empêche la boucle "Error in sys.excepthook")
def safe_excepthook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    # Écriture forcée sur la sortie standard d'origine
    if sys.__stderr__:
        sys.__stderr__.write("\n=== ERREUR PYTHON CAPTURÉE ===\n" + error_msg + "\n")
    # Sauvegarde sur disque pour diagnostic
    try:
        with open("crash.log", "a", encoding="utf-8") as f:
            f.write("\n=== NOUVEAU CRASH ===\n" + error_msg + "\n")
    except Exception:
        pass

sys.excepthook = safe_excepthook

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Chargement de la feuille de style si elle existe
    if os.path.exists("ui/styles.qss"):
        with open("ui/styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())