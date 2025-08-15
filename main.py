# main.py
# [SECTION: Imports]
from __future__ import annotations

import sys
from pathlib import Path
from PyQt6 import QtCore, QtWidgets

# [END: Imports]
# Zorg dat projectpaden in sys.path staan (voor import van gui/ en handlers/)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for sub in ("handlers", "services", "gui", "resources"):
    p = ROOT / sub
    if p.is_dir():
        sp = str(p.resolve())
        if sp not in sys.path:
            sys.path.append(sp)

from ProjAssist import Ui_Dialog
from handlers.projassist_handlers import ProjAssistHandlers


# [FUNC: _enable_high_dpi_safe]
def _enable_high_dpi_safe() -> None:
    """Veilige High-DPI instellingen (alleen als attribuut bestaat)."""
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

# [FUNC: open_code_changer]
def open_code_changer(
    parent_dialog: QtWidgets.QDialog, handlers: object | None = None
) -> None:
    """
    Opent de Codewijziger-GUI en koppelt de controller,
    zodat tab 'Formulier' meteen werkt.
    """
    # Lazy imports om start-up licht te houden
    from gui.codewijziger import Ui_CodeWijzigerWindow
    from handlers.codewijziger_controller import CodeWijzigerController

    win = QtWidgets.QMainWindow(parent_dialog)
    ui_cw = Ui_CodeWijzigerWindow()
    ui_cw.setupUi(win)

    # Controller 'aanzetten' (koppelstuk UI ↔ logica)
    ctrl = CodeWijzigerController(
        ui_cw,
        win,
        project_root=getattr(handlers, "project_root", None),
        json_path=getattr(handlers, "json_path", None),
    )

    # Referenties bewaren zodat venster/ctrl niet door GC gesloten worden
    parent_dialog._codewijziger_win = win
    parent_dialog._codewijziger_ui = ui_cw
    parent_dialog._codewijziger_ctrl = ctrl

    win.show()
    win.raise_()
    win.activateWindow()

# [END: open_code_changer]

# [FUNC: main]
def main() -> int:
    _enable_high_dpi_safe()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Projectassisten2_0")
    app.setOrganizationName("Vioprint")

    # Hoofd-UI (QDialog zoals in jouw ProjAssist.ui → Ui_Dialog)
    dlg = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(dlg)

    # Handlers van jouw hoofdapp
    handlers = ProjAssistHandlers(ui, parent=dlg)  # bewaart o.a. project_root/json_path

    # Koppeling voor Codewijziger-knop (ondersteun beide namen)
    btn = getattr(ui, "btnOpenCodeChanger", None) or getattr(ui, "btnCodeChanger", None)
    if btn is not None:
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        btn.clicked.connect(lambda: open_code_changer(dlg, handlers))

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
