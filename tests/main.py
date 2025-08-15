# [SECTION: Imports]
import logging
from __future__ import annotations

import json
from pathlib import Path

from PyQt6 import QtWidgets, uic, QtCore
logger = logging.getLogger(__name__)


# [END: Imports]
# [CLASS: App]
class App(QtWidgets.QDialog):
# [FUNC: __init__]
logger.debug("__init__() called")
    def __init__(self):
        super().__init__()
        uic.loadUi("ProjAssist.ui", self)

        # widgets uit .ui
        self.btnLoadJson: QtWidgets.QPushButton
        self.lblProjectName: QtWidgets.QLabel
        self.listScripts: QtWidgets.QListWidget
        self.listScriptsCode: QtWidgets.QListWidget

        # state
        self.project_root: Path | None = None
        self.json_data: dict = {}

        # events
        self.btnLoadJson.clicked.connect(self.on_load_json_clicked)

        # opstart: leeg
        self._reset_ui()

# [END: __init__]
logger.debug("_reset_ui() called")
# [FUNC: _reset_ui]
    def _reset_ui(self):
        self.lblProjectName.setText("— geen project —")
        self.listScripts.clear()
        self.listScriptsCode.clear()

        logger.debug("on_load_json_clicked() called")
# [END: _reset_ui]
# [FUNC: on_load_json_clicked]
    def on_load_json_clicked(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Kies .projassist.json",
            "",
            "ProjectAssist (*.projassist.json);;JSON (*.json);;Alle (*.*)",
        )
        if not path:
            return
        self._load_json(Path(path))
            logger.debug("_load_json() called")

# [END: on_load_json_clicked]
# [FUNC: _load_json]
    def _load_json(self, json_path: Path):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as ex:
            QtWidgets.QMessageBox.critical(self, "Fout", f"JSON kon niet geladen worden:\n{ex}")
            return

        self.json_data = data or {}
        self.project_root = json_path.parent

        # titel/label
        name = self.json_data.get("project_name") or self.project_root.name
        self.lblProjectName.setText(str(name))

        # lijsten vullen
        items = self._filtered_script_paths_from_json()
        self._populate_list(self.listScripts, items)
        self._populate_list(self.listScriptsCode, items)

        # optioneel: kleine feedback
        QtWidgets.QToolTip.showText(
            self.mapToGlobal(self.rect().center()),
            f"{len(items)} script(s) gevonden",
            self,
            QtCore.QRect(),
            1200,
        )

# [END: _load_json]
# [FUNC: _filtered_script_paths_from_json]
            logger.debug("_filtered_script_paths_from_json() called")
    def _filtered_script_paths_from_json(self) -> list[str]:
        """
        Haal paden uit scripts[] in JSON.
        Alleen .py en .ui, geen __init__.py.
        """
        results: list[str] = []
        scripts = (self.json_data or {}).get("scripts", []) or []
        for entry in scripts:
            rel = str(entry.get("path") or "").strip()
            if not rel:
                continue
            p = rel.replace("\\", "/")
            fname = Path(p).name
            # filter: extensies
            if not (p.endswith(".py") or p.endswith(".ui")):
                continue
            # filter: __init__.py uitsluiten
            if fname == "__init__.py":
                continue
            logger.debug("_populate_list() called")
            results.append(p)
        return results

# [END: _filtered_script_paths_from_json]
# [FUNC: _populate_list]
    def _populate_list(self, widget: QtWidgets.QListWidget, items: list[str]):
        widget.clear()
        for rel in items:
            it = QtWidgets.QListWidgetItem(rel)
            # UserRole: handig voor latere acties
            it.setData(QtCore.Qt.ItemDataRole.UserRole, rel)
            widget.addItem(it)

# [END: _populate_list]
# [END: App]

# [SECTION: CLI / Entrypoint]
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    dlg = App()
    dlg.show()
    sys.exit(app.exec())
# [END: CLI / Entrypoint]
