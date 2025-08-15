# [SECTION: Imports]
import logging
import subprocess
from pathlib import Path
logger = logging.getLogger(__name__)



# [END: Imports]
# [FUNC: _run_git]
def _run_git(args: list[str], cwd: str | Path) -> tuple[bool, str]:
    """
    Voer een git-commando uit in `cwd`.
    Retourneert (ok, gecombineerd stdout/stderr).
logger.debug("_run_git() called")
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        ok = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return ok, output.strip()
    except Exception as ex:
        return False, f"git error: {ex}"

# [END: _run_git]



# [FUNC: is_repo]
logger.debug("is_repo() called")
def is_repo(folder: str | Path) -> bool:
    """True als `folder` zich binnen een git repository bevindt."""
    ok, _ = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=folder)
    return ok

# [END: is_repo]



# [FUNC: add]
def add(paths: list[str | Path], cwd: str | Path) -> tuple[bool, str]:
logger.debug("add() called")
    """
    `git add -- <paths>`
    """
    args = ["add", "--"] + [str(p) for p in paths]
    return _run_git(args, cwd=cwd)

# [END: add]



# [FUNC: commit]
def commit(message: str, cwd: str | Path) -> tuple[bool, str]:
logger.debug("commit() called")
    """
    `git commit -m <message>`
    Geeft (True, "Nothing to commit") terug als er niets te committen is.
    """
    ok, out = _run_git(["commit", "-m", message], cwd=cwd)
    if not ok and "nothing to commit" in out.lower():
        return True, "Nothing to commit"
    return ok, out

# [END: commit]

logger.debug("_current_branch() called")


# [FUNC: _current_branch]
def _current_branch(cwd: str | Path) -> tuple[bool, str]:
    """Haal huidige branchnaam op."""
    ok, out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return ok, out

# [END: _current_branch]



# [FUNC: push]
    logger.debug("push() called")
def push(
    cwd: str | Path, remote: str = "origin", branch: str | None = None
) -> tuple[bool, str]:
    """
    `git push <remote> <branch>`; indien branch=None, autodetecteer huidige branch.
    """
    if branch is None:
        ok, out = _current_branch(cwd)
        if not ok:
            return False, out
        branch = out.strip()
    return _run_git(["push", remote, branch], cwd=cwd)

# [END: push]



# [FUNC: rm]
        logger.debug("rm() called")
def rm(
    paths: list[str | Path], cwd: str | Path, cached: bool = False
) -> tuple[bool, str]:
    """
    `git rm [--cached] -- <paths>`
    Handig wanneer je ook uit git-index wil verwijderen bij het wissen van bestanden.
    """
    args = ["rm"]
    if cached:
        args.append("--cached")
    args += ["--"] + [str(p) for p in paths]
    return _run_git(args, cwd=cwd)

# [END: rm]

