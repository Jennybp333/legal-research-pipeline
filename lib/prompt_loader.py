"""Load Markdown prompt/config files and apply simple `{{VAR}}` substitution."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_VAR_RE = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def load(rel_path: str) -> str:
    """Read a file under the repo root and return its text contents."""
    return repo_path(rel_path).read_text(encoding="utf-8")


def render(template: str, variables: dict[str, str]) -> str:
    """Substitute `{{VAR}}` placeholders. Missing variables become an empty string."""

    def replace(match: re.Match[str]) -> str:
        return variables.get(match.group(1), "")

    return _VAR_RE.sub(replace, template)


def load_and_render(rel_path: str, variables: dict[str, str]) -> str:
    return render(load(rel_path), variables)
