import logging
import sys
from PyQt6 import QtWidgets, QtCore
try:
    from gui.MainWindow import Ui_MainWindow  # wordt gegenereerd uit .ui
except Exception:
    Ui_MainWindow = None

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log.txt", mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def main():
    try:
        logging.info("main.py gestart")
        app = QtWidgets.QApplication(sys.argv)
        win = QtWidgets.QMainWindow()
        if Ui_MainWindow is None:
            # Fallback: toon lege QMainWindow met hint
            win.setWindowTitle("PyQt app — eerst UI → PY uitvoeren in VS Code task")
        else:
            ui = Ui_MainWindow()
            ui.setupUi(win)
        win.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
        win.show()
        sys.exit(app.exec())
    except Exception:
        logging.exception("Onverwachte fout in main()")

if __name__ == "__main__":
    main()
