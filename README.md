# AI Agentic Setup

> **An AGENTS.md manager** — a personal AI agentic setup using opencode with SearXNG.

## What is this?

This is a **template-based AGENTS.md manager**. It helps you compose, customize, and deploy `AGENTS.md` files (the system prompt files that steer agent behavior) across your projects using a library of plug-and-play templates.

Features:

- **AGENTS.md template library** — 18+ ready-made templates covering Python, TypeScript, Docker, Chrome DevTools, and more
- **Interactive template selector** — toggle which templates to include in your generated `AGENTS.md`
- **Per-project steering** — generate a tailored `AGENTS.md` for any directory in seconds
- **Full opencode setup** — SearXNG meta search, Chrome DevTools MCP, and pre-configured `opencode.json`

## Installation

### Quick Install (One-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/muntedcrocodile/AI_setup/refs/heads/master/bootstrap.sh | bash
```

This will clone the repository to `~/Applications/AI_setup` and run the install script.

### Manual Install

#### Prerequisites

- Linux (or WSL on Windows)
- [Docker](https://docs.docker.com/engine/install/) - For running SearXNG and Redis containers
- [Bun](https://bun.sh/) - JavaScript runtime for MCP servers
- Chromium based browser - For Chrome DevTools automation

##### Chromium Setup

Install Chromium and create an alias for the start command:

```bash
# Install Chromium (Ubuntu/Debian)
sudo apt update && sudo apt install chromium-browser

# Or on Fedora/RHEL
sudo dnf install chromium

# Add alias to your ~/.bashrc or ~/.zshrc
# Change chromium to whatever ur chromium based browser instanciation command is this might not be required test before implentation
echo 'alias chrome="chromium"' >> ~/.bashrc
source ~/.bashrc
```

1. Clone this repository:
```bash
git clone <repository-url>
cd AI_setup
```

2. Copy opencode configuration:
```bash
mkdir -p ~/.config/opencode
cp opencode.json ~/.config/opencode/
```

3. Set up the systemd service to run Docker Compose automatically:

   **Important:** Edit `docker-compose-applications.service` and change `WorkingDirectory=%h/Applications` to match where you cloned this repository (e.g., `WorkingDirectory=%h/AI_setup`).

```bash
cp docker-compose-applications.service ~/.config/systemd/user/
systemctl --user enable docker-compose-applications.service
systemctl --user start docker-compose-applications.service
```

4. Start the Docker services manually (if not using the systemd service):
```bash
docker compose up -d
```

## Usage

### Quick start: generate an AGENTS.md for any project

Use the **AGENTS.md manager** to compose a tailored `AGENTS.md` from templates:

```bash
# Interactive template picker — generates AGENTS.md in the target directory
make_agent_file <target_directory>

# Example — create AGENTS.md in the current directory
make_agent_file
```

Templates are stored in `make_agents/agents_templates/` with numbered prefixes for ordering. Use the interactive UI to toggle which templates to include. Supports per harness and per llm template management.

Press **Ctrl+E** on a highlighted template to open its file in the configured
editor. Set `editor` in `make_agents/config.yml` to an editor command
(default: `codium`). Arguments are supported, for example `codium --wait` or
`code --reuse-window`; quote executable paths containing
spaces within the command string. The picker reloads when the editor command
returns. If the editor stays open separately, press **Ctrl+R** after saving to
refresh the preview and generated content.

The picker uses two YAML files:

- `make_agents/config.yml`: program settings, such as `editor: codium`.
- `make_agents/metadata.yml`: model providers, model access for each harness,
  template selections, and expanded tree paths.

Edit the `harnesses` section of `metadata.yml` to control which models appear
under each harness. For example:

```yaml
providers:
  default provider:
    - gpt-6-astra
    - minimax m2.5
    - minimax m3
harnesses:
  codex:
    models: [gpt-6-astra]
  opencode:
    models: [minimax m2.5, minimax m3]
```

On startup and refresh, names are discovered from snippet front matter (`llm`
and `harness`). Unregistered models are added under `default provider`; you can
move them into your own provider groups. Newly discovered harnesses start with
the models named in their snippets. After that, each harness's `models` list is
manual: new models require an explicit entry to appear under an existing
harness, and removed entries stay removed. `models: []` hides model-specific
snippets for that harness; snippets with `llm: []` remain available.

The preview displays the snippet's declared harnesses and models above its full
text. Use **Page Up/Page Down** for long previews. **Ctrl+R** reloads both YAML
files and snippet files. Automatic updates preserve YAML comments, provider
assignments, and manual access lists. Selections and expanded paths are saved
in `metadata.yml`. Snippets excluded from every harness are not included in
generated output.

Existing `template_config.json` settings are imported when the corresponding
YAML file does not yet exist. Existing YAML settings take precedence.

### Use the agent

1. Make sure an `AGENTS.md` exists in the directory (generate one above, or copy the default).
2. Run opencode in that directory:
```bash
opencode
```

A useful command if you want VS Code as well is:
```bash
code . && opencode
```
This will open VS Code to the target directory and start the opencode TUI.

### AGENTS.md

The `AGENTS.md` file in this repository serves as the system prompt for the AI agent. It provides steering instructions and context that the agent uses to guide its behavior.

**Important:** Copy `AGENTS.md` to every directory where you instantiate the agent. For example, if you run `opencode` in your home directory (`~`), you need to copy the file to `~/AGENTS.md`.

### Agent Generator

For full control over template selection, use `make_agent_file.py` directly. See the **Quick start** section above.

### General Agentic Usage Advice

- **Project-specific AGENTS.md:** The provided `AGENTS.md` is a template with general steering advice. You are encouraged to add project-specific instructions. Best practice is to only add things you need to tell the agent frequently. For example, if you always need to instruct the agent to perform a certain task, add it to `AGENTS.md` so it doesn't need to be repeated.

- **Keep AGENTS.md short:** A shorter file prevents context bloat and helps the agent stay focused and intelligent.

- **Avoid unnecessary MCPs:** Adding unused MCP servers contributes to context bloat. Consider disabling MCPs you don't need in `opencode.json`.

- **Use `/new` for new tasks:** When starting a new task, use the `/new` command in the opencode TUI to create a fresh session. This helps reduce context bloat from previous conversations.

## Services

The setup includes the following Docker services:

- **Redis** - Cache/database for SearXNG
- **SearXNG** - Private meta search engine (available at http://localhost:1080)

## Configuration

- `opencode.json` - OpenCode configuration with SearXNG and Chrome DevTools MCP servers
- `docker-compose.yml` - Docker services configuration
- `searxng/settings.yml` - SearXNG instance settings