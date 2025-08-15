# [SECTION: Imports]
from PyQt6 import QtWidgets


# [END: Imports]
# [FUNC: test_sync_scroll]
def test_sync_scroll(qtbot, ui_env, tmp_target):
    ui, win, ctrl = ui_env
    # Maak een lang voorstel zodat scrollbalken ontstaan
    long_left = (
        "# [FUNC: process_items]\n"
        + "\n".join(f"line {i}" for i in range(200))
        + "\n# [END: FUNC: process_items]\n"
    )
    form = f"""\
Bestand: {tmp_target}
Actie: REPLACE
Marker-van: # [FUNC: process_items]
Marker-tot: # [END: FUNC: process_items]
Contextregels: 1
Voorstel-blok:
{long_left}
"""
    from tests.conftest import paste_form_and_analyse

    paste_form_and_analyse(qtbot, ui, form)

    lbar = ui.txtVoorstel.verticalScrollBar()
    rbar = ui.txtHuidig.verticalScrollBar()

    # 1) Scroll links halfweg → rechts moet proportioneel volgen
    lbar.setValue(int(lbar.maximum() * 0.5))
    QtWidgets.QApplication.processEvents()
    qtbot.wait(150)

    if lbar.maximum() > 0 and rbar.maximum() > 0:
        lr = lbar.value() / lbar.maximum()
        rr = rbar.value() / rbar.maximum()
        assert abs(lr - rr) <= 0.05
    else:
        assert rbar.maximum() == 0 or lbar.maximum() == 0

    # 2) Scroll rechts naar top → links moet proportioneel mee naar (bijna) top
    rbar.setValue(0)
    QtWidgets.QApplication.processEvents()
    qtbot.wait(150)

    if lbar.maximum() > 0 and rbar.maximum() > 0:
        lr = lbar.value() / lbar.maximum()
        rr = rbar.value() / rbar.maximum()  # = 0 bij top
        assert rr <= 0.01 and abs(lr - rr) <= 0.05
    else:
        assert rbar.maximum() == 0 or lbar.maximum() == 0
# [END: test_sync_scroll]
