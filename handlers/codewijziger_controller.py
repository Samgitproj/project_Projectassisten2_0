# handlers/codewijziger_controller.py

# [SECTION: Imports]
from __future__ import annotations

import os
import re
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6 import QtCore, QtWidgets

import subprocess
from datetime import datetime



# [END: Imports]
# [CLASS: FormState]
@dataclass
class FormState:
    bestand: Path = Path()
    actie: str = ""  # "ADD" | "REPLACE" | "DELETE"
    marker_van: str = ""
    marker_tot: str = ""
    contextregels: int = 3
    blok_id: Optional[str] = None
    korte_reden: Optional[str] = None

    voorstel_blok: str = ""  # links (volledige tekst incl. markers)
    huidig_blok: str = ""  # rechts (gevonden in bestand, incl. context)
    huidig_blok_range: Tuple[int, int] = (-1, -1)  # (start_idx, end_idx) in file lines

    file_lines: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# [END: FormState]

# hunk-model voor tab Wijzigingen
# [CLASS: Hunk]
@dataclass
class Hunk:
    tag: str  # 'replace' | 'delete' | 'insert' | 'equal'
    r1: int  # indexbereik in rechts (huidig)
    r2: int
    l1: int  # indexbereik in links (voorstel)
    l2: int
    n_add: int  # aantal toegevoegde regels (links)
    n_del: int  # aantal verwijderde regels (rechts)
    preview: str  # 1 regel preview

# [END: Hunk]



_FORM_LABELS = {
    "bestand": r"^\s*Bestand\s*:\s*(?P<val>.+?)\s*$",
    "actie": r"^\s*Actie\s*:\s*(?P<val>ADD|REPLACE|DELETE)\s*$",
    "marker_van": r"^\s*Marker[\-–]van\s*:\s*(?P<val>.+?)\s*$",
    "marker_tot": r"^\s*Marker[\-–]tot\s*:\s*(?P<val>.+?)\s*$",
    "context": r"^\s*Contextregels\s*:\s*(?P<val>.+?)\s*$",
    "blok_id": r"^\s*Blok[\-–_]ID\s*:\s*(?P<val>.+?)\s*$",
    "reden": r"^\s*Korte\s+reden\s*:\s*(?P<val>.+?)\s*$",
    "voorstel_header": r"^\s*Voorstel[\-– ]blok\s*:\s*$",
}
_CODE_FENCE = re.compile(r"^\s*```+")


# [FUNC: _expand_path]
def _expand_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    p = os.path.expandvars(os.path.expanduser(p))
    return Path(p)

# [END: _expand_path]

# [FUNC: parse_wijzigformulier]
def parse_wijzigformulier(text: str) -> FormState:
    """
    Parse het standaard wijzigformulier.
    - Herkent labels (Bestand, Actie, Marker-van, Marker-tot, Contextregels, Blok-ID, Korte reden, Voorstel-blok).
    - Alles na 'Voorstel-blok:' is het voorstel; code fences ``` worden genegeerd.
    """
    lines = text.splitlines()
    st = FormState()

    # Kop uitlezen tot aan 'Voorstel-blok:'
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(_FORM_LABELS["voorstel_header"], line, flags=re.IGNORECASE):
            i += 1
            break
        for key, pat in _FORM_LABELS.items():
            if key == "voorstel_header":
                continue
            m = re.match(pat, line, flags=re.IGNORECASE)
            if not m:
                continue
            val = m.group("val").strip()
            if key == "bestand":
                st.bestand = _expand_path(val)
            elif key == "actie":
                st.actie = val.upper()
            elif key == "marker_van":
                st.marker_van = val
            elif key == "marker_tot":
                st.marker_tot = val
            elif key == "context":
                try:
                    st.contextregels = max(0, int(val))
                except ValueError:
                    st.errors.append("Contextregels is geen getal.")
            elif key == "blok_id":
                st.blok_id = val
            elif key == "reden":
                st.korte_reden = val
        i += 1

    # Voorstel-blok lezen (alles na header), strip optionele codefences
    voorstel_lines: List[str] = []
    if i < len(lines) and _CODE_FENCE.match(lines[i]):
        i += 1
    while i < len(lines):
        if _CODE_FENCE.match(lines[i]):  # sluitende fence
            i += 1
            break
        voorstel_lines.append(lines[i])
        i += 1
    st.voorstel_blok = "\n".join(voorstel_lines).rstrip("\n")

    # Validaties
    if not st.bestand:
        st.errors.append("Bestand: ontbreekt.")
    if not st.actie:
        st.errors.append("Actie: ontbreekt of ongeldig (ADD|REPLACE|DELETE).")
    if st.actie in ("REPLACE", "DELETE"):
        if not st.marker_van or not st.marker_tot:
            st.errors.append(
                "Markers: Marker-van en Marker-tot zijn verplicht voor REPLACE/DELETE."
            )
    if st.actie == "ADD":
        if not st.voorstel_blok.strip():
            st.errors.append("Voorstel-blok ontbreekt voor ADD.")
    return st

# [END: parse_wijzigformulier]



# [FUNC: _read_file_lines]
def _read_file_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)

# [END: _read_file_lines]

# [FUNC: _find_marker_range]
def _find_marker_range(
    lines: List[str], start_marker: str, end_marker: str
) -> Tuple[int, int]:
    """Vind eerste match [start,end] (incl.). Retour (-1,-1) als niet gevonden."""
    start_idx = end_idx = -1
    sm = start_marker.strip()
    em = end_marker.strip()
    for idx, raw in enumerate(lines):
        if raw.rstrip("\r\n") == sm:
            start_idx = idx
            break
    if start_idx == -1:
        return (-1, -1)
    for idx in range(start_idx, len(lines)):
        if lines[idx].rstrip("\r\n") == em:
            end_idx = idx
            break
    return (start_idx, end_idx)

# [END: _find_marker_range]

# [FUNC: _find_all_marker_ranges]
def _find_all_marker_ranges(
    lines: List[str], start_marker: str, end_marker: str
) -> List[Tuple[int, int]]:
    """Vind alle opeenvolgende [start,end]-paren die bij elkaar horen."""
    sm = start_marker.strip()
    em = end_marker.strip()
    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == sm]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == em]
    ranges: List[Tuple[int, int]] = []
    ei = 0
    for si in starts:
        while ei < len(ends) and ends[ei] < si:
            ei += 1
        if ei < len(ends):
            ranges.append((si, ends[ei]))
            ei += 1
    return ranges

# [END: _find_all_marker_ranges]



# [FUNC: _norm_line]
def _norm_line(s: str, ignore_ws: bool, ignore_case: bool) -> str:
    if ignore_ws:
        s = s.replace("\t", "    ")
        s = re.sub(r"\s+", " ", s).rstrip()
    if ignore_case:
        s = s.lower()
    return s

# [END: _norm_line]

# [FUNC: _build_hunks_and_opcodes]
def _build_hunks_and_opcodes(
    right_text: str,
    left_text: str,
    ignore_ws: bool,
    ignore_case: bool,
) -> Tuple[List[Hunk], List[Tuple[str, int, int, int, int]]]:
    """Bouw non-equal hunks + bewaar alle opcodes voor selectief toepassen."""
    right_lines = right_text.splitlines(keepends=True)
    left_lines = left_text.splitlines(keepends=True)
    right_norm = [_norm_line(x, ignore_ws, ignore_case) for x in right_lines]
    left_norm = [_norm_line(x, ignore_ws, ignore_case) for x in left_lines]

    sm = difflib.SequenceMatcher(a=right_norm, b=left_norm)
    opcodes = sm.get_opcodes()

    hunks: List[Hunk] = []
    for tag, r1, r2, l1, l2 in opcodes:
        if tag == "equal":
            continue
        n_del = r2 - r1
        n_add = l2 - l1
        preview = ""
        for ln in left_lines[l1:l2]:
            if ln.strip():
                preview = ln.strip()
                break
        if not preview:
            for rn in right_lines[r1:r2]:
                if rn.strip():
                    preview = rn.strip()
                    break
        hunks.append(
            Hunk(
                tag=tag,
                r1=r1,
                r2=r2,
                l1=l1,
                l2=l2,
                n_add=n_add,
                n_del=n_del,
                preview=preview,
            )
        )
    return hunks, opcodes

# [END: _build_hunks_and_opcodes]

# [FUNC: _extract_block_only]
def _extract_block_only(text: str, marker_van: str, marker_tot: str) -> List[str]:
    """Haal alleen het blok (incl. markers) uit een context-bundel."""
    lines = text.splitlines(keepends=True)
    mv = marker_van.strip()
    mt = marker_tot.strip()
    s = e = -1
    for i, ln in enumerate(lines):
        if ln.rstrip("\r\n") == mv:
            s = i
            break
    if s == -1:
        return []
    for j in range(s, len(lines)):
        if lines[j].rstrip("\r\n") == mt:
            e = j
            break
    if e == -1:
        return []
    return lines[s : e + 1]

# [END: _extract_block_only]

# [FUNC: _ensure_trailing_nl]
def _ensure_trailing_nl(lines: List[str]) -> List[str]:
    if not lines:
        return lines
    if not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"
    return lines

# [END: _ensure_trailing_nl]



# [FUNC: _run_git]
def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, shell=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

# [END: _run_git]

# [FUNC: _git_is_repo]
def _git_is_repo(cwd: Path) -> bool:
    rc, out, _ = _run_git(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return rc == 0 and (out.lower() == "true")

# [END: _git_is_repo]

# [FUNC: _git_after_save]
def _git_after_save(cwd: Path, target: Path, msg: str, parent) -> None:
    # alleen het gewijzigde bestand committen
    try:
        rel = target.resolve().relative_to(cwd.resolve())
    except Exception:
        rel = target.name

    rc, _, err = _run_git(["git", "add", str(rel)], cwd)
    if rc != 0:
        QtWidgets.QMessageBox.information(parent, "Git", f"git add faalde:\n{err}")
        return

    rc, _, err = _run_git(["git", "commit", "-m", msg], cwd)
    if rc != 0:
        # vaak: nothing to commit
        QtWidgets.QMessageBox.information(
            parent, "Git", f"git commit:\n{err or 'niets te committen'}"
        )
        return

    rc, out, err = _run_git(["git", "push"], cwd)
    if rc == 0:
        QtWidgets.QMessageBox.information(
            parent, "Git", "Wijzigingen gecommit en gepusht."
        )
    else:
        QtWidgets.QMessageBox.information(
            parent, "Git", f"git push faalde:\n{err or out}"
        )

# [END: _git_after_save]



# [CLASS: CodeWijzigerController]
class CodeWijzigerController:
    """
    Controller voor Codewijziger-UI.
    - Tab 'Formulier': laden, parsen, velden invullen, links/rechts klaarmaken.
    - Tab 'Wijzigingen': hunks tonen, selectief of volledig toepassen, dry-run, opslaan/herstel.
    """

# [FUNC: __init__]
    def __init__(
        self,
        ui: Any,
        window: QtWidgets.QMainWindow,
        project_root: Optional[Path] = None,
        json_path: Optional[Path] = None,
    ) -> None:
        self.ui = ui
        self.window = window
        self.project_root = Path(project_root) if project_root else None
        self.json_path = Path(json_path) if json_path else None
        self.state = FormState()
        self._hunks: List[Hunk] = []
        self._opcodes: List[Tuple[str, int, int, int, int]] = []
        self._syncing_scroll = False

        self._connect_signals()
        self._init_defaults()
        self._setup_sync_scroll()

# [END: __init__]

# [FUNC: _init_defaults]
    def _init_defaults(self) -> None:
        try:
            self.ui.spinContext.setValue(3)
        except Exception:
            pass
        try:
            if self.json_path and hasattr(self.ui, "lineJsonPath"):
                self.ui.lineJsonPath.setText(str(self.json_path))
        except Exception:
            pass
        for name, val in (
            ("chkIgnoreWhitespace", False),
            ("chkIgnoreCase", False),
            ("chkHideIdentical", False),
        ):
            try:
                cb = getattr(self.ui, name, None)
                if cb is not None:
                    cb.setChecked(val)
            except Exception:
                pass

# [END: _init_defaults]

# [FUNC: _setup_sync_scroll]
    def _setup_sync_scroll(self) -> None:
        """Optioneel: gesynchroniseerd scrollen tussen links/rechts."""
        left = getattr(self.ui, "txtVoorstel", None)
        right = getattr(self.ui, "txtHuidig", None)
        if not left or not right:
            return
        try:
            lbar = left.verticalScrollBar()
            rbar = right.verticalScrollBar()
            lbar.valueChanged.connect(lambda v: self._sync_scrollbars("L2R", v))
            rbar.valueChanged.connect(lambda v: self._sync_scrollbars("R2L", v))
        except Exception:
            pass

# [END: _setup_sync_scroll]
# [FUNC: _sync_scrollbars]
    def _sync_scrollbars(self, direction: str, value: int) -> None:
        if self._syncing_scroll:
            return
        left = getattr(self.ui, "txtVoorstel", None)
        right = getattr(self.ui, "txtHuidig", None)
        if not left or not right:
            return
        try:
            self._syncing_scroll = True
            src = left if direction == "L2R" else right
            dst = right if direction == "L2R" else left
            sbar = src.verticalScrollBar()
            dbar = dst.verticalScrollBar()
            smax = sbar.maximum()
            dmax = dbar.maximum()
            if smax <= 0 or dmax < 0:
                dbar.setValue(0)
            else:
                ratio = value / smax
                dbar.setValue(int(round(ratio * dmax)))
        finally:
            self._syncing_scroll = False

# [END: _sync_scrollbars]

# [FUNC: _connect_signals]
    def _connect_signals(self) -> None:
        # Formulier
        if hasattr(self.ui, "btnLoadForm"):
            self.ui.btnLoadForm.clicked.connect(self._on_load_form)
        if hasattr(self.ui, "btnAnalyse"):
            self.ui.btnAnalyse.clicked.connect(self._on_analyse_form)
        # Wijzigingen – toggles
        for name in ("chkIgnoreWhitespace", "chkIgnoreCase", "chkHideIdentical"):
            cb = getattr(self.ui, name, None)
            if cb is not None:
                cb.stateChanged.connect(self._rebuild_hunks)
        # Wijzigingen – acties
        btn = getattr(self.ui, "btnGeselecteerdToepassen", None)
        if btn is not None:
            btn.clicked.connect(lambda: self._apply_hunks(selected_only=True))
        btn = getattr(self.ui, "btnBlokToepassen", None)
        if btn is not None:
            btn.clicked.connect(lambda: self._apply_hunks(selected_only=False))
        btn = getattr(self.ui, "btnDryRun", None)
        if btn is not None:
            btn.clicked.connect(self._on_dry_run)
        btn = getattr(self.ui, "btnOpslaan", None)
        if btn is not None:
            btn.clicked.connect(self._on_save)
        btn = getattr(self.ui, "btnHerstel", None)
        if btn is not None:
            btn.clicked.connect(self._on_restore)

# [END: _connect_signals]

# [FUNC: _set_status]
    def _set_status(self, msg: str) -> None:
        sb = getattr(self.ui, "statusbar", None) or getattr(
            self.window, "statusbar", None
        )
        try:
            if sb:
                sb.showMessage(msg, 5000)
        except Exception:
            pass

# [END: _set_status]
# [FUNC: _error_box]
    def _error_box(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.critical(self.window, title, text)

# [END: _error_box]
# [FUNC: _info_box]
    def _info_box(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.information(self.window, title, text)

# [END: _info_box]
# [FUNC: _on_load_form]
    def _on_load_form(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Kies wijzigformulier",
            str(self.project_root or Path.home()),
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not fn:
            return
        try:
            content = Path(fn).read_text(encoding="utf-8")
        except Exception as ex:
            self._error_box("Lezen mislukt", f"Kon bestand niet lezen:\n{ex}")
            return
        if hasattr(self.ui, "txtFormulier"):
            self.ui.txtFormulier.setPlainText(content)
        self._set_status("Formulier geladen.")

# [END: _on_load_form]
# [FUNC: _pick_marker_range_if_needed]
    def _pick_marker_range_if_needed(
        self, lines: List[str], st: FormState
    ) -> Tuple[int, int]:
        """Kies blok als meerdere matches. Retourneer (start,end) of (-1,-1)."""
        ranges = _find_all_marker_ranges(lines, st.marker_van, st.marker_tot)
        if not ranges:
            return (-1, -1)
        if len(ranges) == 1:
            return ranges[0]
        # Meerdere matches → dialoog
        items = []
        for a, b in ranges:
            preview = lines[a].rstrip("\r\n")
            items.append(f"Regels {a+1}-{b+1}: {preview}")
        choice, ok = QtWidgets.QInputDialog.getItem(
            self.window, "Meerdere blokken gevonden", "Kies blok:", items, 0, False
        )
        if not ok:
            return (-1, -1)
        idx = items.index(choice)
        return ranges[idx]

# [END: _pick_marker_range_if_needed]
# [FUNC: _on_analyse_form]
    def _on_analyse_form(self) -> None:
        """Parseer formulier, vul velden, lees doelbestand, prepareer panelen en hunks."""
        text = (
            self.ui.txtFormulier.toPlainText()
            if hasattr(self.ui, "txtFormulier")
            else ""
        )
        st = parse_wijzigformulier(text)
        try:
            st.contextregels = int(self.ui.spinContext.value())
        except Exception:
            pass

        errs: List[str] = []
        errs.extend(st.errors)
        if st.bestand and not st.bestand.exists():
            errs.append(f"Bestand bestaat niet: {st.bestand}")
        if st.actie not in ("ADD", "REPLACE", "DELETE"):
            errs.append("Actie moet ADD, REPLACE of DELETE zijn.")
        if errs:
            self._error_box("Formulier onvolledig", "\n".join(errs))
            return

        # UI velden invullen
        try:
            self.ui.lineBestand.setText(str(st.bestand))
        except Exception:
            pass
        try:
            idx = self.ui.comboActie.findText(st.actie)
            if idx >= 0:
                self.ui.comboActie.setCurrentIndex(idx)
        except Exception:
            pass
        try:
            self.ui.lineMarkerVan.setText(st.marker_van)
            self.ui.lineMarkerTot.setText(st.marker_tot)
        except Exception:
            pass

        # Doelbestand lezen & huidig blok vinden
        right_block = ""
        right_range = (-1, -1)
        file_lines: List[str] = []
        if st.bestand.exists():
            try:
                file_lines = _read_file_lines(st.bestand)
            except Exception as ex:
                self._error_box("Lezen mislukt", f"Kon doelbestand niet lezen:\n{ex}")
                return

            if st.actie in ("REPLACE", "DELETE"):
                start_idx, end_idx = self._pick_marker_range_if_needed(file_lines, st)
                if start_idx == -1 or end_idx == -1:
                    self._error_box(
                        "Markers niet gevonden",
                        "Kon het blok tussen Marker-van en Marker-tot niet vinden in het doelbestand.",
                    )
                else:
                    ctx = max(0, st.contextregels)
                    a = max(0, start_idx - ctx)
                    b = min(len(file_lines), end_idx + 1 + ctx)
                    right_block = "".join(file_lines[a:b])
                    right_range = (start_idx, end_idx)

        # State bijwerken
        st.file_lines = file_lines
        st.huidig_blok = right_block
        st.huidig_blok_range = right_range
        self.state = st

        # Linker/rechter panelen vullen
        if hasattr(self.ui, "txtVoorstel"):
            self.ui.txtVoorstel.setPlainText(st.voorstel_blok.strip("\n"))
        if hasattr(self.ui, "txtHuidig"):
            self.ui.txtHuidig.setPlainText(st.huidig_blok)

        # Hunks opbouwen en tonen
        self._rebuild_hunks()
        self._set_status("Formulier geanalyseerd, panelen en hunks voorbereid.")

# [END: _on_analyse_form]
# [FUNC: _rebuild_hunks]
    def _rebuild_hunks(self) -> None:
        """Herbouw de hunklijst obv links/rechts en toggles."""
        left_text = (
            self.ui.txtVoorstel.toPlainText()
            if hasattr(self.ui, "txtVoorstel")
            else self.state.voorstel_blok
        )
        right_text = (
            self.ui.txtHuidig.toPlainText()
            if hasattr(self.ui, "txtHuidig")
            else self.state.huidig_blok
        )

        ignore_ws = bool(
            getattr(self.ui, "chkIgnoreWhitespace", None)
            and self.ui.chkIgnoreWhitespace.isChecked()
        )
        ignore_case = bool(
            getattr(self.ui, "chkIgnoreCase", None)
            and self.ui.chkIgnoreCase.isChecked()
        )
        hide_ident = bool(
            getattr(self.ui, "chkHideIdentical", None)
            and self.ui.chkHideIdentical.isChecked()
        )

        self._hunks, self._opcodes = _build_hunks_and_opcodes(
            right_text=right_text,
            left_text=left_text,
            ignore_ws=ignore_ws,
            ignore_case=ignore_case,
        )
        self._update_hunks_list(hide_ident=hide_ident)

# [END: _rebuild_hunks]
# [FUNC: _update_hunks_list]
    def _update_hunks_list(self, hide_ident: bool) -> None:
        lw = getattr(self.ui, "listHunks", None)
        if lw is None:
            return
        lw.clear()
        for hk in self._hunks:
            text = f"{hk.tag.upper():7s}  r:{hk.r1}-{hk.r2}  l:{hk.l1}-{hk.l2}  (+{hk.n_add}/-{hk.n_del})"
            if hk.preview:
                text += f"  |  {hk.preview}"
            item = QtWidgets.QListWidgetItem(text)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, hk)
            lw.addItem(item)
        self._set_status(f"{len(self._hunks)} wijzigingshunk(s) gevonden.")

# [END: _update_hunks_list]
# [FUNC: _selected_hunk_keys]
    def _selected_hunk_keys(self) -> set[Tuple[int, int, int, int]]:
        lw = getattr(self.ui, "listHunks", None)
        keys: set[Tuple[int, int, int, int]] = set()
        if lw is None:
            return keys
        for i in range(lw.count()):
            it = lw.item(i)
            if it.checkState() == QtCore.Qt.CheckState.Checked:
                hk: Hunk = it.data(QtCore.Qt.ItemDataRole.UserRole)
                keys.add((hk.r1, hk.r2, hk.l1, hk.l2))
        return keys

# [END: _selected_hunk_keys]
# [FUNC: _apply_hunks]
    def _apply_hunks(self, selected_only: bool) -> None:
        """Maak nieuwe 'rechts' (txtHuidig). Schrijft NIET naar file."""
        left_lines = (
            self.ui.txtVoorstel.toPlainText()
            if hasattr(self.ui, "txtVoorstel")
            else self.state.voorstel_blok
        ).splitlines(keepends=True)
        right_lines = (
            self.ui.txtHuidig.toPlainText()
            if hasattr(self.ui, "txtHuidig")
            else self.state.huidig_blok
        ).splitlines(keepends=True)

        # Volledig blok toepassen → exact links tonen (geen lock-markers hier)
        if not selected_only:
            new_right = left_lines

        else:
            # Geselecteerd toepassen
            if self.state.actie == "ADD" and not right_lines:
                new_right = left_lines
            else:
                selected = self._selected_hunk_keys()
                out: List[str] = []
                for tag, r1, r2, l1, l2 in self._opcodes:
                    if tag == "equal":
                        out.extend(right_lines[r1:r2])
                    else:
                        take_left = (r1, r2, l1, l2) in selected
                        out.extend(
                            left_lines[l1:l2] if take_left else right_lines[r1:r2]
                        )
                new_right = out

            # Lock markers alleen bij “geselecteerd toepassen”
            if (
                getattr(self.ui, "chkLockMarkers", None)
                and self.ui.chkLockMarkers.isChecked()
            ):
                mv = self.state.marker_van.strip()
                mt = self.state.marker_tot.strip()
                right_markers = {}
                for ln in right_lines:
                    s = ln.rstrip("\r\n")
                    if s == mv or s == mt:
                        right_markers[s] = ln
                for i, ln in enumerate(new_right):
                    s = ln.rstrip("\r\n")
                    if s in right_markers:
                        new_right[i] = right_markers[s]

        if hasattr(self.ui, "txtHuidig"):
            self.ui.txtHuidig.setPlainText("".join(new_right))
        self._set_status(
            "Wijzigingen toegepast in rechterpaneel (nog niet opgeslagen)."
        )

# [END: _apply_hunks]
# [FUNC: _compose_new_file_lines]
    def _compose_new_file_lines(
        self, action: str, proposed_right_text: str
    ) -> Optional[List[str]]:
        """Maak de volledige bestandsinhoud voor preview/save."""
        st = self.state
        file_lines = st.file_lines[:] if st.file_lines else []
        if action == "ADD":
            add_lines = proposed_right_text.splitlines(keepends=True)
            add_lines = _ensure_trailing_nl(add_lines)
            # Probeer vóór [END: SECTION: EXTENSION_POINTS] in te voegen, anders aan eind
            insert_at = None
            end_token = "# [END: SECTION: EXTENSION_POINTS]"
            for idx, ln in enumerate(file_lines):
                if ln.rstrip("\r\n") == end_token:
                    insert_at = idx
                    break
            if insert_at is None:
                file_lines.extend(add_lines)
            else:
                file_lines[insert_at:insert_at] = add_lines
            return file_lines

        if action in ("REPLACE", "DELETE"):
            s, e = st.huidig_blok_range
            if s < 0 or e < 0:
                self._error_box(
                    "Markers niet gevonden",
                    "Er is geen geldig marker-bereik om te vervangen/verwijderen.",
                )
                return None

            if action == "DELETE":
                del file_lines[s : e + 1]
                return file_lines

            # REPLACE: vervang uitsluitend het blok (incl. markers)
            # Extract alleen het blok uit proposed_right_text (kan context bevatten)
            block_only = _extract_block_only(
                proposed_right_text, st.marker_van, st.marker_tot
            )
            if not block_only:
                self._error_box(
                    "Blok niet gevonden",
                    "Kon het blok (tussen markers) niet uit het rechterpaneel halen.",
                )
                return None
            block_only = _ensure_trailing_nl(block_only)
            file_lines[s : e + 1] = block_only
            return file_lines

        self._error_box("Onbekende actie", f"Actie '{action}' is niet ondersteund.")
        return None

# [END: _compose_new_file_lines]
# [FUNC: _on_dry_run]
    def _on_dry_run(self) -> None:
        """Toon preview van het volledige bestand met de huidige rechtertekst."""
        st = self.state
        # gebruik inhoud uit rechts (wat je net selectief/vol heeft toegepast)
        proposed_right_text = (
            self.ui.txtHuidig.toPlainText()
            if hasattr(self.ui, "txtHuidig")
            else st.huidig_blok
        )
        if st.actie == "ADD" and not proposed_right_text.strip():
            # geen rechterinhoud → gebruik links
            proposed_right_text = self.ui.txtVoorstel.toPlainText()

        new_lines = self._compose_new_file_lines(st.actie, proposed_right_text)
        if new_lines is None:
            return

        # Toon in dialoog
        dlg = QtWidgets.QDialog(self.window)
        dlg.setWindowTitle("Dry-run: resultaat (niet opgeslagen)")
        dlg.resize(900, 600)
        lay = QtWidgets.QVBoxLayout(dlg)
        te = QtWidgets.QPlainTextEdit(dlg)
        te.setReadOnly(True)
        te.setPlainText("".join(new_lines))
        lay.addWidget(te)
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close, parent=dlg
        )
        btn.rejected.connect(dlg.reject)
        lay.addWidget(btn)
        dlg.exec()

# [END: _on_dry_run]
# [FUNC: _on_save]
    def _on_save(self) -> None:
        """Schrijf naar bestand (met .bak) + auto-Git (add/commit/push)."""
        st = self.state
        if not st.bestand:
            self._error_box("Onbekend bestand", "Er is geen doelbestand ingesteld.")
            return

        # bepaal rechtertekst (wat nu in de UI staat)
        proposed_right_text = (
            self.ui.txtHuidig.toPlainText()
            if hasattr(self.ui, "txtHuidig")
            else st.huidig_blok
        )
        if st.actie == "ADD" and not proposed_right_text.strip():
            proposed_right_text = self.ui.txtVoorstel.toPlainText()

        new_lines = self._compose_new_file_lines(st.actie, proposed_right_text)
        if new_lines is None:
            return

        # Backup
        bak = Path(str(st.bestand) + ".bak")
        try:
            original = st.bestand.read_text(encoding="utf-8")
            bak.write_text(original, encoding="utf-8")
        except Exception as ex:
            self._error_box("Backup mislukt", f"Kon backup niet schrijven:\n{ex}")
            return

        # Schrijf nieuwe file
        try:
            Path(st.bestand).write_text("".join(new_lines), encoding="utf-8")
        except Exception as ex:
            self._error_box("Opslaan mislukt", f"Kon wijzigingen niet schrijven:\n{ex}")
            return

        self._set_status(f"Opgeslagen. Backup: {bak.name}")
        self._info_box(
            "Opgeslagen",
            f"Wijzigingen zijn opgeslagen.\nBackup gemaakt als: {bak.name}",
        )

        # Repo-root bepalen: voorkeur project_path uit .projassist.json, anders map van het bestand
        repo_root = None
        if self.project_root:
            repo_root = Path(self.project_root)
        elif self.json_path:
            # .projassist.json staat normaal in je projectroot
            repo_root = Path(self.json_path).parent
        else:
            repo_root = Path(st.bestand).resolve().parent

        if not _git_is_repo(repo_root):
            # Niet in een git-repo → geen push
            self._set_status("Niet in Git-repo, push overgeslagen.")
            return

        # Commit-boodschap
        blok_info = st.blok_id or (st.marker_van if st.marker_van else "")
        reden = (st.korte_reden or "").strip()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"Codewijziger: {st.actie} {Path(st.bestand).name}"
        if blok_info:
            msg += f" [{blok_info}]"
        if reden:
            msg += f" — {reden}"
        msg += f" — {stamp}"

        _git_after_save(repo_root, Path(st.bestand), msg, self.window)

# [END: _on_save]
# [FUNC: _on_restore]
    def _on_restore(self) -> None:
        """Herstel uit .bak."""
        st = self.state
        if not st.bestand:
            self._error_box("Onbekend bestand", "Er is geen doelbestand ingesteld.")
            return
        bak = Path(str(st.bestand) + ".bak")
        if not bak.exists():
            self._error_box("Geen backup", f"Backup niet gevonden: {bak}")
            return
        try:
            data = bak.read_text(encoding="utf-8")
            st.bestand.write_text(data, encoding="utf-8")
        except Exception as ex:
            self._error_box("Herstel mislukt", f"Kon backup niet herstellen:\n{ex}")
            return
        self._set_status("Backup hersteld.")
        self._info_box("Hersteld", "De backup is succesvol teruggezet.")

# [END: _on_restore]
# [END: CodeWijzigerController]

