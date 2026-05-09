"""Load credentials from config/llm_api.toml into env vars.

Search order for the TOML file:
  1. $LLM_API_TOML if set
  2. ./config/llm_api.toml (cwd-relative)
  3. <repo_root>/config/llm_api.toml (project root next to scripts/, src/)
  4. <git_common_dir>/../config/llm_api.toml (handles git worktrees:
     the file in the main repo's config/ is reused when running from a worktree
     that does not have its own copy.)

Recognized [llm] keys: api_key, base_url, model, judge_model.
The first source that defines a key wins; missing env vars are filled, but
existing env vars are NOT overwritten so .env / shell stay authoritative.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def _git_common_dir() -> Optional[Path]:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    p = Path(out.decode().strip())
    if not p.is_absolute():
        try:
            p = (Path(__file__).resolve().parent / p).resolve()
        except OSError:
            return None
    return p


def candidate_paths() -> list[Path]:
    """All paths that may contain llm_api.toml, in priority order."""
    paths: list[Path] = []
    env = os.environ.get("LLM_API_TOML", "").strip()
    if env:
        paths.append(Path(env))
    paths.append(Path.cwd() / "config" / "llm_api.toml")
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    paths.append(repo_root / "config" / "llm_api.toml")
    gcd = _git_common_dir()
    if gcd is not None:
        paths.append(gcd.parent / "config" / "llm_api.toml")
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in paths:
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp in seen:
            continue
        seen.add(rp)
        deduped.append(p)
    return deduped


def _setdefault_env(key: str, value: str) -> None:
    if value and not os.environ.get(key):
        os.environ[key] = value


def load_llm_api_toml() -> Optional[Path]:
    """Read llm_api.toml (if any) and apply [llm] keys as env vars.

    Returns the path of the file that was loaded, or None if none was found.
    Does not raise when no file is found — env / .env may still supply values.
    """
    for path in candidate_paths():
        if not path.is_file():
            continue
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        llm = data.get("llm") or {}
        api_key = str(llm.get("api_key") or "").strip()
        base_url = str(llm.get("base_url") or "").strip()
        model = str(llm.get("model") or "").strip()
        judge_model = str(llm.get("judge_model") or llm.get("model") or "").strip()
        if api_key:
            _setdefault_env("LLMAPI_KEY", api_key)
        if base_url:
            _setdefault_env("OPENAI_BASE_URL", base_url)
        if model:
            _setdefault_env("EVAL_MODEL", model)
        if judge_model:
            _setdefault_env("JUDGE_MODEL", judge_model)
        return path
    return None
