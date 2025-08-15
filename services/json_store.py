# [SECTION: Imports]
import logging
import json
import os
import tempfile
from pathlib import Path
logger = logging.getLogger(__name__)



# [END: Imports]
# [FUNC: load_json]
def load_json(json_path: str | Path) -> dict:
    """
    Laad JSON-bestand. Bestaat het bestand niet of is het onleesbaar → {}.
logger.debug("load_json() called")
    """
    p = Path(json_path)
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Veiligheidsnet: niet crashen op corrupte JSON
        return {}

# [END: load_json]



# [FUNC: save_json]
def save_json(json_path: str | Path, data: dict) -> None:
    """
logger.debug("save_json() called")
    Schrijf JSON atomisch (tempfile + replace), UTF-8, met nette inspringing.
    """
    p = Path(json_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(prefix=p.name, dir=p.parent)
    os.close(fd)
    tmp_path = Path(tmp)

    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, p)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

# [END: save_json]

