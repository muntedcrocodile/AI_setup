#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Add ~/.local/bin to PATH
if ! grep -q 'HOME.*\.local/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
if [ -f "$HOME/.zshrc" ] && ! grep -q 'HOME.*\.local/bin' "$HOME/.zshrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
fi

export PATH="$HOME/.local/bin:$PATH"

# ============ Install Python venv (required for virtual environment) ============
if ! python3 -m venv --help &> /dev/null || ! python3 -m ensurepip --help &> /dev/null; then
    echo "Installing python3-venv and ensurepip..."
    sudo apt update && sudo apt install -y python3-venv python3-full
else
    echo "python3-venv and ensurepip already installed"
fi

# Ensure bun is in PATH
if [ -f "$HOME/.bun/bin/bun" ]; then
    export PATH="$HOME/.bun/bin:$PATH"
fi

# ============ Install Docker (root required) ============
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    rm /tmp/get-docker.sh
else
    echo "Docker already installed"
fi

# Add user to docker group
DOCKER_GROUP_ADDED=false
if ! groups | grep -q docker; then
    echo "Adding user to docker group..."
    sudo usermod -aG docker "$USER"
    DOCKER_GROUP_ADDED=true
else
    echo "User already in docker group"
fi

# Ensure docker service is running
if ! systemctl is-active --quiet docker 2>/dev/null; then
    echo "Starting docker service..."
    sudo systemctl start docker
    sudo systemctl enable docker
else
    echo "Docker service already running"
fi

# ============ Install Bun (user level) ============
if ! command -v bun &> /dev/null; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
else
    echo "Bun already installed"
fi

# Refresh shell to recognize bun
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
fi
if [ -f "$HOME/.profile" ]; then
    source "$HOME/.profile"
fi

# Re-export PATH after shell refresh
if [ -f "$HOME/.bun/bin/bun" ]; then
    export PATH="$HOME/.bun/bin:$PATH"
fi

# ============ Install OpenCode (user level via npm/bun) ============
if ! command -v opencode &> /dev/null; then
    echo "Installing OpenCode..."
    bun add -g opencode-ai 2>/dev/null || true
else
    echo "OpenCode already installed"
fi

# Ensure opencode is in PATH
if [ -f "$HOME/.local/bin/opencode" ]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# ============ Copy OpenCode Config ============
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"
mkdir -p "$OPENCODE_CONFIG_DIR"

if [ -f "$SCRIPT_DIR/opencode.json" ]; then
    # Symlink opencode.json so the installed config always mirrors this repo's
    # single source of truth. If a real file (or broken symlink) is already
    # in place, replace it with a symlink to the repo file.
    if [ -L "$OPENCODE_CONFIG_DIR/opencode.json" ] && [ "$(readlink -f "$OPENCODE_CONFIG_DIR/opencode.json")" = "$(readlink -f "$SCRIPT_DIR/opencode.json")" ]; then
        echo "opencode.json symlink already points to repo"
    else
        if [ -e "$OPENCODE_CONFIG_DIR/opencode.json" ] || [ -L "$OPENCODE_CONFIG_DIR/opencode.json" ]; then
            echo "Replacing existing opencode.json with symlink to repo..."
            rm -f "$OPENCODE_CONFIG_DIR/opencode.json"
        else
            echo "Symlinking opencode.json to config directory..."
        fi
        ln -s "$SCRIPT_DIR/opencode.json" "$OPENCODE_CONFIG_DIR/opencode.json"
    fi
fi

# ============ Set up Systemd User Service ============
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

if [ -f "$SCRIPT_DIR/docker-compose-applications.service" ]; then
    # Update WorkingDirectory to point to actual script location
    sed "s|WorkingDirectory=%h/.*|WorkingDirectory=$SCRIPT_DIR|" "$SCRIPT_DIR/docker-compose-applications.service" > "/tmp/docker-compose-applications.service"

    if [ ! -f "$SYSTEMD_USER_DIR/docker-compose-applications.service" ] || ! diff -q "/tmp/docker-compose-applications.service" "$SYSTEMD_USER_DIR/docker-compose-applications.service" > /dev/null 2>&1; then
        echo "Copying systemd service..."
        cp "/tmp/docker-compose-applications.service" "$SYSTEMD_USER_DIR/"
    else
        echo "systemd service already up to date"
    fi
fi

# Enable and start the systemd user service (idempotent)
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable docker-compose-applications.service 2>/dev/null || true

# Attempt to start containers now via docker group (uses sg if group was just added)
if [ "$DOCKER_GROUP_ADDED" = true ]; then
    sg docker -c "docker compose up -d" 2>/dev/null || true
else
    docker compose up -d 2>/dev/null || true
fi

# ============ Virtual Environment Setup ============
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists"
fi

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing packages..."
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
fi

# ============ Add make_agent_file to PATH ============
if [ -f "$SCRIPT_DIR/make_agents/make_agent_file.py" ]; then
    chmod +x "$SCRIPT_DIR/make_agents/make_agent_file.py"

    # Create symlink in ~/.local/bin if not exists
    # Create ~/.local/bin if it doesn't exist
    mkdir -p "$HOME/.local/bin"

    if [ ! -L "$HOME/.local/bin/make_agent_file" ]; then
        echo "Adding make_agent_file to PATH..."
        ln -sf "$SCRIPT_DIR/make_agents/make_agent_file.py" "$HOME/.local/bin/make_agent_file"
    else
        echo "make_agent_file already in PATH"
    fi
fi


# Refresh shell to recognize other things
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
fi
if [ -f "$HOME/.profile" ]; then
    source "$HOME/.profile"
fi

echo "Setup complete."