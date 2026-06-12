"""Template tree building, navigation, and rendering.

The tree is built dynamically from YAML front matter in each template file.
A template is placed at the deepest level for which it declares metadata:

    harness                            (when only harness is present)
    harness / llm                      (when harness and llm are present)
    harness / llm / language           (when all three are present)

Templates with multiple harnesses / llms / languages are placed in every
combination (their selection state however is unique and shared across
all occurrences).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any, Iterator

import curses
import yaml
import re


INDENT = "  "
EXPANDED_MARKER = "[-]"
COLLAPSED_MARKER = "[+]"
SELECTED_CHECK = "[x]"
UNSELECTED_CHECK = "[ ]"
PARTIAL_CHECK = "[~]"


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_template(content: str) -> tuple[dict[str, Any], str]:
    """Split a template file into (front_matter_dict, body)."""
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return {}, content
    raw, body = match.group(1), match.group(2)
    try:
        meta = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def normalise_meta(meta: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "llm": _as_list(meta.get("llm")),
        "harness": _as_list(meta.get("harness")),
        "language": _as_list(meta.get("language")),
    }


def load_templates(templates_dir: Path) -> dict[str, dict[str, Any]]:
    """Read every template, returning a dict keyed by template stem."""
    templates: dict[str, dict[str, Any]] = {}
    if not templates_dir.exists():
        return templates
    for f in sorted(templates_dir.glob("*.md")):
        raw = f.read_text()
        meta, body = parse_template(raw)
        templates[f.stem] = {
            "path": f,
            "meta": normalise_meta(meta),
            "body": body,
        }
    return templates


@dataclass
class Node:
    """A node in the template tree.

    A node is either a folder (harness, llm, or language grouping) or a
    template leaf. Folders own children; templates do not.
    """

    name: str
    path: str
    level: str
    is_template: bool = False
    template_name: str | None = None
    expanded: bool = False
    parent: "Node | None" = field(default=None, repr=False)
    children: list["Node"] = field(default_factory=list)

    def add_child(self, child: "Node") -> "Node":
        child.parent = self
        self.children.append(child)
        return child

    def sort_recursive(self) -> None:
        """Folders (alphabetical) first, then templates (alphabetical)."""
        self.children.sort(key=lambda c: (c.is_template, c.name.lower()))
        for child in self.children:
            child.sort_recursive()

    def walk(self) -> Iterator["Node"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def collect_template_names(self) -> list[str]:
        """Return all template names in this subtree (duplicates possible)."""
        if self.is_template:
            return [self.template_name] if self.template_name else []
        names: list[str] = []
        for child in self.children:
            names.extend(child.collect_template_names())
        return names

    def folder_selection_state(
        self, selected: dict[str, bool]
    ) -> tuple[bool, bool]:
        """Return ``(all_selected, none_selected)`` for this folder's subtree."""
        names = self.collect_template_names()
        if not names:
            return False, True
        selected_count = sum(1 for n in names if selected.get(n, False))
        return selected_count == len(names), selected_count == 0

    def set_folder_selection(
        self, selected: dict[str, bool], value: bool
    ) -> None:
        for name in self.collect_template_names():
            selected[name] = value

    def toggle_selection(self, selected: dict[str, bool]) -> None:
        if self.is_template:
            if self.template_name:
                selected[self.template_name] = not selected.get(
                    self.template_name, False
                )
            return
        all_sel, _ = self.folder_selection_state(selected)
        self.set_folder_selection(selected, not all_sel)

    def expand(self) -> bool:
        """Expand this folder. Returns True if state changed."""
        if self.is_template or self.expanded:
            return False
        self.expanded = True
        return True

    def collapse(self) -> bool:
        """Collapse this folder. Returns True if state changed."""
        if self.is_template or not self.expanded:
            return False
        self.expanded = False
        return True

    def visible_descendants(self) -> list["Node"]:
        """Return the children visible at the current expansion depth (DFS)."""
        result: list[Node] = []
        for child in self.children:
            result.append(child)
            if not child.is_template and child.expanded:
                result.extend(child.visible_descendants())
        return result

    def _line(self, selected: dict[str, bool]) -> str:
        if self.is_template:
            check = (
                SELECTED_CHECK
                if selected.get(self.template_name, False)
                else UNSELECTED_CHECK
            )
            return f"{check} {self.name}"
        all_sel, none_sel = self.folder_selection_state(selected)
        if all_sel and not none_sel:
            check = SELECTED_CHECK
        elif none_sel and not all_sel:
            check = UNSELECTED_CHECK
        else:
            check = PARTIAL_CHECK
        marker = EXPANDED_MARKER if self.expanded else COLLAPSED_MARKER
        return f"{check} {marker} {self.name}"

    def render_self(
        self,
        stdscr: "curses._CursesWindow",
        y: int,
        depth: int,
        width: int,
        selected: dict[str, bool],
        is_cursor: bool = False,
    ) -> None:
        """Render only this node at (y, 0) with the given indentation.

        Useful when the caller iterates over a flat list of visible nodes
        (e.g. to apply scrolling or to know which node was drawn at a
        given y). For a recursive one-shot render, see
        :meth:`render_tree`.
        """
        line = INDENT * depth + self._line(selected)
        attr = curses.A_REVERSE if is_cursor else curses.A_NORMAL
        try:
            stdscr.addstr(y, 0, line.ljust(width)[:width], attr)
        except curses.error:
            pass

    def render_tree(
        self,
        stdscr: "curses._CursesWindow",
        y: int,
        depth: int,
        width: int,
        selected: dict[str, bool],
        cursor_path: str,
    ) -> int:
        """Recursively render this node and its visible descendants.

        Each node handles rendering itself, then recurses into its
        visible children, returning the next free y position.
        """
        self.render_self(
            stdscr,
            y=y,
            depth=depth,
            width=width,
            selected=selected,
            is_cursor=(self.path == cursor_path),
        )
        y += 1
        if not self.is_template and self.expanded:
            for child in self.children:
                y = child.render_tree(
                    stdscr,
                    y,
                    depth + 1,
                    width,
                    selected,
                    cursor_path,
                )
        return y


class Tree:
    """The full dynamically built template tree."""

    ROOT_LEVEL = "root"

    def __init__(self, templates: dict[str, dict[str, Any]]):
        self.root = Node(name="(root)", path="", level=self.ROOT_LEVEL)
        self.templates = templates
        self._build()

    def _build(self) -> None:
        for name, info in self.templates.items():
            meta = info["meta"]
            harnesses = meta["harness"] or ["general"]
            llms = meta["llm"] or [None]
            languages = meta["language"] or [None]
            for h, l, lang in product(harnesses, llms, languages):
                parts: list[tuple[str, str]] = [("harness", h)]
                if l is not None:
                    parts.append(("llm", l))
                if lang is not None:
                    parts.append(("language", lang))
                cursor = self.root
                current_path = ""
                for idx, (level, value) in enumerate(parts):
                    current_path = (
                        value if idx == 0 else f"{current_path}/{value}"
                    )
                    existing = next(
                        (c for c in cursor.children if c.name == value), None
                    )
                    if existing is None:
                        existing = cursor.add_child(
                            Node(value, current_path, level)
                        )
                    cursor = existing
                leaf = cursor.add_child(
                    Node(name, f"{cursor.path}/{name}", "template")
                )
                leaf.is_template = True
                leaf.template_name = name
        self.root.sort_recursive()

    def all_nodes(self) -> Iterator[Node]:
        """Iterate every node in the tree (including the virtual root)."""
        return self.root.walk()

    def visible_nodes(self) -> list[Node]:
        """Flat list of nodes visible at the current expansion depth."""
        return self.root.visible_descendants()

    def apply_expansion_state(self, expanded_paths: list[str]) -> None:
        expanded_set = set(expanded_paths)
        for node in self.all_nodes():
            if node.is_template:
                continue
            node.expanded = node.path in expanded_set

    def expanded_paths(self) -> list[str]:
        return [
            n.path for n in self.all_nodes() if not n.is_template and n.expanded
        ]

    def render(
        self,
        stdscr: "curses._CursesWindow",
        y: int,
        width: int,
        selected: dict[str, bool],
        cursor_path: str,
    ) -> int:
        """Render the visible tree starting at ``y`` and return the next y.

        The virtual root itself is never drawn; its top-level children are
        rendered at depth 0.
        """
        for child in self.root.children:
            y = child.render_tree(
                stdscr=stdscr,
                y=y,
                depth=0,
                width=width,
                selected=selected,
                cursor_path=cursor_path,
            )
        return y
