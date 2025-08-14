# services/marker_normalizer.py
[SECTION: Imports & Constants]
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import re, shutil, datetime, ast, io, os
from typing import List, Optional, Tuple

[END: Imports & Constants]
BEGIN_SEC = "[SECTION:"
END_SEC_PREFIX = "[END:"
BEGIN_FUNC = "[FUNC:"
BEGIN_CLASS = "[CLASS:"

# Herken alle mogelijke oude markers (jouw oude, en generiek zoals region/endregion)
CLEAN_PATTERNS = [
    r"^\s*\[SECTION:.*\]\s*$",
    r"^\s*\[FUNC:.*\]\s*$",
    r"^\s*\[CLASS:.*\]\s*$",
    r"^\s*\[END:.*\]\s*$",
    r"^\s*#\s*region\b.*$",
    r"^\s*#\s*endregion\b.*$",
    r"^\s*//\s*region\b.*$",
    r"^\s*//\s*endregion\b.*$",
    r"^\s*#\s*-{3,}.*$",
    r"^\s*#\s*= {3,}.*$",
]
CLEAN_RE = re.compile("|".join(CLEAN_PATTERNS))

[CLASS: StepLog]

@dataclass
[FUNC: add]
class StepLog:
    steps: List[str]
[END: add]
[FUNC: _timestamp]

[END: StepLog]
[END: _timestamp]
    def add(self, msg: str) -> None:
        self.steps.append(msg)
[FUNC: _backup_file]


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _backup_file(src: Path, project_root: Optional[Path], log: StepLog) -> Path:
    if not project_root:
        # fallback: backup naast het bestand
        dst_dir = src.parent / "backup" / _timestamp()
    else:
        rel = (
            src.resolve().relative_to(project_root.resolve())
            if src.is_absolute()
            else Path(src)
        )
[END: _backup_file]
        dst_dir = project_root / "backup" / _timestamp() / rel.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
[FUNC: _remove_old_markers]
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    log.add(f"Back‑up gemaakt: {dst}")
    return dst

[END: _remove_old_markers]

def _remove_old_markers(lines: List[str], log: StepLog) -> List[str]:
[FUNC: _find_import_block]
    cleaned = [ln for ln in lines if not CLEAN_RE.match(ln)]
    removed = len(lines) - len(cleaned)
    log.add(f"Oude markers verwijderd: {removed} regel(s).")
    return cleaned


def _find_import_block(lines: List[str]) -> Optional[Tuple[int, int]]:
    """
    Vind het aaneengesloten import‑blok (van eerste import/from tot de laatste
    voordat er echte code/def/class komt).
    """
    first = None
    last = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(import\s+\w|from\s+\w)", ln):
            if first is None:
                first = i
            last = i
        elif first is not None and re.match(r"^\s*(def|class)\b", ln):
            break
        elif first is not None and ln.strip() == "":
            # laat één lege regel in import‑blok toe
            last = i
[END: _find_import_block]
        elif first is not None and not re.match(r"^\s*(import|from|\Z)", ln):
            # iets anders dan import/from/lege regel -> stop
[FUNC: _inject_section]
            break
    if first is None:
        return None
    return (first, last if last is not None else first)
[END: _inject_section]


[FUNC: _insert_line]
def _inject_section(lines: List[str], start_idx: int, end_idx: int, title: str) -> None:
    """Voeg sectie‑markers rond [start_idx, end_idx] (inclusief) toe."""
[END: _insert_line]
    lines.insert(start_idx, f"{BEGIN_SEC} {title}]\n")
    lines.insert(end_idx + 2, f"{END_SEC_PREFIX} {title}]\n")  # +2 door eerdere insert
[FUNC: _inject_func_markers]


def _insert_line(lines: List[str], idx: int, text: str) -> None:
    lines.insert(idx, text if text.endswith("\n") else text + "\n")

[END: _inject_func_markers]

def _inject_func_markers(
[FUNC: _inject_class_markers]
    lines: List[str], start_line: int, end_line: int, name: str
) -> None:
    _insert_line(lines, start_line - 1, f"{BEGIN_FUNC} {name}]")
    _insert_line(lines, end_line + 1, f"{END_SEC_PREFIX} {name}]")

[END: _inject_class_markers]

def _inject_class_markers(
[FUNC: _parse_python_blocks]
    lines: List[str], start_line: int, end_line: int, name: str
) -> None:
    _insert_line(lines, start_line - 1, f"{BEGIN_CLASS} {name}]")
[END: _parse_python_blocks]
    _insert_line(lines, end_line + 1, f"{END_SEC_PREFIX} {name}]")

[FUNC: _collect_defs_with_ranges]

def _parse_python_blocks(src_text: str) -> List[ast.AST]:
    tree = ast.parse(src_text)
    return list(ast.walk(tree))


def _collect_defs_with_ranges(
    src_text: str,
) -> Tuple[
    List[Tuple[str, int, int]], List[Tuple[str, int, int, List[Tuple[str, int, int]]]]
]:
    """
    Returns:
      - functions: list of (name, lineno, end_lineno)
      - classes: list of (name, lineno, end_lineno, methods[list of (name, lineno, end_lineno)])
    """
    tree = ast.parse(src_text)
    funcs = []
    classes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs.append(
                (node.name, node.lineno, getattr(node, "end_lineno", node.lineno))
            )
        elif isinstance(node, ast.ClassDef):
            methods = []
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    methods.append(
                        (sub.name, sub.lineno, getattr(sub, "end_lineno", sub.lineno))
                    )
            classes.append(
                (
                    node.name,
[END: _collect_defs_with_ranges]
                    node.lineno,
                    getattr(node, "end_lineno", node.lineno),
[FUNC: _find_main_guard]
                    methods,
                )
            )
    return funcs, classes


def _find_main_guard(lines: List[str]) -> Optional[Tuple[int, int]]:
    """
    Vind blok: if __name__ == "__main__":
    Neem tot einde file of tot volgende top‑level def/class.
    """
    start = None
    for i, ln in enumerate(lines):
        if re.match(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*$', ln):
            start = i
            break
    if start is None:
        return None
[END: _find_main_guard]
    end = len(lines) - 1
    for j in range(start + 1, len(lines)):
[FUNC: normalize_markers]
        if re.match(r"^(def|class)\b", lines[j].lstrip()):
            end = j - 1
            break
    return (start, end)


def normalize_markers(
    file_path: Path,
    project_root: Optional[Path] = None,
    git_callback: Optional[callable] = None,
) -> List[str]:
    """
    Doet: back‑up → clean → parse → inject → opslaan → (git)
    Retourneert een lijst van logstappen (voor jouw GUI pop‑up).
    """
    log = StepLog([])
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {file_path}")

    ext = file_path.suffix.lower()
    log.add(f"Bestand: {file_path} (ext: {ext})")

    # 1) Back‑up
    _backup_file(file_path, project_root, log)

    # 2) Clean
    orig_text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = orig_text.splitlines(keepends=True)
    lines = _remove_old_markers(lines, log)

    if ext == ".py":
        # 3) Parse (Python)
        text_wo = "".join(lines)
        funcs, classes = _collect_defs_with_ranges(text_wo)

        # 4) Inject secties en markers
        # 4a) Imports
        imp = _find_import_block(lines)
        if imp:
            _inject_section(lines, imp[0], imp[1], "Imports & Constants")

        # 4b) Classes + methods
        # Sorteer op omgekeerde startlijn zodat inserts indices niet breken
        for cname, cstart, cend, methods in sorted(
            classes, key=lambda t: t[1], reverse=True
        ):
            _inject_class_markers(lines, cstart, cend, cname)
            for mname, mstart, mend in sorted(
                methods, key=lambda t: t[1], reverse=True
            ):
                _inject_func_markers(lines, mstart, mend, mname)

        # 4c) Top‑level functions
        for fname, fstart, fend in sorted(funcs, key=lambda t: t[1], reverse=True):
            _inject_func_markers(lines, fstart, fend, fname)

        # 4d) Main guard
        mg = _find_main_guard(lines)
        if mg:
            _inject_section(lines, mg[0], mg[1], "CLI / Entrypoint")

        # 5) Opslaan
        file_path.write_text("".join(lines), encoding="utf-8")
        log.add("Markers toegepast en bestand opgeslagen.")

    elif ext == ".ui":
        # Voor .ui: enkel oude markers weghalen en hoofdsecties labelen bovenaan/onderaan file
        # (we wijzigen geen XML structuur om fouten te vermijden)
        header = f"{BEGIN_SEC} UI File]\n"
        footer = f"{END_SEC_PREFIX} UI File]\n"
        new_text = header + "".join(lines) + footer
        file_path.write_text(new_text, encoding="utf-8")
        log.add("UI: markers rond volledige file toegevoegd (veilig).")

    else:
        # Onbekend type: enkel clean + globale sectie, niet stuk‑specifiek injecteren
        new_text = f"{BEGIN_SEC} File]\n" + "".join(lines) + f"{END_SEC_PREFIX} File]\n"
        file_path.write_text(new_text, encoding="utf-8")
        log.add("Onbekend type: globale sectie toegevoegd.")

    # 6) Git (optioneel)
    if git_callback:
        try:
            git_callback([file_path], f"Normalize markers: {file_path.name}")
[END: normalize_markers]
            log.add("Git: wijzigingen vastgelegd.")
        except Exception as ex:
            log.add(f"Git: overslagen/fout: {ex}")

    log.add("Klaar.")
    return log.steps
