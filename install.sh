#!/usr/bin/env bash

################################################################################
# install.sh - Installer for the 'indo' command
#
# Purpose:
#   Installs the 'indo' command (plus an 'in' link) to a suitable directory in your PATH.
#   Can be run locally from the repository or via curl pipe to bash.
#
# Usage:
#   Local:  ./install.sh [--with-skill] [--create-dir] [command_name]
#   Remote: curl -sL https://raw.githubusercontent.com/inevolin/indo-cli/main/install.sh | bash -s -- [--with-skill] [--create-dir] [command_name]
#
#   --create-dir creates DEST_DIR if it does not exist (same as CREATE_DIR=1).
#   Without it, a missing DEST_DIR stops the install with an error.
#   --with-skill also installs the indo Agent Skill to $SKILL_DIR/indo/SKILL.md
#   (default SKILL_DIR: ~/.claude/skills, used by Claude Code and Cursor).
#   For Codex use SKILL_DIR=~/.agents/skills.
#
# What it does:
#   1. Finds a suitable installation directory (checks /usr/local/bin, ~/.local/bin, etc.)
#   2. Creates the directory if it doesn't exist
#   3. Downloads or copies in.sh from the repository
#   4. Makes it executable and installs to chosen directory (may require sudo)
#   5. Warns if the installation directory is not in PATH
################################################################################

set -e  # Exit on any error

REPO_URL="https://raw.githubusercontent.com/inevolin/indo-cli/main/in.sh"
SKILL_URL="https://raw.githubusercontent.com/inevolin/indo-cli/main/skills/indo/SKILL.md"
SOURCE_FILE="./in.sh"

# Options: --with-skill (anywhere), then an optional command name
WITH_SKILL=0
CREATE_DIR="${CREATE_DIR:-0}"
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --with-skill) WITH_SKILL=1 ;;
        --create-dir) CREATE_DIR=1 ;;
        *) ARGS+=("$arg") ;;
    esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

# Default command name is "indo". "in" is a reserved word in Bash and sh, so
# "in * git status" fails there (including "bash -c", which AI agents use).
# Without an argument we also add an "in" link for zsh users and old scripts.
# A custom name (first argument) installs only that name.
if [ -n "${1:-}" ]; then
    COMMAND_NAME="$1"
    ALIAS_NAME=""
else
    COMMAND_NAME="indo"
    ALIAS_NAME="in"
fi

# An explicit DEST_DIR is always used, never replaced by another folder.
# If it does not exist, stop, unless --create-dir (or CREATE_DIR=1) was given.
if [ -n "$DEST_DIR" ]; then
    if [ ! -d "$DEST_DIR" ]; then
        if [ "$CREATE_DIR" != "1" ]; then
            echo "Error: DEST_DIR=$DEST_DIR does not exist. Nothing was installed." >&2
            echo "Create it first (mkdir -p \"$DEST_DIR\"), or run the installer again with --create-dir (or CREATE_DIR=1)." >&2
            exit 1
        fi
        echo "Creating directory: $DEST_DIR"
        if ! mkdir -p "$DEST_DIR" 2>/dev/null; then
            if command -v sudo >/dev/null 2>&1 && sudo mkdir -p "$DEST_DIR"; then
                :
            else
                echo "Error: could not create DEST_DIR=$DEST_DIR. Create it yourself or pick another folder." >&2
                exit 1
            fi
        fi
    fi
    CANDIDATE_DIRS=("$DEST_DIR")
# Otherwise, try reasonable candidate installation directories (in order of preference)
else
    CANDIDATE_DIRS=(
        "/usr/local/bin"
        "$HOME/.local/bin"
        "$HOME/bin"
        "/usr/bin"
    )
fi

# Find the best installation directory
DEST_DIR=""
for dir in "${CANDIDATE_DIRS[@]}"; do
    # Check if directory exists or can be created
    if [ -d "$dir" ]; then
        DEST_DIR="$dir"
        break
    elif [ "$dir" = "$HOME/.local/bin" ] || [ "$dir" = "$HOME/bin" ]; then
        # User directories - can create without sudo
        echo "Creating directory: $dir"
        mkdir -p "$dir"
        DEST_DIR="$dir"
        break
    fi
done

# If no suitable directory found, default to /usr/local/bin and create it
if [ -z "$DEST_DIR" ]; then
    DEST_DIR="/usr/local/bin"
    if [ ! -d "$DEST_DIR" ]; then
        echo "Creating directory: $DEST_DIR (may require sudo)"
        if sudo mkdir -p "$DEST_DIR" 2>/dev/null; then
            echo "Directory created successfully"
        else
            echo "Error: Could not create $DEST_DIR"
            exit 1
        fi
    fi
fi

DEST_FILE="$DEST_DIR/$COMMAND_NAME"
TMP_FILE=$(mktemp 2>/dev/null || echo "/tmp/indo.$$.tmp")

echo "Installing '$COMMAND_NAME' to $DEST_FILE..."

# Download or copy the script
# A local in.sh is used only if it really is indo (not some other in.sh in this folder)
if [ -f "in.sh" ] && grep -qE "inevolin/(in|indo)-cli" in.sh 2>/dev/null; then
    cp in.sh "$TMP_FILE"
else
    echo "Downloading from $REPO_URL..."
    if ! curl -fsSL "$REPO_URL" -o "$TMP_FILE" || ! grep -qE "inevolin/(in|indo)-cli" "$TMP_FILE" 2>/dev/null; then
        rm -f "$TMP_FILE"
        echo "Error: download failed from $REPO_URL. Nothing was installed." >&2
        exit 1
    fi
fi

chmod +x "$TMP_FILE"

# Install to destination (with sudo if needed)
if [ -w "$DEST_DIR" ]; then
    mv "$TMP_FILE" "$DEST_FILE"
else
    echo "Sudo permissions required to install to $DEST_DIR"
    sudo mv "$TMP_FILE" "$DEST_FILE"
fi

echo "Successfully installed '$COMMAND_NAME' to $DEST_FILE!"

# Backward-compatible "in" link (only replaces an older install of this tool)
if [ -n "$ALIAS_NAME" ] && [ "$ALIAS_NAME" != "$COMMAND_NAME" ]; then
    ALIAS_FILE="$DEST_DIR/$ALIAS_NAME"
    if [ -e "$ALIAS_FILE" ] && [ ! -L "$ALIAS_FILE" ] && ! grep -qE "inevolin/(in|indo)-cli" "$ALIAS_FILE" 2>/dev/null; then
        echo "Skipping '$ALIAS_NAME' link: $ALIAS_FILE exists and is not indo."
    else
        if [ -w "$DEST_DIR" ]; then
            ln -sf "$COMMAND_NAME" "$ALIAS_FILE"
        else
            sudo ln -sf "$COMMAND_NAME" "$ALIAS_FILE"
        fi
        echo "Linked '$ALIAS_NAME' -> '$COMMAND_NAME' (works in zsh; in Bash use '$COMMAND_NAME')."
    fi
fi

# Check if the install directory is in PATH
case ":$PATH:" in
    *":$DEST_DIR:"*) IN_PATH=1 ;;
    *) IN_PATH=0 ;;
esac
if [ "$IN_PATH" = "0" ]; then
    echo ""
    echo "⚠️  Warning: $DEST_DIR is not in your PATH"
    echo "To make '$COMMAND_NAME' accessible, follow these steps:"
    echo "1. Add this line to your shell configuration (~/.bashrc, ~/.zshrc, etc.):"
    echo "   export PATH=\"$DEST_DIR:\$PATH\""
    echo "2. Restart your shell or run:"
    echo "   source ~/.bashrc  # or ~/.zshrc"
fi

# Optional Agent Skill for coding agents (Claude Code, Cursor, Codex)
if [ "$WITH_SKILL" = "1" ]; then
    SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills}"
    mkdir -p "$SKILL_DIR/indo"
    if [ -f "skills/indo/SKILL.md" ]; then
        cp "skills/indo/SKILL.md" "$SKILL_DIR/indo/SKILL.md"
    else
        echo "Downloading the indo skill from $SKILL_URL..."
        SKILL_TMP=$(mktemp 2>/dev/null || echo "/tmp/indo-skill.$$.tmp")
        if curl -fsSL "$SKILL_URL" -o "$SKILL_TMP" && grep -q "^name: indo" "$SKILL_TMP"; then
            mv "$SKILL_TMP" "$SKILL_DIR/indo/SKILL.md"
        else
            rm -f "$SKILL_TMP"
            echo "Error: could not download the indo skill from $SKILL_URL." >&2
            exit 1
        fi
    fi
    echo "Installed the indo Agent Skill to $SKILL_DIR/indo/SKILL.md"
fi

echo ""
echo "Try it out: $COMMAND_NAME --help"
