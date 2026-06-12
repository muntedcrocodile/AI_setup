"""Template snippet creation backed by opencode.

The actual prompt lives in ``create_template_prompt.md`` (next to this
file). It is loaded fresh on every invocation so the placeholders are
always up to date with the latest guidance, and then formatted with the
target directory, the user's natural language description, and the list
of LLMs already in use across existing templates.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tree_builder import load_templates

PROJECT_ROOT = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_ROOT / "create_template_prompt.md"
TEMPLATES_DIR = PROJECT_ROOT / "agents_templates"


def load_prompt_template() -> str:
    """Read the raw prompt markdown used to drive opencode."""
    return PROMPT_FILE.read_text()


def discover_available_llms() -> list[str]:
    """Return a sorted, de-duplicated list of LLMs declared in existing
    template front matter. Order is alphabetical so the list opencode
    presents is stable across runs.
    """
    llms: set[str] = set()
    for info in load_templates(TEMPLATES_DIR).values():
        for name in info["meta"].get("llm", []):
            if name:
                llms.add(name)
    return sorted(llms)


def format_llm_list(llms: list[str]) -> str:
    """Render the list of LLMs as a markdown bullet list for the prompt."""
    if not llms:
        return "  (no LLMs are declared in any existing template yet)"
    return "\n".join(f"  - {name}" for name in llms)


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
    available_llms = format_llm_list(discover_available_llms())
    prompt = load_prompt_template().format(
        directory=target,
        description=description,
        available_llms=available_llms,
    )
    subprocess.run(
        ["opencode", "--prompt", prompt],
        cwd=target,
        check=False,
    )
