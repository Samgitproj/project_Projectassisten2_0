# [SECTION: Imports]
from __future__ import annotations
import sys, json, logging, subprocess
from pathlib import Path
from typing import Optional
from PyQt6 import QtWidgets, QtCore
import os, shutil
from handlers.sync_projassist import SyncProjassistService
from handlers.marker_normalizer import normalize_project

# [END: Imports]
APP_NAME = "Projectassisten2_0"
VENV_PY_EXE = Path(r"C:\virt omgeving\Projectassisten2_0\venv\Scripts\python.exe")


# [CLASS: ProjAssistHandlers]
class ProjAssistHandlers:
# [FUNC: __init__]
    def __init__(self, ui, parent: Optional[QtWidgets.QWidget] = None):
        self.ui = ui
        self.parent = parent
        self.json_path: Optional[Path] = None
        self.json_data: dict = {}
        self.project_root: Optional[Path] = None
        self._connect_signals()
        self._init_ui_defaults()

# [END: __init__]

# [FUNC: _init_ui_defaults]
    def _init_ui_defaults(self):
        if hasattr(self.ui, "plainTextScriptEditor"):
            self.ui.plainTextScriptEditor.setPlainText("")
            self.ui.plainTextScriptEditor.setReadOnly(True)
        for name in ("lblProjectName", "lblProjectName1"):
            w = getattr(self.ui, name, None)
            if w:
                w.setText("—")
        # NIEUW: label voor geselecteerd script resetten
        w = getattr(self.ui, "lblProjectScipt", None)
        if w:
            w.setText("—")
        # nieuwe line-edits leegmaken
        for name in ("lineLoadEditscript", "lineEditDeleteScipt"):
            w = getattr(self.ui, name, None)
            if w:
                w.setText("")

# [END: _init_ui_defaults]

# [FUNC: _connect_signals]
    def _connect_signals(self):
        c = self.ui

        def hook(name, slot):
            w = getattr(c, name, None)
            if not w:
                return
            try:
                w.clicked.disconnect()
            except Exception:
                pass
            w.clicked.connect(slot)

        # Projectbeheer
        hook("btnOpenProjectCreator", self.open_project_creator)
        hook("btnBladerenProject", self._choose_project_folder)
        hook("btnVerwijderProject", self._delete_project_clicked)
        hook("btnOpenGitRepo", self._open_github_repo)

        # Scripts beheren (aanmaken/registreren – ongewijzigd)
        hook("btnBladerenScript", self._choose_new_script_folder)
        hook("btnBrowseScript", self._choose_existing_script_file)
        hook("btnScriptToevoegen", self._create_new_script_clicked)
        hook("btnScriptRegistreren", self._register_existing_script_clicked)

        # NIEUW: één script laden (tab Scripts & JSON)
        hook("BtnBrowseScript", self._browse_load_script_clicked)
        hook("btnLoadScript", self._load_script_to_editor_clicked)

        # NIEUW: één script verwijderen (tab Project)
        hook("btnBrowseDelete", self._browse_delete_script_clicked)
        hook("BtnDeleteScript", self._delete_script_clicked)

        # Export
        hook("btnBrowseProject", self._choose_build_project_path)
        hook("btnBrowseOutput", self._choose_build_output_path)
        hook("btnExportProject", self._export_project_clicked)

        # JSON laden (tab Scripts & JSON)
        hook("btnLoadJson", self._load_json_clicked)

        # NIEUW: markers normaliseren
        hook("btnSetMarkers", self._set_markers_clicked)
        hook("btnMarkProject", self._on_mark_project_clicked)

        # NIEUW: project scripts syncen met .projassist.json
        hook("btnSyncProjassist", self._on_sync_projassist)

# [END: _connect_signals]

# [FUNC: _load_json_clicked]
    def _load_json_clicked(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent,
            "Kies .projassist.json",
            "",
            "ProjectAssist (*.projassist.json);;JSON (*.json)",
        )
        if not path:
            return
        self._load_json(Path(path))

# [END: _load_json_clicked]

# [FUNC: _load_json]
    def _load_json(self, json_path: Path):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as ex:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Fout",
                f"JSON kon niet geladen worden:\n{json_path}\n\n{ex}",
            )
            return
        self.json_path = json_path
        self.json_data = data or {}
        self.project_root = json_path.parent
        name = self.json_data.get("project_name") or self.project_root.name
        if hasattr(self.ui, "lblProjectName"):
            self.ui.lblProjectName.setText(str(name))
        if hasattr(self.ui, "lblProjectName1"):
            self.ui.lblProjectName1.setText(str(name))

        # NIEUW: bij nieuw project nog geen script gekozen → label resetten
        w = getattr(self.ui, "lblProjectScipt", None)
        if w:
            w.setText("—")

# [END: _load_json]

# [FUNC: _browse_load_script_clicked]
    def _browse_load_script_clicked(self):
        start_dir = str(self.project_root or "")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent,
            "Kies script om te laden",
            start_dir,
            "Python/Ui (*.py *.ui);;Alle (*.*)",
        )
        if not path:
            return
        le = getattr(self.ui, "lineLoadEditscript", None)
        if le:
            le.setText(path)

# [END: _browse_load_script_clicked]

# [FUNC: _load_script_to_editor_clicked]
    def _load_script_to_editor_clicked(self):
        le = getattr(self.ui, "lineLoadEditscript", None)
        path = Path(le.text().strip()) if le else None
        label = getattr(self.ui, "lblProjectScipt", None)
        if not path or not path.exists():
            QtWidgets.QMessageBox.information(
                self.parent, "Laden", "Geen geldig script geselecteerd."
            )
            # NIEUW: bij fout ook label leegmaken
            if label:
                label.setText("—")
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as ex:
            text = f"[Kon bestand niet lezen]\n{path}\n\n{ex}"
        if hasattr(self.ui, "plainTextScriptEditor"):
            self.ui.plainTextScriptEditor.setPlainText(text)
        # NIEUW: na succesvol laden → bestandsnaam tonen in het label
        if label:
            label.setText(path.name)

# [END: _load_script_to_editor_clicked]

# [FUNC: _browse_delete_script_clicked]
    def _browse_delete_script_clicked(self):
        start_dir = str(self.project_root or "")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent,
            "Kies script om te verwijderen",
            start_dir,
            "Python/Ui (*.py *.ui);;Alle (*.*)",
        )
        if not path:
            return
        le = getattr(self.ui, "lineEditDeleteScipt", None)  # let op: objectName exact
        if le:
            le.setText(path)

# [END: _browse_delete_script_clicked]

# [FUNC: _delete_script_clicked]
    def _delete_script_clicked(self):
        le = getattr(self.ui, "lineEditDeleteScipt", None)
        abs_path = Path(le.text().strip()) if le else None
        if not abs_path:
            QtWidgets.QMessageBox.information(
                self.parent, "Verwijderen", "Geen script geselecteerd."
            )
            return
        if not abs_path.exists():
            QtWidgets.QMessageBox.information(
                self.parent, "Verwijderen", f"Bestand bestaat niet:\n{abs_path}"
            )
            return
        if (
            QtWidgets.QMessageBox.question(
                self.parent, "Bevestigen", f"Script verwijderen?\n\n{abs_path}"
            )
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return

        # 1) fysiek bestand verwijderen (OneDrive path is ook gewoon een pad)
        try:
            abs_path.unlink(missing_ok=True)
        except Exception as ex:
            QtWidgets.QMessageBox.critical(
                self.parent, "Verwijderen", f"Kon bestand niet verwijderen:\n{ex}"
            )
            return

        # 2) git: deletion commit + push
        try:
            self._git_record([abs_path], f"Remove script: {abs_path.name}")
        except Exception:
            pass

        # 3) JSON bijwerken
        msg_json = "Geen .projassist.json geladen; JSON niet aangepast."
        if self.json_path:
            try:
                from services.script_ops import remove_script

                removed = remove_script(
                    self.json_path, abs_path, delete_from_disk=False
                )
                self._load_json(self.json_path)  # state verversen
                msg_json = (
                    "Uit JSON verwijderd." if removed else "Niet gevonden in JSON."
                )
            except Exception as ex:
                msg_json = f"Kon JSON niet bijwerken: {ex}"

        QtWidgets.QMessageBox.information(
            self.parent, "Script", f"Script verwijderd.\n{msg_json}"
        )
        if le:
            le.setText("")

# [END: _delete_script_clicked]

# [FUNC: _set_markers_clicked]
    def _set_markers_clicked(self):
        # Haal geselecteerd script op uit jouw bestaande veld (zelfde als load)
        le = getattr(self.ui, "lineLoadEditscript", None)
        path = Path(le.text().strip()) if le else None
        if not path or not path.exists():
            QtWidgets.QMessageBox.information(
                self.parent, "Markers", "Geen geldig script geselecteerd."
            )
            return

        # Veiligheidsnet: project_root is nodig voor backup-pad
        project_root = self.project_root

        # Voer normalisatie uit
        try:
            from handlers.marker_normalizer import normalize_markers

            logs = normalize_markers(
                path,
                project_root=project_root,
                git_callback=lambda paths, msg: self._git_record(paths, msg),
            )
            # Toon pop-up met de stappen
            QtWidgets.QMessageBox.information(self.parent, "Markers", "\n".join(logs))
        except Exception as ex:
            QtWidgets.QMessageBox.critical(self.parent, "Markers", f"Fout:\n{ex}")

# [END: _set_markers_clicked]

# [FUNC: _on_sync_projassist]
    def _on_sync_projassist(self):
        if not self.project_root or not self.json_path:
            QtWidgets.QMessageBox.information(
                self.parent, "Sync", "Laad eerst een .projassist.json (project)."
            )
            return

        svc = SyncProjassistService(
            project_root=self.project_root,
            json_path=self.json_path,
            parent_window=self.parent,  # <-- was self.window
        )
        svc.run()

# [END: _on_sync_projassist]

# [FUNC: _on_mark_project_clicked]
    def _on_mark_project_clicked(self):
        if not self.project_root or not self.json_path:
            QtWidgets.QMessageBox.information(
                self.parent, "Markers", "Laad eerst een .projassist.json (project)."
            )
            return
        # Eén commit aan het einde
        normalize_project(
            project_root=self.project_root,
            json_path=self.json_path,
            parent=self.parent,
            commit_to_git=True,
        )

# [END: _on_mark_project_clicked]

# [FUNC: _choose_project_folder]
    def _choose_project_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Kies projectfolder"
        )
        if folder and hasattr(self.ui, "lineProjectFolder"):
            self.ui.lineProjectFolder.setText(folder)

# [END: _choose_project_folder]

# [FUNC: _delete_project_clicked]
    def _delete_project_clicked(self):
        r"""
        Verwijdert project zoals in MainCodeAssist:
        1) .git forceren te wissen
        2) (optioneel) GitHub repo verwijderen met 'Authorization: token <PAT>'
        3) Projectmap wissen
        4) (optioneel) venv-root wissen: C:\virt omgeving\<projectnaam>
        """
        import os, shutil, subprocess, json
        from pathlib import Path
        from PyQt6 import QtWidgets
        import requests
        from dotenv import load_dotenv

        # 0) Pad en bevestigingen
        folder_line = getattr(self.ui, "lineProjectFolder", None)
        chosen = folder_line.text().strip() if folder_line else ""
        if not chosen or not Path(chosen).is_dir():
            QtWidgets.QMessageBox.warning(
                self.parent, "Ongeldig pad", "Selecteer een geldige projectmap."
            )
            return

        root = Path(chosen).resolve()
        meta_path = root / ".projassist.json"
        if not meta_path.exists():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Verwijderen",
                "Beveiliging: geen .projassist.json in deze map.",
            )
            return

        if (
            QtWidgets.QMessageBox.question(
                self.parent,
                "Bevestigen",
                f"Weet je zeker dat je het volledige project wilt verwijderen?\n\n{root}",
            )
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return

        # project_name + github_url uitlezen
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
        project_name = str(meta.get("project_name") or root.name)
        github_url = meta.get("github_repo")

        # extra vragen: venv + github
        venv_root = Path(r"C:\virt omgeving") / project_name
        del_venv = (
            QtWidgets.QMessageBox.question(
                self.parent,
                "Venv verwijderen",
                f"Ook de venv verwijderen?\n{venv_root}",
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        )
        gh_target = (
            github_url or f"https://github.com/Samgitproj/project_{project_name}"
        )
        del_gh = (
            QtWidgets.QMessageBox.question(
                self.parent,
                "GitHub verwijderen",
                f"Ook de GitHub-repo verwijderen?\n{gh_target}",
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        )

        fouten = []

        # 1) .git forceren te wissen (zoals in MainCodeAssist)
        git_dir = root / ".git"
        if git_dir.exists():
            try:
                shutil.rmtree(git_dir, onerror=self._on_rm_error)
            except Exception as e:
                fouten.append(f"⚠️ .git-map niet verwijderd via Python: {e}")
                try:
                    ps = f'Remove-Item -LiteralPath "{git_dir}" -Recurse -Force'
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps], check=True
                    )
                except Exception as ps_e:
                    fouten.append(
                        f"❌ Fallback via PowerShell mislukt voor .git: {ps_e}"
                    )

        # 2) GitHub repo verwijderen met header 'Authorization: token <PAT>' (identiek aan MainCodeAssist)
        if del_gh:
            try:
                load_dotenv()  # zelfde als MainCodeAssist
                token = os.getenv("GITHUB_TOKEN")
                owner = "Samgitproj"
                repo = f"project_{project_name}"
                url = f"https://api.github.com/repos/{owner}/{repo}"
                if not token:
                    fouten.append("❌ Geen GITHUB_TOKEN gevonden in omgeving/.env.")
                else:
                    headers = {
                        "Authorization": f"token {token}",  # <— belangrijk: 'token', niet 'Bearer'
                        "Accept": "application/vnd.github+json",
                    }
                    r = requests.delete(url, headers=headers, timeout=30)
                    if r.status_code == 204:
                        pass  # succes
                    elif r.status_code == 404:
                        fouten.append(
                            "⚠️ GitHub-repo niet gevonden (misschien al verwijderd)."
                        )
                    elif r.status_code == 403:
                        fouten.append(
                            "❌ Verboden (403) — token scopes onvoldoende? Vereist: delete_repo."
                        )
                    else:
                        fouten.append(
                            f"❌ GitHub-delete onverwachte status: {r.status_code}"
                        )
            except Exception as ex:
                fouten.append(f"❌ GitHub-delete fout: {ex}")

        # 3) Projectmap wissen
        try:
            if root.exists():
                shutil.rmtree(root, onerror=self._on_rm_error)
        except Exception as e:
            fouten.append(f"❌ Kon projectmap niet verwijderen: {e}")

        # 4) Venv-root wissen (zoals in MainCodeAssist: hele map '<venv_base>\\<project_name>')
        if del_venv:
            try:
                if venv_root.exists():
                    shutil.rmtree(venv_root, onerror=self._on_rm_error)
            except Exception as e:
                fouten.append(f"❌ Kon virtuele omgeving niet verwijderen: {e}")

        # Slotcontrole/feedback (zelfde stijl)
        if root.exists():
            fouten.append("❌ Projectmap bestaat nog steeds op schijf.")
        if del_venv and venv_root.exists():
            fouten.append("❌ Virtuele omgeving is niet volledig verwijderd.")

        if not fouten:
            QtWidgets.QMessageBox.information(
                self.parent,
                "Verwijderd",
                f"✅ Project '{project_name}' is volledig verwijderd.",
            )
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Fout", "\n".join(fouten))

# [END: _delete_project_clicked]

# [FUNC: _prime_github_token_from_global_env]
    def _prime_github_token_from_global_env(self):
        r"""
        Lees GITHUB_TOKEN / GH_TOKEN uit vaste .env:
        C:\OneDrive\Vioprint\OneDrive - Vioprint\software projecten\Projectassisten2_0\.env
        Zet die in de omgeving vóór GitHub-delete wordt aangeroepen.
        """
        # Als er al een token in de omgeving staat, niets doen
        if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
            return

        env_file = Path(
            r"C:\OneDrive\Vioprint\OneDrive - Vioprint\software projecten\Projectassisten2_0\.env"
        )
        try:
            if not env_file.exists():
                return
            for line in env_file.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if "=" not in line or line.strip().startswith("#"):
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in ("GITHUB_TOKEN", "GH_TOKEN") and v:
                    os.environ.setdefault(k, v)
        except Exception:
            # stil falen – we tonen eventuele fouten via de delete-functie resultaten
            pass

# [END: _prime_github_token_from_global_env]

# [FUNC: _open_github_repo]
    def _open_github_repo(self):
        import webbrowser

        url = self.json_data.get("github_repo") if self.json_data else None
        if (
            not url
            and self.project_root
            and (self.project_root / ".projassist.json").exists()
        ):
            try:
                url = json.loads(
                    (self.project_root / ".projassist.json").read_text(encoding="utf-8")
                ).get("github_repo")
            except Exception:
                url = None
        if url:
            webbrowser.open(url)
        else:
            QtWidgets.QMessageBox.information(
                self.parent, "GitHub", "Geen GitHub-URL gevonden."
            )

# [END: _open_github_repo]

# [FUNC: _choose_new_script_folder]
    def _choose_new_script_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Kies map voor nieuw script"
        )
        if folder and hasattr(self.ui, "lineScriptLocatie"):
            self.ui.lineScriptLocatie.setText(folder)

# [END: _choose_new_script_folder]

# [FUNC: _choose_existing_script_file]
    def _choose_existing_script_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, "Kies bestaand script", "", "Python (*.py);;Alle (*.*)"
        )
        if path and hasattr(self.ui, "lineScriptPad"):
            self.ui.lineScriptPad.setText(path)

# [END: _choose_existing_script_file]

# [FUNC: _create_new_script_clicked]
    def _create_new_script_clicked(self):
        if not self.json_path:
            QtWidgets.QMessageBox.warning(
                self.parent, "Scripts", "Laad eerst een .projassist.json."
            )
            return
        name = (
            getattr(self.ui, "lineScriptNaam", None).text().strip()
            if hasattr(self.ui, "lineScriptNaam")
            else ""
        )
        folder = (
            getattr(self.ui, "lineScriptLocatie", None).text().strip()
            if hasattr(self.ui, "lineScriptLocatie")
            else ""
        )
        if not name or not folder:
            QtWidgets.QMessageBox.warning(
                self.parent, "Scripts", "Naam en locatie zijn verplicht."
            )
            return
        from services.script_ops import create_new_script, set_github_url_for_script

        entry = create_new_script(self.json_path, folder, name)
        filename = name if name.endswith(".py") else f"{name}.py"
        new_file = Path(folder) / filename
        self._git_record([new_file], f"Add script: {entry.get('path')}")
        set_github_url_for_script(self.json_path, new_file, branch="main")
        QtWidgets.QMessageBox.information(
            self.parent, "Script", f"Aangemaakt en geregistreerd: {entry.get('path')}"
        )

# [END: _create_new_script_clicked]

# [FUNC: _register_existing_script_clicked]
    def _register_existing_script_clicked(self):
        if not self.json_path:
            QtWidgets.QMessageBox.warning(
                self.parent, "Scripts", "Laad eerst een .projassist.json."
            )
            return
        path = (
            getattr(self.ui, "lineScriptPad", None).text().strip()
            if hasattr(self.ui, "lineScriptPad")
            else ""
        )
        if not path:
            QtWidgets.QMessageBox.warning(self.parent, "Scripts", "Geen pad opgegeven.")
            return
        from services.script_ops import (
            register_existing_script,
            set_github_url_for_script,
        )

        entry = register_existing_script(self.json_path, path)
        self._git_record([Path(path)], f"Register script: {entry.get('path')}")
        set_github_url_for_script(self.json_path, path, branch="main")
        QtWidgets.QMessageBox.information(
            self.parent, "Script", f"Geregistreerd: {entry.get('path')}"
        )

# [END: _register_existing_script_clicked]

# [FUNC: _choose_build_project_path]
    def _choose_build_project_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Kies projectmap met main.py"
        )
        if folder and hasattr(self.ui, "lineProjectPath"):
            self.ui.lineProjectPath.setText(folder)

# [END: _choose_build_project_path]

# [FUNC: _choose_build_output_path]
    def _choose_build_output_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Kies doelmap voor .exe"
        )
        if folder and hasattr(self.ui, "lineOutputPath"):
            self.ui.lineOutputPath.setText(folder)

# [END: _choose_build_output_path]

# [FUNC: _export_project_clicked]
    def _export_project_clicked(self):
        from build_exe import build_exe

        proj = (
            getattr(self.ui, "lineProjectPath", None).text().strip()
            if hasattr(self.ui, "lineProjectPath")
            else ""
        )
        out = (
            getattr(self.ui, "lineOutputPath", None).text().strip()
            if hasattr(self.ui, "lineOutputPath")
            else ""
        )
        if not proj or not out:
            QtWidgets.QMessageBox.warning(
                self.parent, "Export", "Projectmap en doelmap zijn verplicht."
            )
            return
        ok, msg = build_exe(proj, out, entry_script="main.py")
        QtWidgets.QMessageBox.information(
            self.parent,
            "Export" if ok else "Fout",
            (msg[-2000:] if isinstance(msg, str) else str(msg)),
        )

# [END: _export_project_clicked]

# [FUNC: _git_record]
    def _git_record(self, paths: list[Path | str], message: str):
        try:
            if not self.project_root:
                return
            from services.git_ops import is_repo, add, commit, push

            if not is_repo(self.project_root):
                return
            _ok, _ = add([str(p) for p in paths], cwd=self.project_root)
            _ok2, _out2 = commit(message, cwd=self.project_root)
            try:
                _ok3, _out3 = push(cwd=self.project_root)
            except Exception:
                pass
        except Exception:
            logging.debug("git_record: genegeerde fout", exc_info=True)

# [END: _git_record]

# [FUNC: open_project_creator]
    def open_project_creator(self):
        Ui_MainWindow = None
        try:
            from gui.MainWindow import Ui_MainWindow as _UIMW  # type: ignore

            Ui_MainWindow = _UIMW
        except Exception:
            try:
                from MainWindow import Ui_MainWindow as _UIMW  # type: ignore

                Ui_MainWindow = _UIMW
            except Exception:
                pass
        if Ui_MainWindow is None:
            QtWidgets.QMessageBox.information(
                self.parent, "Project Creator", "MainWindow UI niet beschikbaar."
            )
            return
        win = QtWidgets.QDialog(self.parent)
        ui_creator = Ui_MainWindow()
        ui_creator.setupUi(win)
        if not win.windowTitle():
            win.setWindowTitle("Project Creator")
        try:
            ui_creator.SelectPrjocetFolder.clicked.disconnect()
        except Exception:
            pass
        ui_creator.SelectPrjocetFolder.clicked.connect(
            lambda: self._choose_creator_folder(ui_creator)
        )
        try:
            ui_creator.StartCreateProject.clicked.disconnect()
        except Exception:
            pass
        ui_creator.StartCreateProject.clicked.connect(
            lambda: self._on_start_create_project(win, ui_creator)
        )
        win.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        win.show()

# [END: open_project_creator]

# [FUNC: _choose_creator_folder]
    def _choose_creator_folder(self, ui_creator):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Kies projectbasis"
        )
        if folder:
            ui_creator.ShowProjectFolder.setText(folder)

# [END: _choose_creator_folder]

# [FUNC: _on_start_create_project]
    def _on_start_create_project(self, dlg: QtWidgets.QWidget, ui_creator):
        ui_creator.StartCreateProject.setEnabled(False)
        try:
            self._run_create_project(dlg, ui_creator)
        finally:
            ui_creator.StartCreateProject.setEnabled(True)

# [END: _on_start_create_project]

# [FUNC: _run_create_project]
    def _run_create_project(self, dlg: QtWidgets.QWidget, ui_creator):
        base = ui_creator.ShowProjectFolder.text().strip()
        name = ui_creator.NewProjectNameEdit.text().strip()
        readme = ui_creator.READmeBox.toPlainText().strip()
        if not base or not name:
            QtWidgets.QMessageBox.warning(
                dlg, "Project", "Folder en projectnaam zijn verplicht."
            )
            return
        script = (
            Path(__file__).resolve().parent.parent / "create_project.py"
        ).resolve()
        if not script.exists():
            QtWidgets.QMessageBox.information(
                dlg, "Project", "create_project.py niet gevonden in projectroot."
            )
            return
        py = VENV_PY_EXE if VENV_PY_EXE.exists() else Path(sys.executable)
        args = [str(py), str(script), base, name] + ([readme] if readme else [])
        try:
            proc = subprocess.run(args, capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                QtWidgets.QMessageBox.information(dlg, "Project", "Project aangemaakt.")
            else:
                QtWidgets.QMessageBox.critical(
                    dlg,
                    "Project",
                    f"Fout bij aanmaken:\n\n{proc.stdout}\n{proc.stderr}",
                )
        except Exception as ex:
            QtWidgets.QMessageBox.critical(dlg, "Project", f"Onverwachte fout:\n{ex}")

# [END: _run_create_project]

# [FUNC: _on_rm_error]
    def _on_rm_error(self, func, path, exc_info):
        """Forceer verwijdering van read-only bestanden (Windows) — zelfde idee als 'verwijder_forceer' in MainCodeAssist."""
        import os, stat

        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

# [END: _on_rm_error]

# [FUNC: _prime_github_token_from_dotenv]
    def _prime_github_token_from_dotenv(self, project_root: Path):
        """
        Als GITHUB_TOKEN/GH_TOKEN niet in de omgeving staat, lees het uit project_root/.env
        zodat delete_github_repo kan slagen, ook als de map later gewist wordt.
        """
        if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
            return
        env_file = project_root / ".env"
        try:
            if env_file.exists():
                for line in env_file.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines():
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("GITHUB_TOKEN", "GH_TOKEN") and v:
                        os.environ.setdefault(k, v)
        except Exception:
            pass

# [END: _prime_github_token_from_dotenv]

# [FUNC: _delete_local_venv_variants]
    def _delete_local_venv_variants(self, project_root: Path) -> str:
        r"""
        Probeer ook <project>\.venv en <project>\venv te verwijderen.
        (delete_project pakt al C:\virt omgeving\<project>\venv)
        """
        msgs = []
        for cand in (project_root / ".venv", project_root / "venv"):
            try:
                if cand.exists() and cand.is_dir():
                    shutil.rmtree(cand, ignore_errors=False)
                    msgs.append(f"Extra venv verwijderd: {cand}")
            except Exception as ex:
                msgs.append(f"Extra venv niet verwijderd: {cand} ({ex})")
        return "\n".join(msgs)

# [END: _delete_local_venv_variants]
# [END: ProjAssistHandlers]


