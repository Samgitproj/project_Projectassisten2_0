# [SECTION: Imports]
import logging
from PyQt6 import QtWidgets, QtCore


# [END: Imports]
# [FUNC: _uncheck_all_hunks]
def _uncheck_all_hunks(ui):
logger.debug("_uncheck_all_hunks() called")
    for i in range(ui.listHunks.count()):
        it = ui.listHunks.item(i)
        it.setCheckState(QtCore.Qt.CheckState.Unchecked)

# [END: _uncheck_all_hunks]

# [FUNC: _check_all_hunks]
logger.debug("_check_all_hunks() called")
def _check_all_hunks(ui):
    for i in range(ui.listHunks.count()):
        it = ui.listHunks.item(i)
        it.setCheckState(QtCore.Qt.CheckState.Checked)

# [END: _check_all_hunks]

logger.debug("test_apply_selected_and_block() called")
# [FUNC: test_apply_selected_and_block]
def test_apply_selected_and_block(qtbot, ui_env, tmp_target):
    ui, win, ctrl = ui_env
    form = f"""\
Bestand: {tmp_target}
Actie: REPLACE
Marker-van: # [FUNC: process_items]
Marker-tot: # [END: FUNC: process_items]
Contextregels: 2
Voorstel-blok:
def process_items(items: Iterable[int]) -> List[int]:
    # wijziging voor test
    base = [x * 2 for x in items]
    _ = {{x: x**2 for x in base}}
    __ = {{x**2 for x in base}}
    return [x for x in base if x % 3 != 0]
"""
    from tests.conftest import paste_form_and_analyse
logger = logging.getLogger(__name__)

    paste_form_and_analyse(qtbot, ui, form)

    original_right = ui.txtHuidig.toPlainText()

    # Geselecteerd toepassen met GEEN hunks geselecteerd → rechts blijft gelijk
    _uncheck_all_hunks(ui)
    qtbot.mouseClick(
        ui.btnGeselecteerdToepassen, QtWidgets.QApplication.mouseButtons().LeftButton
    )
    assert ui.txtHuidig.toPlainText() == original_right

    # Geselecteerd toepassen met ALLES geselecteerd → rechts wordt gelijk aan links (op blokniveau)
    _check_all_hunks(ui)
    qtbot.mouseClick(
        ui.btnGeselecteerdToepassen, QtWidgets.QApplication.mouseButtons().LeftButton
    )
    after_selected = ui.txtHuidig.toPlainText()
    assert "# [FUNC: process_items]" in after_selected
    assert "wijziging voor test" in after_selected

    # Blok toepassen → rechts exact links
    qtbot.mouseClick(
        ui.btnBlokToepassen, QtWidgets.QApplication.mouseButtons().LeftButton
    )
    assert ui.txtHuidig.toPlainText().strip() == ui.txtVoorstel.toPlainText().strip()
# [END: test_apply_selected_and_block]
