# [SECTION: Imports]
from pathlib import Path
from PyQt6 import QtWidgets


# [END: Imports]
# [FUNC: test_replace_happy]
def test_replace_happy(qtbot, ui_env, tmp_target):
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
    squares_map = {{}}
    __ = {{x**2 for x in base}}
    return [x for x in base if x % 3 != 0]
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)

    assert ui.lineBestand.text().endswith("dummy_target.py")
    assert "wijziging voor test" in ui.txtVoorstel.toPlainText()
    assert "# [FUNC: process_items]" in ui.txtHuidig.toPlainText()
    # hunks moeten gevuld zijn
    assert ui.listHunks.count() >= 1

# [END: test_replace_happy]

# [FUNC: test_add_happy]
def test_add_happy(qtbot, ui_env, tmp_target):
    ui, win, ctrl = ui_env
    form = f"""\
Bestand: {tmp_target}
Actie: ADD
Contextregels: 2
Voorstel-blok:
def hello_world() -> str:
    return "hello from ADD"
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)
    assert "hello from ADD" in ui.txtVoorstel.toPlainText()
    # rechts is leeg bij ADD (er is geen bestaand blok)
    assert ui.txtHuidig.toPlainText().strip() == ""

# [END: test_add_happy]

# [FUNC: test_delete_happy]
def test_delete_happy(qtbot, ui_env, tmp_target):
    ui, win, ctrl = ui_env
    form = f"""\
Bestand: {tmp_target}
Actie: DELETE
Marker-van: # [FUNC: dangerous_op]
Marker-tot: # [END: FUNC: dangerous_op]
Contextregels: 3
Voorstel-blok:
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)
    assert "# [FUNC: dangerous_op]" in ui.txtHuidig.toPlainText()
    assert ui.txtVoorstel.toPlainText().strip() == ""

# [END: test_delete_happy]

# [FUNC: test_toggles_rebuild_hunks]
def test_toggles_rebuild_hunks(qtbot, ui_env, tmp_target):
    ui, win, ctrl = ui_env
    form = f"""\
Bestand: {tmp_target}
Actie: REPLACE
Marker-van: # [FUNC: process_items]
Marker-tot: # [END: FUNC: process_items]
Contextregels: 2
Voorstel-blok:
def process_items(items: Iterable[int]) -> List[int]:
    base = [x * 2 for x in items]
    _ = {{x: x**2 for x in base}}
    __ = {{x**2 for x in base}}
    # extra regel voor diff
    return [x for x in base if x % 3 != 0]
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)
    n1 = ui.listHunks.count()
    ui.chkIgnoreWhitespace.setChecked(True)
    n2 = ui.listHunks.count()
    ui.chkIgnoreCase.setChecked(True)
    n3 = ui.listHunks.count()
    # geen crash; aantal mag veranderen of gelijk blijven
    assert n1 >= 1 and n2 >= 1 and n3 >= 1
# [END: test_toggles_rebuild_hunks]
