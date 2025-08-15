# [SECTION: Imports]
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6 import QtWidgets



# [END: Imports]
# [FUNC: _run_git]
def _run_git(args: List[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, shell=False)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

# [END: _run_git]

# [FUNC: _git_is_repo]
def _git_is_repo(cwd: Path) -> bool:
    rc, out, _ = _run_git(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return rc == 0 and (out.lower() == "true")

# [END: _git_is_repo]

# [FUNC: _git_current_branch]
def _git_current_branch(cwd: Path) -> Optional[str]:
    rc, out, _ = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return out if rc == 0 and out else None

# [END: _git_current_branch]

# [FUNC: _git_after_save]
def _git_after_save(cwd: Path, target_paths: List[Path], msg: str, parent) -> None:
    # target_paths: bestanden relatief aan cwd of absolute paden
    rels: List[str] = []
    for p in target_paths:
        try:
            rels.append(str(Path(p).resolve().relative_to(cwd.resolve())))
        except Exception:
            rels.append(str(Path(p).name))
    rc, _, err = _run_git(["git", "add", *rels], cwd)
    if rc != 0:
        QtWidgets.QMessageBox.information(parent, "Git", f"git add faalde:\n{err}")
        return
    rc, _, err = _run_git(["git", "commit", "-m", msg], cwd)
    if rc != 0:
        QtWidgets.QMessageBox.information(
            parent, "Git", f"git commit:\n{err or 'niets te committen'}"
        )
        return
    rc, out, err = _run_git(["git", "push"], cwd)
    if rc != 0:
        QtWidgets.QMessageBox.information(
            parent, "Git", f"git push faalde:\n{err or out}"
        )
    else:
        QtWidgets.QMessageBox.information(
            parent, "Git", "Wijzigingen gecommit en gepusht."
        )

# [END: _git_after_save]



# [FUNC: _load_json]
def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

# [END: _load_json]

# [FUNC: _save_json]
def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# [END: _save_json]



# [FUNC: _scan_scripts]
def _scan_scripts(root: Path, exts: tuple[str, ...] = (".py", ".ui")) -> List[str]:
    out: List[str] = []
    backup_root = (root / "backup").resolve()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # sla alles onder <root>/backup/… over
        try:
            if backup_root in p.resolve().parents:
                continue
        except Exception:
            pass
        if p.suffix.lower() in exts:
            rel = p.relative_to(root).as_posix()
            out.append(rel)
    out.sort(key=lambda s: (0 if s.endswith(".py") else 1, s.lower()))
    return out

# [END: _scan_scripts]



# [FUNC: _build_github_url_map]
def _build_github_url_map(
    root: Path, scripts: List[str], cfg: Dict[str, Any]
) -> Dict[str, str]:
    """
    Verwacht in cfg (uit .projassist.json) bijv.:
      - 'github_repo': 'https://github.com/<owner>/<repo>'
      - optioneel 'branch': 'main'  (anders HEAD-branch)
    """
    base = (cfg.get("github_repo") or "").strip()
    if not base:
        return {}
    branch = (cfg.get("branch") or "").strip()
    if not branch:
        # Probeer huidige branch uit Git te halen
        if _git_is_repo(root):
            branch = _git_current_branch(root) or "main"
        else:
            branch = "main"
    # Maak browser-URL's (geen raw)
    # https://github.com/<owner>/<repo>/blob/<branch>/<path>
    return {rel: f"{base.rstrip('/')}/blob/{branch}/{rel}" for rel in scripts}

# [END: _build_github_url_map]



# [CLASS: SyncProjassistService]
@dataclass
class SyncProjassistService:
    project_root: Path
    json_path: Path
    parent_window: QtWidgets.QWidget

# [FUNC: run]
    def run(self) -> None:
        root = self.project_root
        if not root or not root.exists():
            QtWidgets.QMessageBox.critical(
                self.parent_window, "Sync", "Projectroot niet gevonden."
            )
            return
        if not self.json_path or not self.json_path.exists():
            QtWidgets.QMessageBox.critical(
                self.parent_window, "Sync", ".projassist.json niet gevonden."
            )
            return

        cfg = _load_json(self.json_path)
        scanned = _scan_scripts(root)  # slaat 'backup/' al over

        # Bestaande lijst ophalen/normaliseren en 'backup/' verwijderen
        existing: List[str] = []
        if isinstance(cfg.get("scripts"), list):
            existing = [str(x) for x in cfg.get("scripts") if isinstance(x, (str,))]
        existing = [s for s in existing if not s.startswith("backup/")]

        # Unieke merge: eerst bestaande (opgeschoond), dan nieuwe
        existing_set = set(existing)
        new_items = [s for s in scanned if s not in existing_set]
        updated_list = existing + new_items

        # URL-map opschonen (verwijder keys onder 'backup/')
        url_map = (
            cfg.get("script_urls") if isinstance(cfg.get("script_urls"), dict) else {}
        )
        if url_map:
            url_map = {k: v for k, v in url_map.items() if not k.startswith("backup/")}

        changed = bool(new_items or len(updated_list) != len(cfg.get("scripts", [])))
        if changed:
            cfg["scripts"] = updated_list
            # URL's bijwerken of aanvullen
            built_urls = _build_github_url_map(root, updated_list, cfg)
            if built_urls:
                url_map.update(built_urls)
                cfg["script_urls"] = url_map
            elif url_map:
                cfg["script_urls"] = url_map

            # Schrijf JSON
            _save_json(self.json_path, cfg)

            # Auto Git
            if _git_is_repo(root):
                _git_after_save(
                    cwd=root,
                    target_paths=[self.json_path],
                    msg="SyncProjAssist: scripts gesynchroniseerd en JSON bijgewerkt",
                    parent=self.parent_window,
                )
            QtWidgets.QMessageBox.information(
                self.parent_window,
                "Sync voltooid",
                f"{len(new_items)} nieuw(e) script(s) toegevoegd en lijst opgeschoond.",
            )
        else:
            QtWidgets.QMessageBox.information(
                self.parent_window,
                "Geen wijzigingen",
                "Alle scripts stonden al correct in .projassist.json.",
            )

# [END: run]
# [END: SyncProjassistService]

