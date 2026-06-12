"""Template snippet creation backed by opencode.

The actual prompt lives in ``prompt.md`` (project root). It is loaded at
import time so the placeholders are always up to date with the latest
guidance, and then formatted per invocation with the target directory
and the user's natural language description.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_ROOT / "create_template_prompt.md"


def load_prompt_template() -> str:
    """Read the raw prompt markdown used to drive opencode."""
    return PROMPT_FILE.read_text()


def run_opencode_interactive(directory: str, description: str) -> None:
    """Spawn opencode to create new template snippet file(s).

    Parameters
    ----------
    directory:
        Absolute path to the project root. The prompt is told to place
        new files in the ``agents_templates/`` subdirectory.
    description:
        Natural language description of the template/s to create.
    """
    target = os.path.join(directory, "agents_templates")
    prompt = load_prompt_template().format(
        directory=target,
        description=description,
    )
    subprocess.run(
        ["opencode", "--prompt", prompt],
        cwd=target,
        check=False,
    )
