#!/home/user/Documents/AI_setup/.venv/bin/python
import json
import os
import subprocess
import sys
from pathlib import Path
import curses
import click

from input_popup import input_popup

SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "agents_templates"
CONFIG_FILE = SCRIPT_DIR / "template_config.json"

DEFAULT_CONFIG = {
    "templates": {}
}

OPENCODE_PROMPT = """Create a new agent template snippet for the AGENTS.md file. 

The template should be a single instruction line that starts with a dash "-".

Examples of existing templates:
000_opencode.md ```md
- An empty message form the use means to continue on
```

006_lazy_llm.md ```md
- Never skip doing something because its hard we want a full working appliction. Never implement mock solutions!!!! NO MOCKS!!
- Don't cheat or take shorcust that will effect the final product take as much time as you need its ok to spend lots of time to solve a complex problem dont feel like u need to cheat in order to complete a task simply keep grinding.
- Before giving up on a particular task or trying to find a quick fix/bypass search the internet for documentationon the original solution before proceeding
- Believe in yourself dont give up just because a task iss hard you are smart and capable and very persistent at achiving the task even if it is very tedious eor difficult
```

Directory context: {directory}

User's description of the template/s they want:
{description}

Please create a concise template/s that captures what the user wants.

The new template/s need to be placed in {directory} as new file/s. This is not a modification to any existing AGENTS.md file but the creation of a new template snippet file that will be a used in the creation of new AGENTS.md files in future. Do nto modify the AGENTS.md file simply create new snippet templates in {directory}
"""


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def get_templates():
    templates = {}
    if TEMPLATES_DIR.exists():
        for f in TEMPLATES_DIR.glob("*.md"):
            templates[f.stem] = f.read_text()
    return templates


def run_opencode_interactive(directory, description):
    directory = os.path.join(directory, "agents_templates")
    prompt = OPENCODE_PROMPT.format(directory=directory, description=description, templates_dir=str(TEMPLATES_DIR))
    subprocess.run(
        ["opencode", "--prompt", prompt],
        cwd=directory,
        check=False
    )


def run_main(target_dir):
    while True:
        stdscr = curses.initscr()
        try:
            result = main(stdscr, target_dir)
        finally:
            try:
                curses.endwin()
            except curses.error:
                pass
        if result != "restart":
            break
        os.execv(sys.executable, [sys.executable, __file__, "select", target_dir])


def main(stdscr, target_dir):
    curses.cbreak()
    curses.noecho()
    stdscr.keypad(True)

    templates = get_templates()
    if not templates:
        stdscr.addstr(0, 0, "No templates found in agents_templates/")
        stdscr.getch()
        return

    config = load_config()
    defaults = config.get("templates", {})

    selected = {name: defaults.get(name, False) for name in templates}

    curses.curs_set(0)
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    current_idx = 0
    template_names = sorted(templates.keys())
    scroll_offset = 0

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        title = f"Select templates for {target_dir}"
        stdscr.addstr(0, 0, title, curses.A_REVERSE)

        max_visible = h - 4
        if max_visible > 0:
            if current_idx < scroll_offset:
                scroll_offset = current_idx
            elif current_idx >= scroll_offset + max_visible:
                scroll_offset = current_idx - max_visible + 1
        scroll_offset = max(0, scroll_offset)

        for i, name in enumerate(template_names):
            y = i - scroll_offset + 2
            if y < 2 or y >= h - 2:
                continue
            prefix = "[x]" if selected[name] else "[ ]"
            attr = curses.A_REVERSE if i == current_idx else curses.A_NORMAL
            stdscr.addstr(y, 0, f" {prefix} {name}", attr)

        stdscr.addstr(h - 2, 0, "Space: toggle | Enter: confirm | Ctrl+S: save defaults | Ctrl+A: add template | Esc: quit", curses.A_DIM)

        key = stdscr.getch()

        if key == 27:
            return
        elif key == ord("\n"):
            break
        elif key == ord(" "):
            selected[template_names[current_idx]] = not selected[template_names[current_idx]]
        elif key == 19:
            config["templates"] = selected
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            stdscr.addstr(h - 3, 0, "Defaults saved!                                          ", curses.A_BOLD)
            stdscr.refresh()
            curses.napms(1000)
        elif key == 1:
            description = input_popup(stdscr, "Add new template")
            if description:
                run_opencode_interactive(str(SCRIPT_DIR), description)
                templates = get_templates()
                template_names = sorted(templates.keys())
                selected = {name: defaults.get(name, False) for name in templates}
                current_idx = 0
                scroll_offset = 0
                return "restart"
        elif key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(template_names) - 1:
            current_idx += 1

    output_lines = []
    for name in sorted(template_names):
        if selected[name]:
            output_lines.append(templates[name].strip())

    output = "# AGENTS\n\n" + "\n\n".join(output_lines) + "\n"
    target_path = Path(target_dir) / "AGENTS.md"
    target_path.write_text(output + "\n")

    print(f"Created {target_path}")
    stdscr.keypad(False)
    return


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(select)


@cli.command()
@click.argument("directory", default=os.getcwd())
@click.pass_context
def select(ctx, directory):
    run_main(directory)


@cli.command()
@click.argument("description", required=False)
def add(description):
    if description:
        run_opencode_interactive(str(SCRIPT_DIR), description)

    while True:
        stdscr = curses.initscr()
        try:
            result = main(stdscr, str(SCRIPT_DIR))
        finally:
            try:
                curses.endwin()
            except curses.error:
                pass
        if result != "restart":
            break
        os.execv(sys.executable, [sys.executable, __file__, "select", str(SCRIPT_DIR)])


if __name__ == "__main__":
    cli()