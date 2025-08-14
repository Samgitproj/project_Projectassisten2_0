# main.py
# [SECTION: Imports & Constants]
from __future__ import annotations
import sys
from pathlib import Path
from PyQt6 import QtCore, QtWidgets

# [END: Imports & Constants]
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Voeg pakketmappen toe (voor het geval Start_Main.bat met andere CWD runt)
for sub in ("handlers", "services", "gui", "resources"):
    p = ROOT / sub
    if p.is_dir():
        sp = str(p.resolve())
        if sp not in sys.path:
            sys.path.append(sp)

from ProjAssist import Ui_Dialog
from handlers.projassist_handlers import ProjAssistHandlers


# [FUNC: _enable_high_dpi_safe]
def _enable_high_dpi_safe():
    """Zet High‑DPI opties aan als je Qt build ze ondersteunt."""
    # Sommige PyQt6 builds hebben deze niet meer nodig/beschikbaar.
    try:
        attr = getattr(QtCore.Qt.ApplicationAttribute, "AA_EnableHighDpiScaling", None)
        if attr is not None:
            QtWidgets.QApplication.setAttribute(attr, True)
    except Exception:
        pass
    try:
        attr = getattr(QtCore.Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps", None)
        if attr is not None:
            QtWidgets.QApplication.setAttribute(attr, True)
    except Exception:
        pass

# [END: _enable_high_dpi_safe]

# [FUNC: main]
def main() -> int:
    _enable_high_dpi_safe()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Projectassisten2_0")
    app.setOrganizationName("Vioprint")

    # Hoofdvenster
    dlg = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(dlg)

    # Handlers koppelen (referentie bewaren)
    handlers = ProjAssistHandlers(ui, parent=dlg)  # noqa: F841

    # Eventueel starttab (Scripts & JSON is index 1)
    try:
        ui.tabMain.setCurrentIndex(1)
    except Exception:
        pass

    dlg.show()
    return app.exec()

# [END: main]

# [SECTION: CLI / Entrypoint]
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as ex:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        QtWidgets.QMessageBox.critical(None, "Startfout", str(ex))
        raise
# [END: CLI / Entrypoint]
