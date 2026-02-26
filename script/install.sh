#!/usr/bin/env bash

#==============================================================================
# Iskra Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/NoamFav/Iskra/main/script/install.sh | bash
#
# Strategy:
#   1. Try to download a pre-built binary from GitHub Releases (no Go needed)
#   2. Fall back to building from source if Go 1.21+ is available
#==============================================================================

set -e
trap 'error_exit "Installation failed at line $LINENO"' ERR

#==============================================================================
# Configuration
#==============================================================================

REPO="NoamFav/Iskra"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/iskra"
TMP_DIR="$(mktemp -d)"

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
# Helpers
#==============================================================================

print_header() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}⚡ Iskra Installer${RESET}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${DIM}Intelligent Git Automation${RESET}"
    echo ""
}

print_step()    { echo -e "${BLUE}→${RESET} ${BOLD}$1${RESET}"; }
print_success() { echo -e "${GREEN}✓${RESET} $1"; }
print_error()   { echo -e "${RED}✗${RESET} $1" >&2; }
print_warning() { echo -e "${YELLOW}⚠${RESET}  $1"; }
print_info()    { echo -e "${CYAN}ℹ${RESET}  $1"; }

check_command() { command -v "$1" >/dev/null 2>&1; }

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

error_exit() {
    print_error "$1"
    echo ""
    print_info "For help: https://github.com/${REPO}/issues"
    exit 1
}

#==============================================================================
# Platform Detection
#==============================================================================

detect_platform() {
    local os arch

    case "$(uname -s)" in
        Linux)  os="linux"  ;;
        Darwin) os="macos"  ;;
        *)      error_exit "Unsupported OS: $(uname -s)" ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)  arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *)             error_exit "Unsupported architecture: $(uname -m)" ;;
    esac

    echo "${os}-${arch}"
}

#==============================================================================
# Strategy 1: Download pre-built binary
#==============================================================================

get_latest_version() {
    if check_command curl; then
        curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
            2>/dev/null | grep '"tag_name"' | cut -d'"' -f4
    elif check_command wget; then
        wget -qO- "https://api.github.com/repos/${REPO}/releases/latest" \
            2>/dev/null | grep '"tag_name"' | cut -d'"' -f4
    fi
}

download_binary() {
    local platform="$1"
    local version="$2"
    local archive="iskra-${version}-${platform}.tar.gz"
    local url="https://github.com/${REPO}/releases/download/${version}/${archive}"

    print_step "Downloading iskra ${version} for ${platform}..."

    if check_command curl; then
        curl -fsSL --progress-bar "$url" -o "${TMP_DIR}/${archive}" || return 1
    elif check_command wget; then
        wget -q --show-progress "$url" -O "${TMP_DIR}/${archive}" || return 1
    else
        return 1
    fi

    tar -xzf "${TMP_DIR}/${archive}" -C "${TMP_DIR}" || return 1

    if [ ! -f "${TMP_DIR}/iskra" ]; then
        return 1
    fi

    mkdir -p "$BIN_DIR"
    mv "${TMP_DIR}/iskra" "$BIN_DIR/iskra"
    chmod +x "$BIN_DIR/iskra"
    print_success "Installed iskra ${version} → ${BIN_DIR}/iskra"
    return 0
}

#==============================================================================
# Strategy 2: Build from source
#==============================================================================

check_go() {
    if ! check_command go; then
        return 1
    fi
    local ver major minor
    ver=$(go version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    [ "$major" -ge 1 ] && [ "$minor" -ge 21 ]
}

build_from_source() {
    # Must be run from the repo directory
    local repo_dir
    repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    print_step "Building from source: ${repo_dir}"

    if [ ! -d "${repo_dir}/go-core" ]; then
        error_exit "go-core/ not found — run this script from the Iskra repo directory"
    fi

    local go_ver
    go_ver=$(go version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    print_success "Go ${go_ver}"

    pushd "${repo_dir}/go-core" > /dev/null
    go mod download || error_exit "Failed to download Go dependencies"

    mkdir -p "$BIN_DIR"
    go build \
        -ldflags "-s -w -X main.version=$(git describe --tags --always 2>/dev/null || echo 'dev')" \
        -o "$BIN_DIR/iskra" \
        ./cmd/iskra/ \
        || error_exit "Go build failed"
    popd > /dev/null

    chmod +x "$BIN_DIR/iskra"
    print_success "Built from source → ${BIN_DIR}/iskra"
}

#==============================================================================
# PATH Setup
#==============================================================================

setup_path() {
    print_step "Configuring PATH..."

    local shell_rc shell_name
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
        if ! grep -q '\.local/bin' "$shell_rc" 2>/dev/null; then
            echo "" >> "$shell_rc"
            echo "# Added by Iskra installer" >> "$shell_rc"
            echo "$path_line" >> "$shell_rc"
            print_success "Added ~/.local/bin to PATH in ${shell_rc}"
        else
            print_info "PATH already configured"
        fi
    else
        print_warning "Could not find shell config — add this manually:"
        print_info "  ${path_line}"
    fi

    export PATH="$BIN_DIR:$PATH"
}

#==============================================================================
# Config
#==============================================================================

initialize_config() {
    print_step "Creating default config..."

    mkdir -p "$CONFIG_DIR"

    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        # Detect a sensible base_dir
        local base_dir="$HOME"
        for candidate in "$HOME/code" "$HOME/projects" "$HOME/dev" "$HOME/src"; do
            if [ -d "$candidate" ]; then
                base_dir="$candidate"
                break
            fi
        done

        cat > "$CONFIG_DIR/config.yaml" << EOFCONFIG
base_dir: ${base_dir}
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
EOFCONFIG
        print_success "Config created at ${CONFIG_DIR}/config.yaml"
        print_info "Edit base_dir to point to your code directory"
    else
        print_info "Config already exists (skipped)"
    fi

    [ ! -f "$CONFIG_DIR/repos.json" ] && echo '{}' > "$CONFIG_DIR/repos.json"
}

#==============================================================================
# Verify
#==============================================================================

verify_installation() {
    print_step "Verifying..."
    echo ""

    if ! "${BIN_DIR}/iskra" --version >/dev/null 2>&1; then
        error_exit "iskra binary not working after install"
    fi

    local ver
    ver=$("${BIN_DIR}/iskra" --version 2>&1 | head -1)
    print_success "${ver}"
    echo ""
}

#==============================================================================
# Summary
#==============================================================================

show_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}✨ Iskra installed!${RESET}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${BOLD}Getting started:${RESET}"
    echo ""
    echo -e "  ${CYAN}1.${RESET} Reload your shell:"
    echo -e "     ${DIM}source ~/.zshrc${RESET}  ${DIM}# or ~/.bashrc${RESET}"
    echo ""
    echo -e "  ${CYAN}2.${RESET} Track your repos:"
    echo -e "     ${DIM}iskra init${RESET}"
    echo ""
    echo -e "  ${CYAN}3.${RESET} Commit everything:"
    echo -e "     ${DIM}iskra${RESET}"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo ""
    echo -e "  ${CYAN}iskra${RESET}                  Auto-commit all tracked repos"
    echo -e "  ${CYAN}iskra status${RESET}           Status across all repos"
    echo -e "  ${CYAN}iskra pulse${RESET}            Commit current repo"
    echo -e "  ${CYAN}iskra pulse switch${RESET}     Switch branches"
    echo -e "  ${CYAN}iskra pulse rebase${RESET}     Guided rebase"
    echo -e "  ${CYAN}iskra info${RESET}             Rich repo stats"
    echo -e "  ${CYAN}iskra gh prs${RESET}           List open PRs"
    echo -e "  ${CYAN}iskra --help${RESET}           All commands"
    echo ""

    if ! check_command ollama; then
        echo -e "${DIM}AI commits use Ollama (optional): https://ollama.ai${RESET}"
        echo ""
    fi

    if ! check_command gh; then
        echo -e "${DIM}GitHub features need gh CLI: https://cli.github.com${RESET}"
        echo ""
    fi

    echo -e "${CYAN}https://github.com/${REPO}${RESET}"
    echo ""
}

#==============================================================================
# Main
#==============================================================================

main() {
    if [ "$EUID" -eq 0 ]; then
        error_exit "Do not run as root"
    fi

    print_header

    # Check git (always required)
    if ! check_command git; then
        error_exit "git is required but not found"
    fi
    print_success "git $(git --version | cut -d' ' -f3)"

    # Optional: gh CLI
    if check_command gh; then
        print_success "gh $(gh --version | head -1 | awk '{print $3}')"
    else
        print_warning "gh CLI not found — iskra gh and iskra clone will be unavailable"
    fi
    echo ""

    local platform
    platform=$(detect_platform)
    print_info "Platform: ${platform}"
    echo ""

    # Try download first
    local installed=false
    local latest_version
    latest_version=$(get_latest_version)

    if [ -n "$latest_version" ]; then
        if download_binary "$platform" "$latest_version"; then
            installed=true
        else
            print_warning "Pre-built binary download failed — falling back to source build"
            echo ""
        fi
    else
        print_warning "Could not fetch latest release info — falling back to source build"
        echo ""
    fi

    # Fall back to source build
    if [ "$installed" = false ]; then
        if check_go; then
            go_ver=$(go version | grep -oE '[0-9]+\.[0-9]+' | head -1)
            print_success "Go ${go_ver} found"
            build_from_source
        else
            echo ""
            print_error "No pre-built binary available and Go 1.21+ not found"
            echo ""
            print_info "Options:"
            print_info "  • Install Go: https://golang.org/dl/"
            print_info "  • Download manually: https://github.com/${REPO}/releases"
            exit 1
        fi
    fi

    setup_path
    initialize_config
    verify_installation
    show_next_steps
}

main "$@"
