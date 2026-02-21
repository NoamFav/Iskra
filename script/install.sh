#!/usr/bin/env bash

#==============================================================================
# Iskra One-Command Installer
# Usage: curl -fsSL https://your-domain.com/install.sh | bash
#==============================================================================

set -e
trap 'error_exit "Installation failed at line $LINENO"' ERR

#==============================================================================
# Configuration
#==============================================================================

ISKRA_VERSION="1.0.0"
INSTALL_DIR="$HOME/.iskra"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/iskra"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

#==============================================================================
# Helper Functions
#==============================================================================

print_header() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}⚡ Iskra Installation${RESET}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${DIM}Intelligent Git Automation${RESET}"
    echo ""
}

print_step() {
    echo -e "${BLUE}→${RESET} ${BOLD}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}✓${RESET} $1"
}

print_error() {
    echo -e "${RED}✗${RESET} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠${RESET}  $1"
}

print_info() {
    echo -e "${CYAN}ℹ${RESET}  $1"
}

error_exit() {
    print_error "$1"
    echo ""
    print_info "Installation failed. Please check the error above."
    print_info "For help: https://github.com/NoamFav/Iskra/issues"
    exit 1
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

#==============================================================================
# System Detection
#==============================================================================

detect_os() {
    case "$OSTYPE" in
        linux*)        echo "linux" ;;
        darwin*)       echo "macos" ;;
        msys*|cygwin*) echo "windows" ;;
        *)             echo "unknown" ;;
    esac
}

detect_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)  echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        *)             echo "unknown" ;;
    esac
}

#==============================================================================
# Dependency Checking
#==============================================================================

check_dependencies() {
    print_step "Checking dependencies..."
    echo ""

    local missing=0

    # Go 1.21+ is required to build the CLI binary
    if check_command go; then
        local go_version
        go_version=$(go version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        local go_major go_minor
        go_major=$(echo "$go_version" | cut -d. -f1)
        go_minor=$(echo "$go_version" | cut -d. -f2)

        if [ "$go_major" -ge 1 ] && [ "$go_minor" -ge 21 ]; then
            print_success "Go ${go_version}"
        else
            print_error "Go 1.21+ required (found ${go_version})"
            missing=1
        fi
    else
        print_error "Go not found (required to build Iskra)"
        print_info "Install from: https://golang.org/dl/"
        missing=1
    fi

    # Git is required
    if check_command git; then
        local git_version
        git_version=$(git --version | cut -d' ' -f3)
        print_success "Git ${git_version}"
    else
        print_error "Git not found"
        missing=1
    fi

    # Python 3.8+ is optional (only for init/clone/gh subcommands)
    if check_command python3; then
        local py_version
        py_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        local py_major py_minor
        py_major=$(echo "$py_version" | cut -d. -f1)
        py_minor=$(echo "$py_version" | cut -d. -f2)

        if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 8 ]; then
            print_success "Python ${py_version} (for init/clone/gh)"
        else
            print_warning "Python 3.8+ recommended (found $py_version)"
        fi
    else
        print_warning "Python 3 not found — init/clone/gh subcommands will be unavailable"
    fi

    echo ""

    if [ $missing -ne 0 ]; then
        error_exit "Missing required dependencies. Please install Go 1.21+ and Git."
    fi
}

#==============================================================================
# Copy Source Files
#==============================================================================

install_from_source() {
    local repo_dir
    repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    print_step "Installing from source: $repo_dir"

    mkdir -p "$INSTALL_DIR"

    # Copy Go source
    rsync -a --delete "$repo_dir/go-core/" "$INSTALL_DIR/go-core/"

    # Copy Python source (for init/clone/gh)
    rsync -a --delete "$repo_dir/src/" "$INSTALL_DIR/lib/"

    print_success "Copied source files to $INSTALL_DIR"
}

#==============================================================================
# Build Go Binary
#==============================================================================

build_go_binary() {
    print_step "Building Go CLI binary..."

    local src_dir="$INSTALL_DIR/go-core"

    if [ ! -d "$src_dir" ]; then
        error_exit "Go source not found at $src_dir"
    fi

    pushd "$src_dir" > /dev/null
    go mod download || error_exit "Failed to download Go dependencies"
    mkdir -p "$INSTALL_DIR/bin"
    go build -ldflags "-s -w" -o "$INSTALL_DIR/bin/iskra" ./cmd/iskra/ \
        || error_exit "Go build failed"
    popd > /dev/null

    print_success "Built Go binary → $INSTALL_DIR/bin/iskra"
}

#==============================================================================
# Install Binaries
#==============================================================================

install_binaries() {
    print_step "Installing binaries..."

    mkdir -p "$BIN_DIR"

    # Primary binary: the Go CLI
    cp "$INSTALL_DIR/bin/iskra" "$BIN_DIR/iskra"
    chmod +x "$BIN_DIR/iskra"
    print_success "iskra (Go CLI) → $BIN_DIR/iskra"

    # Python backend shim for init/clone/gh (only if Python is available)
    if check_command python3; then
        cat > "$BIN_DIR/iskra-py" << 'EOFWRAPPER'
#!/usr/bin/env python3
"""Python backend for iskra init/clone/gh subcommands."""
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.iskra/lib'))
from iskra.iskra import main
if __name__ == '__main__':
    main()
EOFWRAPPER
        chmod +x "$BIN_DIR/iskra-py"
        print_success "iskra-py (Python backend) → $BIN_DIR/iskra-py"
    fi
}

#==============================================================================
# Install Python Dependencies
#==============================================================================

install_python_deps() {
    if ! check_command python3; then
        return 0
    fi

    print_step "Installing Python dependencies..."

    if check_command pip3; then
        pip3 install --user --quiet \
            rich \
            anthropic \
            gitpython \
            PyYAML \
            requests \
            2>/dev/null \
            && print_success "Python dependencies installed" \
            || print_warning "Failed to install some Python deps (init/clone/gh may be limited)"
    else
        print_warning "pip3 not found — skipping Python dependencies"
    fi
}

#==============================================================================
# PATH Setup
#==============================================================================

setup_path() {
    print_step "Configuring PATH..."

    local shell_rc=""
    local shell_name
    shell_name=$(basename "$SHELL")

    case "$shell_name" in
        bash)
            shell_rc="$HOME/.bashrc"
            [ -f "$HOME/.bash_profile" ] && shell_rc="$HOME/.bash_profile"
            ;;
        zsh)  shell_rc="$HOME/.zshrc" ;;
        fish) shell_rc="$HOME/.config/fish/config.fish" ;;
        *)    shell_rc="$HOME/.profile" ;;
    esac

    local path_line='export PATH="$HOME/.local/bin:$PATH"'

    if [ -f "$shell_rc" ]; then
        if ! grep -q "$HOME/.local/bin" "$shell_rc" 2>/dev/null; then
            echo "" >> "$shell_rc"
            echo "# Added by Iskra installer" >> "$shell_rc"
            echo "$path_line" >> "$shell_rc"
            print_success "Added PATH to $shell_rc"
        else
            print_info "PATH already configured in $shell_rc"
        fi
    else
        print_warning "Could not find shell config file"
        print_info "Add to your shell config: $path_line"
    fi

    export PATH="$BIN_DIR:$PATH"
}

#==============================================================================
# Initial Configuration
#==============================================================================

initialize_config() {
    print_step "Creating configuration..."

    mkdir -p "$CONFIG_DIR/logs"

    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cat > "$CONFIG_DIR/config.yaml" << 'EOFCONFIG'
base_dir: ~/Neoware
config_dir: ~/.config/iskra
max_depth: 3
follow_symlinks: true
exclude_patterns: []
only_patterns: []
default_branch: main
protected_branches:
  - main
  - master
  - production
auto_pull: true
auto_push: true
use_ai_commit: true
commit_message_style: conventional
ai_provider: ollama
require_confirmation: true
require_confirmation_for_protected: true
dry_run: false
show_diff: false
verbose: false
use_rich_ui: true
skip_repos_without_changes: false
skip_repos_ahead_of_remote: false
handle_gitignore: false
remove_ds_store: false
EOFCONFIG
        print_success "Configuration created at $CONFIG_DIR"
    else
        print_info "Configuration already exists (skipped)"
    fi

    [ ! -f "$CONFIG_DIR/repos.json" ] && echo '{}' > "$CONFIG_DIR/repos.json"
}

#==============================================================================
# Verification
#==============================================================================

verify_installation() {
    print_step "Verifying installation..."
    echo ""

    if "$BIN_DIR/iskra" --version >/dev/null 2>&1; then
        local ver
        ver=$("$BIN_DIR/iskra" --version 2>&1 | head -1)
        print_success "iskra: $ver"
    else
        print_error "iskra binary not working"
        return 1
    fi

    echo ""
}

#==============================================================================
# Post-Install
#==============================================================================

show_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}✨ Installation Complete! ✨${RESET}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${BOLD}🚀 Quick Start:${RESET}"
    echo ""
    echo -e "  ${CYAN}1.${RESET} Restart your shell or run:"
    echo -e "     ${DIM}source ~/.zshrc${RESET}  ${DIM}# or ~/.bashrc${RESET}"
    echo ""
    echo -e "  ${CYAN}2.${RESET} Initialize Iskra (track your repos):"
    echo -e "     ${DIM}iskra init${RESET}"
    echo ""
    echo -e "  ${CYAN}3.${RESET} Process all tracked repositories:"
    echo -e "     ${DIM}iskra${RESET}"
    echo ""
    echo -e "${BOLD}📚 Documentation:${RESET}"
    echo -e "  ${DIM}https://github.com/NoamFav/Iskra${RESET}"
    echo ""
    echo -e "${BOLD}🛠  Useful Commands:${RESET}"
    echo ""
    echo -e "  ${CYAN}iskra${RESET}               Auto-commit all tracked repos"
    echo -e "  ${CYAN}iskra status${RESET}        Check repository status"
    echo -e "  ${CYAN}iskra pulse${RESET}         Operate on current repo only"
    echo -e "  ${CYAN}iskra sync${RESET}          Pull + push tracked repos"
    echo -e "  ${CYAN}iskra log${RESET}           Show git history"
    echo -e "  ${CYAN}iskra info${RESET}          Show repo statistics"
    echo -e "  ${CYAN}iskra --dry-run${RESET}     Preview operations"
    echo -e "  ${CYAN}iskra --help${RESET}        Show all options"
    echo ""

    if ! check_command ollama; then
        echo -e "${BOLD}🤖 Enable AI Commits:${RESET}"
        echo -e "  ${DIM}https://ollama.ai${RESET}"
        echo ""
    fi

    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${DIM}Thank you for installing Iskra! ⚡${RESET}"
    echo ""
}

#==============================================================================
# Main
#==============================================================================

main() {
    if [ "$EUID" -eq 0 ]; then
        error_exit "Please do not run this installer as root"
    fi

    print_header
    echo -e "${BOLD}Installing Iskra v${ISKRA_VERSION}${RESET}"
    echo ""

    check_dependencies
    install_from_source
    build_go_binary
    install_binaries
    install_python_deps
    setup_path
    initialize_config
    verify_installation
    show_next_steps
}

main "$@"
