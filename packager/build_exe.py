# [SECTION: Imports]
import sys
import subprocess
from pathlib import Path


# [END: Imports]
# Vast venv-python (zoals afgesproken); valt terug op sys.executable indien niet aanwezig
VENV_PY_EXE = Path(r"C:\virt omgeving\Projectassisten2_0\venv\Scripts\python.exe")


# [FUNC: build_exe]
def build_exe(
    project_path: str | Path, output_dir: str | Path, entry_script: str = "main.py"
) -> tuple[bool, str]:
    """
    Bouw een onefile .exe met PyInstaller.
    - project_path: map die het entry script bevat
    - output_dir: doelmap voor de .exe
    - entry_script: bv. 'main.py'
    Retourneert (ok, gecombineerd stdout/stderr).
    """
    proj = Path(project_path).resolve()
    out = Path(output_dir).resolve()
    script = (proj / entry_script).resolve()

    if not proj.exists() or not proj.is_dir():
        return False, f"Projectmap niet gevonden: {proj}"
    if not script.exists():
        return False, f"Entry script niet gevonden: {script}"

    out.mkdir(parents=True, exist_ok=True)

    py = VENV_PY_EXE if VENV_PY_EXE.exists() else Path(sys.executable)

    cmd = [
        str(py),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--distpath",
        str(out),
        str(script),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ok = proc.returncode == 0
        output = (proc.stdout or "") + (proc.stderr or "")
        return ok, output.strip()[-20000:]  # knip extreem lange logs af
    except Exception as ex:
        return False, f"PyInstaller fout: {ex}"

# [END: build_exe]

