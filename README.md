# AI Agentic Setup

Personal AI agentic setup using opencode with SearXNG search and Chrome DevTools MCP servers.

## Prerequisites

- Linux (or WSL on Windows)
- [Docker](https://docs.docker.com/engine/install/) - For running SearXNG and Redis containers
- [Bun](https://bun.sh/) - JavaScript runtime for MCP servers
- Chromium based browser - For Chrome DevTools automation

### Chromium Setup

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

## Installation

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

1. Navigate to a directory in a terminal and copy the AGENTS.md file to that directory:
```bash
cp /path/to/AI_setup/AGENTS.md .
```

2. Run opencode:
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