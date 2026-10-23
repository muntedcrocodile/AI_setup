#!/bin/bash
set -e

TARGET_DIR="$HOME/Applications/AI_setup"

# Clone repository if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "Cloning AI_setup to $TARGET_DIR..."
    mkdir -p "$HOME/Applications"
    git clone https://github.com/muntedcrocodile/AI_setup.git "$TARGET_DIR"
else
    echo "Repository already exists at $TARGET_DIR"
fi

# Initialize only missing shared skills; preserve other checked-out submodules.
if [ ! -f "$TARGET_DIR/.opencode/skills/tailscale-share/SKILL.md" ]; then
    git -C "$TARGET_DIR" submodule update --init -- .opencode/skills
fi

# Make install.sh executable
chmod +x "$TARGET_DIR/install.sh"

# Run install script
echo "Running install.sh..."
cd "$TARGET_DIR"
./install.sh