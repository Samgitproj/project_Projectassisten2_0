# [SECTION: Imports]
import logging
from pathlib import Path
from typing import Optional


from services.json_store import load_json, save_json
logger = logging.getLogger(__name__)



# [END: Imports]
# [FUNC: _to_rel_posix]
def _to_rel_posix(json_path: Path | str, any_path: Path | str) -> str:
    """
    Converteer een absoluut/relatief pad naar een RELATIEF POSIX-pad t.o.v. projectroot (map van .projassist.json).
logger.debug("_to_rel_posix() called")
    """
    jp = Path(json_path)
    root = jp.parent.resolve()
    p = Path(any_path)
    p = p if p.is_absolute() else (root / p)
    try:
        rel = p.resolve().relative_to(root)
    except Exception:
        rel = Path(p.name)
    return rel.as_posix()

# [END: _to_rel_posix]



# [FUNC: register_existing_script]
def register_existing_script(
    projassist_json: str | Path,
    file_path: str | Path,
    name: Optional[str] = None,
) -> dict:
    """
    Registreer een bestaand script in .projassist.json onder key 'scripts'.
logger.debug("register_existing_script() called")
    Retourneert de (nieuwe of bestaande) entry.
    """
    json_path = Path(projassist_json)
    data = load_json(json_path)
    scripts = data.get("scripts", [])

    rel_posix = _to_rel_posix(json_path, file_path)
    entry_name = name or Path(rel_posix).stem

    # Dubbele entry voorkomen
    for s in scripts:
        if str(s.get("path", "")) == rel_posix:
            return s

    entry = {"name": entry_name, "path": rel_posix, "type": "py"}
    scripts.append(entry)
    data["scripts"] = scripts
    save_json(json_path, data)
    return entry

# [END: register_existing_script]



# [FUNC: create_new_script]
def create_new_script(
    projassist_json: str | Path,
    dir_path: str | Path,
    name: str,
    template: Optional[str] = None,
) -> dict:
    """
logger.debug("create_new_script() called")
    Maak nieuw .py-bestand aan in dir_path (aanmaken indien nodig) en registreer het.
    Retourneert de aangemaakte entry.
    """
    json_path = Path(projassist_json)
    root = json_path.parent.resolve()

    d = Path(dir_path)
    d = d if d.is_absolute() else (root / d)
    d.mkdir(parents=True, exist_ok=True)

    filename = name if name.endswith(".py") else f"{name}.py"
    new_file = d / filename
    if not new_file.exists():
        content = (
            template
            if template is not None
            else f'# {filename}\n\nif __name__ == "__main__":\n    pass\n'
        )
        new_file.write_text(content, encoding="utf-8")

    return register_existing_script(json_path, new_file, name=new_file.stem)

# [END: create_new_script]



# [FUNC: remove_script]
def remove_script(
    projassist_json: str | Path,
    script_path: str | Path,
    delete_from_disk: bool = False,
) -> bool:
    """
logger.debug("remove_script() called")
    Verwijder script uit .projassist.json (en optioneel van schijf).
    - script_path mag absoluut of relatief zijn.
    Retourneert True als JSON gewijzigd werd.
    """
    json_path = Path(projassist_json)
    data = load_json(json_path)
    scripts = data.get("scripts", [])

    rel_posix = _to_rel_posix(json_path, script_path)
    new_scripts = [s for s in scripts if str(s.get("path", "")) != rel_posix]
    changed = len(new_scripts) != len(scripts)

    if changed:
        data["scripts"] = new_scripts
        save_json(json_path, data)

    if delete_from_disk:
        root = json_path.parent.resolve()
        abs_path = (root / Path(rel_posix)).resolve()
        try:
            if abs_path.exists() and abs_path.is_file():
                abs_path.unlink()
        except Exception:
            # Stil falen: best effort verwijderen
            pass

    return changed

# [END: remove_script]
logger.debug("_build_github_blob_url() called")



# [FUNC: _build_github_blob_url]
def _build_github_blob_url(repo_url: str, rel_posix: str, branch: str = "main") -> str:
    url = repo_url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    return f"{url}/blob/{branch}/{rel_posix}"

# [END: _build_github_blob_url]



# [FUNC: set_github_url_for_script]
def set_github_url_for_script(
    projassist_json: str | Path,
    script_path: str | Path,
    logger.debug("set_github_url_for_script() called")
    branch: str = "main",
) -> str | None:
    """
    Zet scripts[i].github_url op basis van top-level 'github_repo'.
    Retourneert de URL of None als repo ontbreekt of entry niet gevonden is.
    """
    json_path = Path(projassist_json)
    data = load_json(json_path)
    repo = data.get("github_repo")
    if not repo:
        return None

    rel_posix = _to_rel_posix(json_path, script_path)
    scripts = data.get("scripts", [])
    for s in scripts:
        if str(s.get("path", "")) == rel_posix:
            url = _build_github_blob_url(repo, rel_posix, branch=branch)
            s["github_url"] = url
            save_json(json_path, data)
            return url
    return None

# [END: set_github_url_for_script]

