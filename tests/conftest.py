# [SECTION: Imports]
import sys, shutil
from pathlib import Path
import pytest
from PyQt6 import QtWidgets

# [END: Imports]
ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "gui", "handlers", "resources"):
    p = ROOT / sub
    sp = str(p.resolve())
    if sp not in sys.path and p.exists():
        sys.path.append(sp)

from gui.codewijziger import Ui_CodeWijzigerWindow
from handlers.codewijziger_controller import CodeWijzigerController

DUMMY_BASE = """\
from typing import Iterable, List

def process_items(items: Iterable[int]) -> List[int]:
    base = [x * 2 for x in items]
    _ = {x: x**2 for x in base}
    __ = {x**2 for x in base}
    return [x for x in base if x % 3 != 0]

def dangerous_op(path):
    try:
        return "ok"
    finally:
        pass

"""


# [FUNC: make_multimatch_content]
def make_multimatch_content() -> str:
    return DUMMY_BASE.replace(
        "# [FUNC: process_items]", "# [FUNC: process_items]\n# variant A"
    ).replace(
        "# [END: FUNC: process_items]",
        "# [END: FUNC: process_items]\n\n# [FUNC: process_items]\n# variant B\n"
        "def process_items(items: Iterable[int]) -> List[int]:\n"
        "    return [x+1 for x in items]\n"
        "# [END: FUNC: process_items]",
    )

# [END: make_multimatch_content]

# [FUNC: tmp_target]
@pytest.fixture
def tmp_target(tmp_path: Path):
    """Maakt een tijdelijk doelbestand met de dummy-inhoud."""
    tgt = tmp_path / "dummy_target.py"
    tgt.write_text(DUMMY_BASE, encoding="utf-8")
    return tgt

# [END: tmp_target]

# [FUNC: tmp_target_multimatch]
@pytest.fixture
def tmp_target_multimatch(tmp_path: Path):
    tgt = tmp_path / "dummy_target_multi.py"
    tgt.write_text(make_multimatch_content(), encoding="utf-8")
    return tgt

# [END: tmp_target_multimatch]

# [FUNC: ui_env]
@pytest.fixture
def ui_env(qtbot, tmp_path: Path):
    """Start het Codewijziger-venster + controller."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win = QtWidgets.QMainWindow()
    ui = Ui_CodeWijzigerWindow()
    ui.setupUi(win)
    ctrl = CodeWijzigerController(
        ui, win, project_root=tmp_path, json_path=tmp_path / "projassist.json"
    )
    win.show()
    qtbot.addWidget(win)
    return ui, win, ctrl

# [END: ui_env]

# [FUNC: paste_form_and_analyse]
def paste_form_and_analyse(qtbot, ui, form_text: str):
    ui.txtFormulier.setPlainText(form_text)
    qtbot.mouseClick(ui.btnAnalyse, QtWidgets.QApplication.mouseButtons().LeftButton)
# [END: paste_form_and_analyse]
