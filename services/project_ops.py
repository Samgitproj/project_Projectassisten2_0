# [SECTION: Imports]
import logging
from pathlib import Path
from shutil import rmtree
import os
import stat



# [END: Imports]
# [FUNC: _on_rm_error]
def _on_rm_error(func, path, exc_info):
    """
    Helper voor rmtree: maak bestand schrijfbaar en probeer opnieuw.
    Voornamelijk nuttig op Windows bij .git/objects.
    """
logger.debug("_on_rm_error() called")
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        # Laat rmtree zelf de fout bubbelen als het écht niet lukt
        pass

# [END: _on_rm_error]



# [FUNC: delete_project]
def delete_project(
    project_root: str | Path,
    delete_venv: bool = True,
    venv_base: str | Path = r"C:\virt omgeving",
) -> tuple[bool, str]:
    """
    Verwijder projectmap (guardrail: .projassist.json moet bestaan).
    Extra: eerst .git forceren te wissen; optioneel ook de venv: <venv_base>/<project_name>/venv.
logger.debug("delete_project() called")
    """
    root = Path(project_root).resolve()

    if not root.exists() or not root.is_dir():
        return False, f"Bestaat niet of is geen map: {root}"
    json_file = root / ".projassist.json"
    if not json_file.exists():
        return False, f"Beveiliging: geen .projassist.json gevonden in {root}"

    # project_name uitlezen vóór verwijderen
    project_name = root.name
    try:
        import json

        project_name = str(
            json.loads(json_file.read_text(encoding="utf-8")).get("project_name")
            or project_name
        )
    except Exception:
        pass

    # 0) .git eerst weg (robuster op Windows)
    try:
        git_dir = root / ".git"
        if git_dir.exists():
            rmtree(git_dir, onerror=_on_rm_error)
    except Exception:
        # Fallback via PowerShell
        try:
            import subprocess

            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Remove-Item -Recurse -Force '{str(git_dir)}'",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            pass

    # 1) projectmap wissen
    try:
        rmtree(root, onerror=_on_rm_error)
        msg = f"Project verwijderd: {root}"
        ok = True
    except Exception as ex:
        return False, f"Verwijderen mislukt: {ex}"

    # 2) gekoppelde venv wissen (optioneel)
    if delete_venv:
        base = Path(venv_base).resolve()
        venv_dir = (base / project_name / "venv").resolve()
        try:
            _ = venv_dir.relative_to(base)  # guardrail binnen base
            if venv_dir.exists() and venv_dir.is_dir():
                rmtree(venv_dir, onerror=_on_rm_error)
                msg += f"\nVenv verwijderd: {venv_dir}"
            else:
                msg += f"\nGeen venv gevonden op: {venv_dir}"
        except Exception as ex:
            msg += f"\nVenv niet verwijderd: {ex}"

    return ok, msg

# [END: delete_project]



# [FUNC: _parse_github_owner_repo]
def _parse_github_owner_repo(url: str) -> tuple[bool, str, str]:
    """
logger.debug("_parse_github_owner_repo() called")
    Parse 'https://github.com/<owner>/<repo>[.git]' → (ok, owner, repo)
    """
    from urllib.parse import urlparse
logger = logging.getLogger(__name__)

    try:
        p = urlparse(url.strip())
        if not p.netloc or "github.com" not in p.netloc.lower():
            return False, "", ""
        parts = [x for x in p.path.strip("/").split("/") if x]
        if len(parts) < 2:
            return False, "", ""
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return True, owner, repo
    except Exception:
        return False, "", ""

# [END: _parse_github_owner_repo]



# [FUNC: delete_github_repo]
def delete_github_repo(
    github_repo_url: str, token: str | None = None
) -> tuple[bool, str]:
logger.debug("delete_github_repo() called")
    """
    Verwijder de GitHub-repo via API. Vereist een PAT in env (GITHUB_TOKEN of GH_TOKEN) of meegegeven token.
    Retourneert (ok, message).
    """
    import os
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    ok, owner, repo = _parse_github_owner_repo(github_repo_url)
    if not ok:
        return False, f"Geen geldige GitHub URL: {github_repo_url}"

    tok = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        return False, "Geen GITHUB_TOKEN/GH_TOKEN gevonden (env)."

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {tok}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Projectassisten2_0",
    }

    try:
        req = Request(api_url, method="DELETE", headers=headers)
        with urlopen(req) as resp:
            # Verwacht 204 No Content
            if resp.status in (200, 202, 204):
                return True, f"GitHub-repo verwijderd: {owner}/{repo}"
            return False, f"Onverwachte status: {resp.status}"
    except HTTPError as e:
        if e.code == 404:
            return False, f"Repo niet gevonden of geen rechten: {owner}/{repo}"
        elif e.code == 403:
            return False, "Verboden (403) — token scopes onvoldoende?"
        return False, f"HTTP fout: {e.code}"
    except URLError as e:
        return False, f"Netwerkfout: {e.reason}"
    except Exception as ex:
        return False, f"Onbekende fout: {ex}"

# [END: delete_github_repo]



logger.debug("_parse_github_owner_repo() called")
# [FUNC: _parse_github_owner_repo]
def _parse_github_owner_repo(url: str) -> tuple[bool, str, str]:
    """
    Parse 'https://github.com/<owner>/<repo>[.git]' → (ok, owner, repo)
    """
    from urllib.parse import urlparse

    try:
        p = urlparse(url.strip())
        if not p.netloc or "github.com" not in p.netloc.lower():
            return False, "", ""
        parts = [x for x in p.path.strip("/").split("/") if x]
        if len(parts) < 2:
            return False, "", ""
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return True, owner, repo
    except Exception:
        return False, "", ""

# [END: _parse_github_owner_repo]



# [FUNC: delete_github_repo]
def delete_github_repo(
    github_repo_url: str | None,
    project_name: str | None = None,
    project_root: str | Path | None = None,
    token: str | None = None,
    default_owner: str = "Samgitproj",
    repo_prefix: str = "project_",
) -> tuple[bool, str]:
    """
        logger.debug("delete_github_repo() called")
    Verwijder de GitHub-repo via API.
    - Als URL gegeven → parse owner/repo.
    - Anders: owner uit .env (GH_OWNER/GITHUB_OWNER) of default_owner;
      repo = f"{repo_prefix}{project_name}"
    Token: uit param, of .env (GITHUB_TOKEN/GH_TOKEN) of process env.
    """
    import os
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    # Token uit .env of env
    if not token:
        # probeer .env in project_root
        env_paths = []
        if project_root:
            pr = Path(project_root)
            env_paths.append(pr / ".env")
        for ep in env_paths:
            try:
                if ep.exists():
                    for line in ep.read_text(
                        encoding="utf-8", errors="ignore"
                    ).splitlines():
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k in ("GITHUB_TOKEN", "GH_TOKEN") and v:
                                token = v
                            if k in ("GH_OWNER", "GITHUB_OWNER") and v:
                                default_owner = v
            except Exception:
                pass
        if not token:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    if not token:
        return False, "Geen GITHUB_TOKEN/GH_TOKEN gevonden (.env of omgeving)."

    # Owner/repo bepalen
    owner, repo = None, None
    if github_repo_url:
        ok, owner, repo = _parse_github_owner_repo(github_repo_url)
        if not ok:
            return False, f"Ongeldige GitHub-URL: {github_repo_url}"
    else:
        if not project_name:
            return (
                False,
                "project_name vereist wanneer geen github_repo_url is opgegeven.",
            )
        owner = default_owner
        repo = f"{repo_prefix}{project_name}"

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Projectassisten2_0",
    }

    try:
        req = Request(api_url, method="DELETE", headers=headers)
        with urlopen(req) as resp:
            if resp.status in (200, 202, 204):
                return True, f"GitHub-repo verwijderd: {owner}/{repo}"
            return False, f"Onverwachte status: {resp.status}"
    except HTTPError as e:
        if e.code == 404:
            return False, f"Repo niet gevonden of geen rechten: {owner}/{repo}"
        if e.code == 403:
            return (
                False,
                "Verboden (403) — token scopes onvoldoende? Vereist: delete_repo",
            )
        return False, f"HTTP fout: {e.code}"
    except URLError as e:
        return False, f"Netwerkfout: {e.reason}"
    except Exception as ex:
        return False, f"Onbekende fout: {ex}"

# [END: delete_github_repo]

