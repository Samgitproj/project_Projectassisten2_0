# handlers/marker_normalizer.py
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable, Dict, Any
import re, shutil, datetime, ast, json
from PyQt6 import QtWidgets


# [SECTION: GIT HELPERS]
def _run_git(args: List[str], cwd: Path) -> tuple[int, str, str]:
    import subprocess

    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, shell=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def _git_is_repo(cwd: Path) -> bool:
    rc, out, _ = _run_git(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return rc == 0 and (out.lower() == "true")


def _git_after_save_batch(
    cwd: Path, target_paths: List[Path], msg: str
) -> tuple[bool, str]:
    # add → commit → push; return (ok, detail)
    rels: List[str] = []
    for p in target_paths:
        try:
            rels.append(str(Path(p).resolve().relative_to(cwd.resolve())))
        except Exception:
            rels.append(str(Path(p).name))
    rc, _, err = _run_git(["git", "add", *rels], cwd)
    if rc != 0:
        return False, f"git add faalde: {err}"
    rc, _, err = _run_git(["git", "commit", "-m", msg], cwd)
    if rc != 0:
        # niets te committen is geen echte fout
        return False, err or "niets te committen"
    rc, out, err = _run_git(["git", "push"], cwd)
    if rc != 0:
        return False, err or out
    return True, "Wijzigingen gecommit en gepusht."


# [END: GIT HELPERS]

# =========================================================
# Marker-dialect per type
# =========================================================

LINE_COMMENT_PREFIXES: Dict[str, Tuple[str, str]] = {
    "hash": ("# ", ""),
    "slashes": ("// ", ""),
    "rem": ("REM ", ""),
    "semi": ("; ", ""),
    "xml": ("<!-- ", " -->"),
}

# Extensie-groepen
EXT_HASH = {
    ".py",
    ".ps1",
    ".psm1",
    ".sh",
    ".bash",
    ".zsh",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".toml",
    ".properties",
    ".conf",
}
EXT_SLASHES = {
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".rs",
    ".swift",
    ".kt",
    ".php",
}
EXT_REM = {".bat", ".cmd"}
EXT_XML = {".xml", ".ui", ".html", ".htm", ".xhtml"}


def _dialect_for_ext(ext: str) -> Tuple[str, str]:
    ext = (ext or "").lower()
    if ext in EXT_REM:
        return LINE_COMMENT_PREFIXES["rem"]
    if ext in EXT_SLASHES:
        return LINE_COMMENT_PREFIXES["slashes"]
    if ext in EXT_XML:
        return LINE_COMMENT_PREFIXES["xml"]
    if ext in EXT_HASH:
        return LINE_COMMENT_PREFIXES["hash"]
    return LINE_COMMENT_PREFIXES["hash"]


# =========================================================
# Marker-helpers
# =========================================================
def _mk_section_begin(title: str, prefix: str, suffix: str) -> str:
    return f"{prefix}[SECTION: {title}]{suffix}"


def _mk_end(name: str, prefix: str, suffix: str) -> str:
    return f"{prefix}[END: {name}]{suffix}"


def _mk_func_begin(name: str, prefix: str, suffix: str) -> str:
    return f"{prefix}[FUNC: {name}]{suffix}"


def _mk_class_begin(name: str, prefix: str, suffix: str) -> str:
    return f"{prefix}[CLASS: {name}]{suffix}"


# =========================================================
# Clean-regels
# =========================================================
MARKER_CORE = r"\[\s*(?:SECTION|FUNC|CLASS|END)\s*:\s*[^]]*]\s*(?:START|END)?\s*"
CLEAN_MARKER_LINE = re.compile(
    r"^\s*(?:#|//|;|REM\s+|<!--\s*)?\s*" + MARKER_CORE + r"(?:-->)?\s*$", re.IGNORECASE
)
CLEAN_REGIONS = re.compile(
    r"^\s*(?:#\s*region\b|#\s*endregion\b|//\s*region\b|//\s*endregion\b|;\s*region\b|;\s*endregion\b|REM\s+region\b|REM\s+endregion\b).*$",
    re.IGNORECASE,
)
CLEAN_DECOR = re.compile(r"^\s*#?\s*[-=]{3,}.*$", re.IGNORECASE)


@dataclass
class StepLog:
    steps: List[str]

    def add(self, msg: str) -> None:
        self.steps.append(msg)


def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _backup_file(src: Path, project_root: Optional[Path], log: StepLog) -> Path:
    if not project_root:
        dst_dir = src.parent / "backup" / _ts()
    else:
        try:
            rel = src.resolve().relative_to(project_root.resolve())
        except Exception:
            rel = Path(src.name)
        dst_dir = project_root / "backup" / _ts() / rel.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    log.add(f"Back-up gemaakt: {dst}")
    return dst


def _remove_old_markers(lines: List[str], log: StepLog) -> List[str]:
    cleaned, removed = [], 0
    for ln in lines:
        if (
            CLEAN_MARKER_LINE.match(ln)
            or CLEAN_REGIONS.match(ln)
            or CLEAN_DECOR.match(ln)
        ):
            removed += 1
        else:
            cleaned.append(ln)
    log.add(f"Oude markers verwijderd: {removed} regel(s).")
    return cleaned


def _insert_line(lines: List[str], idx: int, text: str) -> None:
    if idx < 0:
        idx = 0
    if idx > len(lines):
        idx = len(lines)
    if not text.endswith("\n"):
        text += "\n"
    lines.insert(idx, text)


# =========================================================
# Python analyse (AST) + main/imports
# =========================================================
def _py_node_start_lineno(node: ast.AST) -> int:
    if isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    ) and getattr(node, "decorator_list", None):
        return min(d.lineno for d in node.decorator_list)  # type: ignore[attr-defined]
    return getattr(node, "lineno", 1)


def _py_node_end_lineno(node: ast.AST) -> int:
    end_ln = getattr(node, "end_lineno", None)
    if isinstance(end_ln, int):
        return end_ln

    def last_line(n: ast.AST) -> int:
        v = getattr(n, "end_lineno", None)
        if isinstance(v, int):
            return v
        for attr in ("body", "orelse", "finalbody"):
            seq = getattr(n, attr, None)
            if isinstance(seq, list) and seq:
                return last_line(seq[-1])
        return getattr(n, "lineno", 1)

    return last_line(node)


def _py_find_import_block(lines: List[str]) -> Optional[Tuple[int, int]]:
    first = last = None
    paren_depth = 0
    cont = False
    in_block = False
    for i, ln in enumerate(lines):
        is_import = bool(re.match(r"^\s*(import\s+\w|from\s+\w)", ln))
        if not in_block:
            if is_import:
                first = last = i
                in_block = True
                paren_depth = ln.count("(") - ln.count(")")
                cont = ln.rstrip().endswith("\\")
            continue
        if is_import or paren_depth > 0 or cont:
            last = i
            paren_depth += ln.count("(") - ln.count(")")
            cont = ln.rstrip().endswith("\\")
            continue
        if ln.strip() == "":
            last = i
            cont = False
            continue
        break
    if first is None:
        return None
    return (first, last if last is not None else first)


def _py_collect(src_text: str):
    lines = src_text.splitlines(keepends=True)
    tree = ast.parse(src_text)
    functions: List[Tuple[str, int, int]] = []
    classes: List[Tuple[str, int, int, List[Tuple[str, int, int]]]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s = _py_node_start_lineno(node)
            e = _py_node_end_lineno(node)
            functions.append((node.name, s, e))
        elif isinstance(node, ast.ClassDef):
            cs = _py_node_start_lineno(node)
            ce = _py_node_end_lineno(node)
            methods: List[Tuple[str, int, int]] = []
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ms = _py_node_start_lineno(sub)
                    me = _py_node_end_lineno(sub)
                    methods.append((sub.name, ms, me))
            classes.append((node.name, cs, ce, methods))

    def _find_main_guard(lines: List[str]) -> Optional[Tuple[int, int]]:
        start = None
        for i, ln in enumerate(lines):
            if re.match(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*$', ln):
                start = i
                break
        if start is None:
            return None
        end = len(lines) - 1
        for j in range(start + 1, len(lines)):
            if re.match(r"^\s*(def|class)\b", lines[j]):
                end = j - 1
                break
        return (start, end)

    imp = _py_find_import_block(lines)
    mg = _find_main_guard(lines)
    return {
        "imports": imp,
        "functions": functions,
        "classes": classes,
        "main_guard": mg,
    }


# =========================================================
# PowerShell / Bash / Batch / Generic
# =========================================================
def _scan_block_braces(lines: List[str], start_idx: int) -> int:
    depth = 0
    started = False
    for i in range(start_idx, len(lines)):
        depth += lines[i].count("{")
        if lines[i].count("{"):
            started = True
        depth -= lines[i].count("}")
        if started and depth <= 0:
            return i
    return start_idx


def _ps_collect(lines: List[str]):
    funcs: List[Tuple[str, int, int]] = []
    classes: List[Tuple[str, int, int]] = []
    imports: Optional[Tuple[int, int]] = None
    first = last = None
    for i, ln in enumerate(lines):
        if re.match(
            r"^\s*(using\s+module|Import-Module\b|\.\s+\S+)", ln, re.IGNORECASE
        ):
            if first is None:
                first = i
            last = i
            continue
        if first is not None:
            if ln.strip() == "":
                last = i
                continue
            if re.match(r"^\s*(function|class)\b", ln, re.IGNORECASE):
                break
            if not re.match(
                r"^\s*(using\s+module|Import-Module\b|\.\s+\S+)", ln, re.IGNORECASE
            ):
                break
    if first is not None:
        imports = (first, last if last is not None else first)
    i = 0
    while i < len(lines):
        ln = lines[i]
        m_fun = re.match(r"^\s*function\s+([A-Za-z0-9_:-]+)\s*\{", ln, re.IGNORECASE)
        m_cls = re.match(r"^\s*class\s+([A-Za-z0-9_]+)\s*\{", ln, re.IGNORECASE)
        if m_fun:
            name = m_fun.group(1)
            end = _scan_block_braces(lines, i)
            funcs.append((name, i + 1, end + 1))
            i = end + 1
            continue
        if m_cls:
            name = m_cls.group(1)
            end = _scan_block_braces(lines, i)
            classes.append((name, i + 1, end + 1))
            i = end + 1
            continue
        i += 1
    return {
        "imports": imports,
        "functions": funcs,
        "classes": [(n, s, e, []) for (n, s, e) in classes],
    }


def _sh_collect(lines: List[str]):
    funcs: List[Tuple[str, int, int]] = []
    imports: Optional[Tuple[int, int]] = None
    first = last = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(source\s+\S+|\.\s+\S+)\b", ln):
            if first is None:
                first = i
            last = i
            continue
        if first is not None:
            if ln.strip() == "":
                last = i
                continue
            if re.match(r"^\s*\w+\s*\(\s*\)\s*\{", ln) or re.match(
                r"^\s*function\s+\w+\s*\{", ln
            ):
                break
            if not re.match(r"^\s*(source\s+\S+|\.\s+\S+)\b", ln):
                break
    if first is not None:
        imports = (first, last if last is not None else first)
    i = 0
    while i < len(lines):
        ln = lines[i]
        m1 = re.match(r"^\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\{", ln)
        m2 = re.match(r"^\s*function\s+([A-Za-z_]\w*)\s*\{", ln)
        if m1 or m2:
            name = (m1 or m2).group(1)
            end = _scan_block_braces(lines, i)
            funcs.append((name, i + 1, end + 1))
            i = end + 1
            continue
        i += 1
    return {"imports": imports, "functions": funcs, "classes": []}


def _bat_collect(lines: List[str]):
    funcs: List[Tuple[str, int, int]] = []
    label_lines: List[Tuple[str, int]] = []
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*:([A-Za-z0-9_\.][A-Za-z0-9_\. -]*)\s*$", ln)
        if m:
            label_lines.append((m.group(1).strip(), i))
    for idx, (name, start) in enumerate(label_lines):
        end = (
            (label_lines[idx + 1][1] - 1)
            if idx + 1 < len(label_lines)
            else (len(lines) - 1)
        )
        funcs.append((name, start + 1, end + 1))
    return {"imports": None, "functions": funcs, "classes": []}


def _generic_import_block(lines: List[str]) -> Optional[Tuple[int, int]]:
    first = last = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(import\b|#\s*include\b|const\s+\w+\s*=\s*require\()", ln):
            if first is None:
                first = i
            last = i
            continue
        if first is not None:
            if ln.strip() == "":
                last = i
                continue
            if not re.match(
                r"^\s*(import\b|#\s*include\b|const\s+\w+\s*=\s*require\()", ln
            ):
                break
    if first is None:
        return None
    return (first, last if last is not None else first)


# =========================================================
# Single-file normalizer (bestaand gedrag)
# =========================================================
def normalize_markers(
    file_path: Path,
    project_root: Optional[Path] = None,
    git_callback: Optional[Callable[[List[Path], str], None]] = None,
) -> List[str]:
    log = StepLog([])
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {file_path}")

    # Self-protectie
    if file_path.name.lower() == "marker_normalizer.py":
        log.add("Overgeslagen: marker_normalizer.py zelf wordt niet gemarkeerd.")
        return log.steps

    ext = file_path.suffix.lower()
    prefix, suffix = _dialect_for_ext(ext)
    log.add(f"Bestand: {file_path} (ext: {ext}) — dialect: {prefix.strip()}")

    # 1) Back-up
    _backup_file(file_path, project_root, log)

    # 2) Clean
    orig_text = file_path.read_text(encoding="utf-8-sig", errors="replace")  # strip BOM
    lines = orig_text.splitlines(keepends=True)
    lines = _remove_old_markers(lines, log)

    # 3) Detectie per type
    meta = {"imports": None, "functions": [], "classes": [], "main_guard": None}
    if ext == ".py":
        meta = _py_collect("".join(lines))
    elif ext in {".ps1", ".psm1"}:
        meta = _ps_collect(lines)
    elif ext in {".sh", ".bash", ".zsh"}:
        meta = _sh_collect(lines)
    elif ext in EXT_REM:
        meta = _bat_collect(lines)
    elif ext in EXT_SLASHES:
        meta["imports"] = _generic_import_block(lines)
    elif ext in EXT_XML:
        file_path.write_text("".join(lines), encoding="utf-8")
        log.add(f"{ext}: alleen oude markers verwijderd (geen injectie).")
        if git_callback:
            try:
                git_callback([file_path], f"Normalize markers: {file_path.name}")
                log.add("Git: wijzigingen vastgelegd.")
            except Exception as ex:
                log.add(f"Git: overgeslagen/fout: {ex}")
        log.add("Klaar.")
        return log.steps
    else:
        meta["imports"] = _generic_import_block(lines)

    # 4) Inserts (tie-breaker)
    inserts: List[Tuple[int, int, str]] = []
    total_methods = 0
    BEGIN_PRIO = 0
    CLASS_END_PRIO = 1
    END_PRIO = 2

    for cname, cstart, cend, methods in meta["classes"]:
        inserts.append((cstart - 1, BEGIN_PRIO, _mk_class_begin(cname, prefix, suffix)))
        inserts.append((cend + 1, CLASS_END_PRIO, _mk_end(cname, prefix, suffix)))
        for mname, mstart, mend in methods:
            inserts.append(
                (mstart - 1, BEGIN_PRIO, _mk_func_begin(mname, prefix, suffix))
            )
            inserts.append((mend + 1, END_PRIO, _mk_end(mname, prefix, suffix)))
            total_methods += 1

    for fname, fstart, fend in meta["functions"]:
        inserts.append((fstart - 1, BEGIN_PRIO, _mk_func_begin(fname, prefix, suffix)))
        inserts.append((fend + 1, END_PRIO, _mk_end(fname, prefix, suffix)))

    if meta["imports"]:
        s, e = meta["imports"]
        inserts.append((s, BEGIN_PRIO, _mk_section_begin("Imports", prefix, suffix)))
        inserts.append((e + 1, END_PRIO, _mk_end("Imports", prefix, suffix)))

    if meta.get("main_guard"):
        s, e = meta["main_guard"]
        inserts.append(
            (s, BEGIN_PRIO, _mk_section_begin("CLI / Entrypoint", prefix, suffix))
        )
        inserts.append((e + 1, END_PRIO, _mk_end("CLI / Entrypoint", prefix, suffix)))

    inserts.sort(key=lambda t: (-t[0], t[1]))
    for idx, _prio, text in inserts:
        _insert_line(lines, idx, text)

    # 6) Opslaan
    file_path.write_text("".join(lines), encoding="utf-8")

    # 7) Log
    log.add("Markers toegepast en bestand opgeslagen.")
    log.add(
        "Samenvatting: "
        f"imports={'ja' if meta['imports'] else 'nee'}, "
        f"classes={len(meta['classes'])}, methods={total_methods}, "
        f"functions={len(meta['functions'])}, main={'ja' if meta.get('main_guard') else 'nee'}"
    )

    # 8) Git (optioneel)
    if git_callback:
        try:
            git_callback([file_path], f"Normalize markers: {file_path.name}")
            log.add("Git: wijzigingen vastgelegd.")
        except Exception as ex:
            log.add(f"Git: overgeslagen/fout: {ex}")

    log.add("Klaar.")
    return log.steps


# =========================================================
# Project-breed normaliseren
# =========================================================
def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_project(
    project_root: Path,
    json_path: Path,
    parent: Optional[QtWidgets.QWidget] = None,
    commit_to_git: bool = True,
) -> None:
    """
    Normaliseert markers voor alle .py scripts uit .projassist.json (scripts[]),
    slaat 'backup/'-paden over, maakt per bestand back-up in project_root/backup/<ts>/...
    Één (optionele) Git-commit/push aan het einde.
    """
    if not project_root or not project_root.exists():
        QtWidgets.QMessageBox.critical(parent, "Markers", "Projectroot niet gevonden.")
        return
    if not json_path or not json_path.exists():
        QtWidgets.QMessageBox.critical(
            parent, "Markers", ".projassist.json niet gevonden."
        )
        return

    cfg = _load_json(json_path)
    listed = cfg.get("scripts") if isinstance(cfg.get("scripts"), list) else []
    rel_paths: List[str] = [str(x) for x in listed if isinstance(x, str)]

    # Filter: alleen .py en niet in backup/
    rel_paths = [
        p for p in rel_paths if p.endswith(".py") and not p.startswith("backup/")
    ]

    if not rel_paths:
        QtWidgets.QMessageBox.information(
            parent, "Markers", "Geen .py-scripts gevonden in .projassist.json."
        )
        return

    processed: List[Path] = []
    errors: List[str] = []

    for rel in rel_paths:
        abs_p = (project_root / Path(rel)).resolve()
        try:
            steps = normalize_markers(
                abs_p, project_root=project_root, git_callback=None
            )
            processed.append(abs_p)
        except FileNotFoundError:
            errors.append(f"Ontbrekend bestand: {rel}")
        except Exception as ex:
            errors.append(f"{rel}: {ex}")

    # Git (één batch)
    git_msg = ""
    if commit_to_git and processed and _git_is_repo(project_root):
        ok, detail = _git_after_save_batch(
            project_root,
            [json_path, *processed],
            "MarkerNormalizer: project-breed genormaliseerd",
        )
        git_msg = detail if ok else f"Git waarschuwing: {detail}"

    # Meldingen
    if errors:
        msg = (
            f"Gemarkeerd: {len(processed)} bestand(en).\nFouten: {len(errors)}\n"
            + "\n".join(errors[:5])
        )
    else:
        msg = f"Gemarkeerd: {len(processed)} bestand(en)."
    if git_msg:
        msg += f"\n{git_msg}"
    QtWidgets.QMessageBox.information(parent, "Markers voltooid", msg)
