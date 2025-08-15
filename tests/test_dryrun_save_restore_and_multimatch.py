# [SECTION: Imports]
import logging
from pathlib import Path
from PyQt6 import QtCore, QtWidgets


# [END: Imports]
# [FUNC: _auto_close_dryrun_dialog]
def _auto_close_dryrun_dialog(qtbot):
    """Sluit de dry-run preview automatisch zodra hij opent."""
logger.debug("_auto_close_dryrun_dialog() called")

logger.debug("closer() called")
    def closer():
        for w in QtWidgets.QApplication.topLevelWidgets():
            if (
                isinstance(w, QtWidgets.QDialog)
                and "Dry-run: resultaat" in w.windowTitle()
            ):
                w.close()

    QtCore.QTimer.singleShot(300, closer)

# [END: _auto_close_dryrun_dialog]

# [FUNC: test_dryrun_save_restore]
logger.debug("test_dryrun_save_restore() called")
def test_dryrun_save_restore(qtbot, ui_env, tmp_target, tmp_path):
    ui, win, ctrl = ui_env
    form = f"""\
Bestand: {tmp_target}
Actie: REPLACE
Marker-van: # [FUNC: process_items]
Marker-tot: # [END: FUNC: process_items]
Contextregels: 2
Voorstel-blok:
def process_items(items: Iterable[int]) -> List[int]:
    # wijziging voor opslag
    return [x for x in items]
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)

    # Volledig blok toepassen eerst
    qtbot.mouseClick(
        ui.btnBlokToepassen, QtWidgets.QApplication.mouseButtons().LeftButton
    )

    # Dry-run (sluit automatisch)
    _auto_close_dryrun_dialog(qtbot)
    qtbot.mouseClick(ui.btnDryRun, QtWidgets.QApplication.mouseButtons().LeftButton)

    # Bewaar originele content
    original = Path(tmp_target).read_text(encoding="utf-8")

    # Opslaan
    qtbot.mouseClick(ui.btnOpslaan, QtWidgets.QApplication.mouseButtons().LeftButton)
    bak = Path(str(tmp_target) + ".bak")
    assert bak.exists(), "Backup ontbreekt"
    # Bestand bevat nieuwe inhoud
    saved = Path(tmp_target).read_text(encoding="utf-8")
    assert "wijziging voor opslag" in saved

    # Herstel → bestand terug naar original
    qtbot.mouseClick(ui.btnHerstel, QtWidgets.QApplication.mouseButtons().LeftButton)
    restored = Path(tmp_target).read_text(encoding="utf-8")
    assert restored == original

# [END: test_dryrun_save_restore]

logger.debug("test_multi_match_choose_second() called")
# [FUNC: test_multi_match_choose_second]
def test_multi_match_choose_second(qtbot, ui_env, tmp_target_multimatch, monkeypatch):
logger.debug("fake_get_item() called")
    ui, win, ctrl = ui_env

    # Monkeypatch: kies automatisch het 2e gevonden blok in de keuzelijst
    def fake_get_item(parent, title, label, items, current, editable):
        return items[1], True  # selecteer de tweede

    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", staticmethod(fake_get_item))

    form = f"""\
Bestand: {tmp_target_multimatch}
Actie: REPLACE
Marker-van: # [FUNC: process_items]
Marker-tot: # [END: FUNC: process_items]
Contextregels: 2
Voorstel-blok:
def process_items(items: Iterable[int]) -> List[int]:
    # voorstel dat past op variant B
    return [x+1 for x in items]
"""
    from tests.conftest import paste_form_and_analyse
logger = logging.getLogger(__name__)

    paste_form_and_analyse(qtbot, ui, form)

    # Rechter blok moet nu de variant B (tweede) context tonen
    right = ui.txtHuidig.toPlainText()
    assert "variant B" in right or "return [x+1 for x in items]" in right
# [END: test_multi_match_choose_second]
