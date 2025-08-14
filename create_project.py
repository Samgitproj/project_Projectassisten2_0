# [SECTION: Imports & Constants]
import os
import shutil
import subprocess
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


# [END: Imports & Constants]
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = "Samgitproj"  # pas aan indien nodig

VENV_ROOT = r"C:\virt omgeving"
COPYFILES_PATH = (
    r"C:\OneDrive\Vioprint\OneDrive - Vioprint\software projecten\CopyFiles"
)


# [FUNC:create_github_repo] START
# [FUNC: create_github_repo]
def create_github_repo(project_name: str) -> str | None:
    """Maak (optioneel) een GitHub-repo. Slaat over als GITHUB_TOKEN ontbreekt."""
    if not GITHUB_TOKEN:
        print("INFO: GITHUB_TOKEN ontbreekt - GitHub stap wordt overgeslagen.")
        return None
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    data = {
        "name": f"project_{project_name}",
        "private": False,
        "auto_init": False,
        "description": f"Repo voor {project_name} aangemaakt via ProjectAssistent",
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 201:
        print(f"OK: GitHub-repo aangemaakt: project_{project_name}")
        return f"https://github.com/{GITHUB_USERNAME}/project_{project_name}.git"
    print(f"ERROR: GitHub-repo aanmaken mislukt: {resp.status_code} {resp.text}")
    return None

# [END: create_github_repo]

# [FUNC:create_github_repo] END


# [FUNC:git_init_and_push] START
# [FUNC: git_init_and_push]
def git_init_and_push(project_path: str, github_repo_url: str):
    try:
        subprocess.run(["git", "init"], cwd=project_path, check=True)
        subprocess.run(["git", "add", "."], cwd=project_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Eerste commit via ProjectAssistent"],
            cwd=project_path,
            check=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", github_repo_url],
            cwd=project_path,
            check=True,
        )
        subprocess.run(["git", "branch", "-M", "main"], cwd=project_path, check=True)
        subprocess.run(
            ["git", "push", "-u", "origin", "main"], cwd=project_path, check=True
        )
        print("OK: Project gepusht naar GitHub")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Fout bij Git push: {e}")

# [END: git_init_and_push]

# [FUNC:git_init_and_push] END


# [FUNC:_write_vscode] START
# [FUNC: _write_vscode]
def _write_vscode(project_path: str, project_name: str, venv_root: str):
    """
    Schrijft .vscode/settings.json en tasks.json (BAT-first + UI2PY-tool + Start_Main).
    """
    vscode_dir = Path(project_path) / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    venv_dir = Path(venv_root) / project_name / "venv"
    interpreter = str(venv_dir / "Scripts" / "python.exe")

    settings = {
        "python.defaultInterpreterPath": interpreter,
        "diffEditor.renderSideBySide": True,
        "diffEditor.ignoreTrimWhitespace": True,
        "diffEditor.experimental.showMoves": True,
        "files.encoding": "utf8",
        "files.eol": "\n",
    }

    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Start Qt Designer (via BAT)",
                "type": "process",
                "command": "${workspaceFolder}\\Start_QT.bat",
                "args": [],
                "options": {"cwd": "${workspaceFolder}"},
                "group": {"kind": "build", "isDefault": True},
                "problemMatcher": [],
            },
            {
                "label": "UI2PY Tool (BAT)",
                "type": "process",
                "command": "C:\\Windows\\System32\\cmd.exe",
                "args": ["/c", "${workspaceFolder}\\Start_UI2PY.bat"],
                "options": {"cwd": "${workspaceFolder}"},
                "presentation": {
                    "reveal": "always",
                    "panel": "dedicated",
                    "clear": True,
                },
                "problemMatcher": [],
            },
            {
                "label": "Start main (BAT)",
                "type": "process",
                "command": "C:\\Windows\\System32\\cmd.exe",
                "args": ["/c", "${workspaceFolder}\\Start_Main.bat"],
                "options": {"cwd": "${workspaceFolder}"},
                "presentation": {
                    "reveal": "always",
                    "panel": "dedicated",
                    "clear": True,
                },
                "problemMatcher": [],
            },
        ],
    }

    (vscode_dir / "settings.json").write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )
    (vscode_dir / "tasks.json").write_text(
        json.dumps(tasks, indent=2), encoding="utf-8"
    )
    print("VS Code settings & tasks geschreven")

# [END: _write_vscode]

# [FUNC:_write_vscode] END


# [FUNC:create_project] START
# [FUNC: create_project]
def create_project(base_folder: str, project_name: str, readme_text: str):
    """
    Maakt een PyQt-project in OneDrive en zet een venv op in C:\\virt omgeving\\<project>\\venv.
    """
    project_path = os.path.join(base_folder, project_name)
    venv_path = os.path.join(VENV_ROOT, project_name)

    # Guard
    if os.path.exists(project_path):
        raise FileExistsError(f"Projectmap '{project_path}' bestaat al.")
    os.makedirs(project_path)

    # Basismappen + __init__.py
    folders = ["core", "documents", "gui", "resources", "backup", ".vscode"]
    for folder in folders:
        full_path = os.path.join(project_path, folder)
        os.makedirs(full_path, exist_ok=True)
        if folder not in (".vscode", "backup"):
            with open(
                os.path.join(full_path, "__init__.py"), "w", encoding="utf-8"
            ) as f:
                f.write("")

    # Basissjablonen (UI → PY moet je zelf nog draaien)
    bestand_inhoud = {
        "main.py": """import logging
import sys
from PyQt6 import QtWidgets, QtCore
try:
    from gui.MainWindow import Ui_MainWindow  # wordt gegenereerd uit .ui
except Exception:
    Ui_MainWindow = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log.txt", mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def main():
    logging.info("main.py gestart")
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    if Ui_MainWindow is None:
        win.setWindowTitle("PyQt app — eerst UI → PY uitvoeren (UI2PY Tool)")
        win.resize(1000, 700)
    else:
        ui = Ui_MainWindow()
        ui.setupUi(win)
        win.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
    win.show()
    sys.exit(app.exec())

# [SECTION: CLI / Entrypoint]
if __name__ == "__main__":
    main()
""",
        os.path.join(
            "gui", "MainWindow.ui"
        ): """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="windowTitle"><string>Nieuwe PyQt App</string></property>
  <property name="geometry"><rect><x>0</x><y>0</y><width>1000</width><height>700</height></rect></property>
  <widget class="QWidget" name="centralwidget">
   <property name="styleSheet">
    <string notr="true">
QGroupBox {
  font-weight: bold;
  border: 1px solid #444;
  border-radius: 6px;
  margin-top: 10px;
}
QGroupBox::title { left: 10px; padding: 0 4px; }
QPushButton { padding: 6px 10px; }
QLineEdit, QTextEdit { padding: 4px; }
    </string>
   </property>
   <layout class="QVBoxLayout" name="verticalLayout">
    <item>
     <widget class="QLabel" name="lblIntro">
      <property name="text"><string>Welkom! Bewerk deze UI in Qt Designer en run daarna UI→PY (UI2PY Tool).</string></property>
     </widget>
    </item>
    <item>
     <widget class="QPushButton" name="btnStart">
      <property name="text"><string>Start</string></property>
     </widget>
    </item>
   </layout>
  </widget>
  <widget class="QMenuBar" name="menubar"/>
  <widget class="QStatusBar" name="statusbar"/>
 </widget>
 <resources/><connections/>
</ui>
""",
        os.path.join("documents", "ProjectStructure.txt"): "",
        os.path.join(
            "documents", "requirements.txt"
        ): "PyQt6==6.9.1\nPyQt6-Qt6==6.9.1\nPyQt6_sip==13.10.2\n",
        "README.md": (
            readme_text.strip() if readme_text else f"# {project_name}\n\nPyQt project."
        ),
    }

    changelogs: list[str] = []
    for rel_path, inhoud in bestand_inhoud.items():
        abs_path = os.path.join(project_path, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(inhoud)
        if rel_path.endswith(".py"):
            name_no_ext = os.path.splitext(os.path.basename(rel_path))[0]
            changelog_path = os.path.join(project_path, f"{name_no_ext}.changelog.txt")
            with open(changelog_path, "w", encoding="utf-8") as ch:
                ch.write("")
            changelogs.append(os.path.basename(changelog_path))

    # CopyFiles compat
    if not os.path.exists(COPYFILES_PATH):
        raise FileNotFoundError(f"De map '{COPYFILES_PATH}' werd niet gevonden.")
    for file in os.listdir(COPYFILES_PATH):
        src = os.path.join(COPYFILES_PATH, file)
        if os.path.isfile(src):
            shutil.copy(src, project_path)

    # Venv maken + requirements installeren
    os.makedirs(venv_path, exist_ok=True)
    subprocess.run(
        ["python", "-m", "venv", os.path.join(venv_path, "venv")], check=True
    )
    venv_requirements = os.path.join(venv_path, "requirements.txt")
    shutil.copy(
        os.path.join(project_path, "documents", "requirements.txt"), venv_requirements
    )
    pip_path = os.path.join(venv_path, "venv", "Scripts", "pip.exe")
    subprocess.run([pip_path, "install", "-r", venv_requirements], check=True)

    # VS Code klaarzetten
    _write_vscode(project_path, project_name, VENV_ROOT)

    # GitHub (optioneel) + config schrijven
    github_repo_url = create_github_repo(project_name)
    github_web_url = github_repo_url.replace(".git", "") if github_repo_url else None

    config_data = {
        "project_name": project_name,
        "profile": "pyqt",
        "project_path": project_path,
        "venv_root": VENV_ROOT,
        "venv_path": str(Path(VENV_ROOT) / project_name / "venv"),
        "vscode_bin": "",
        "github_repo": github_web_url,
        "scripts": [],
        "ui_dir": "gui",
        "resources_dir": "resources",
        "log_file": "log.txt",
        "rules": {
            "auto_changelog": {"enabled": True, "apply_to_new_scripts": True},
            "log_format": "default",
            "backup_on_edit": True,
        },
        "ai_rules": [
            {
                "id": "add_logging",
                "description": "Voeg logging.debug toe aan elke methode",
                "active": True,
                "trigger": "btnAddLoggingAI",
                "prompt": "Voeg logging.debug() toe aan het begin van elke functie om aan te geven welke methode wordt aangeroepen. Gebruik geen andere loggingniveaus tenzij nodig.",
            }
        ],
    }

    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith((".py", ".ui")):
                rel = os.path.relpath(os.path.join(root, file), project_path).replace(
                    "\\", "/"
                )
                entry = {"path": rel}
                if github_web_url:
                    entry["github_url"] = f"{github_web_url}/blob/main/{rel}"
                config_data["scripts"].append(entry)

    if github_web_url:
        config_data["gpt_status_url"] = f"{github_web_url}/raw/main/.projassist.json"

    with open(
        os.path.join(project_path, ".projassist.json"), "w", encoding="utf-8"
    ) as jf:
        json.dump(config_data, jf, indent=2)

    if github_repo_url:
        git_init_and_push(project_path, github_repo_url)

    # Hints
    print("\n=== Project aangemaakt ===")
    print(f"Map: {project_path}")
    print(f"Venv: {Path(VENV_ROOT) / project_name / 'venv'}")
    print("In VS Code:")
    print("  - Task: 'Start Qt Designer (via BAT)'")
    print("  - Task: 'UI2PY Tool (BAT)'  -> GUI .ui -> .py genereren")
    print("  - Task: 'Start main (BAT)'  -> app starten")

# [END: create_project]

# [FUNC:create_project] END


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Gebruik: create_project.py <base_folder> <project_name> [readme_text]")
        sys.exit(1)
    base_folder = sys.argv[1]
    project_name = sys.argv[2]
    readme_text = sys.argv[3] if len(sys.argv) > 3 else ""
    create_project(base_folder, project_name, readme_text)
# [END: CLI / Entrypoint]
