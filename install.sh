#!/usr/bin/env bash

#==============================================================================
# Iskra Installation Wizard
# Author: NoamFav
# Description: Interactive installer for Iskra Git automation tool
#==============================================================================

set -e # Exit on error

#==============================================================================
# Colors and Formatting
#==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

#==============================================================================
# Unicode Characters
#==============================================================================

CHECK="✓"
CROSS="✗"
ARROW="→"
STAR="⚡"
ROCKET="🚀"
PACKAGE="📦"
WRENCH="🔧"
SPARKLES="✨"
FOLDER="📁"
BRAIN="🤖"

#==============================================================================
# Configuration
#==============================================================================

REPO_URL="https://github.com/NoamFav/Iskra.git"
INSTALL_DIR="$HOME/.iskra"
CONFIG_DIR="$HOME/.config/iskra"
TEMP_DIR="/tmp/iskra-install-$$"

#==============================================================================
# Helper Functions
#==============================================================================

print_header() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}${STAR} Iskra Installation Wizard${RESET}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${DIM}Intelligent Git Automation with AI-Powered Commits${RESET}"
    echo ""
}

print_step() {
    echo -e "${BLUE}${ARROW}${RESET} ${BOLD}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}${CHECK}${RESET} $1"
}

print_error() {
    echo -e "${RED}${CROSS}${RESET} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${RESET}  $1"
}

print_info() {
    echo -e "${CYAN}ℹ${RESET}  $1"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local response

    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi

    read -p "$(echo -e ${CYAN}?${RESET} $prompt)" response
    response=${response:-$default}

    case "$response" in
    [yY][eE][sS] | [yY]) return 0 ;;
    *) return 1 ;;
    esac
}

ask_input() {
    local prompt="$1"
    local default="$2"
    local response

    if [ -n "$default" ]; then
        prompt="$prompt [$default]: "
    else
        prompt="$prompt: "
    fi

    read -p "$(echo -e ${CYAN}?${RESET} $prompt)" response
    echo "${response:-$default}"
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    while ps -p $pid >/dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

#==============================================================================
# System Detection
#==============================================================================

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

get_python_command() {
    if check_command python3; then
        echo "python3"
    elif check_command python; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

get_pip_command() {
    if check_command pip3; then
        echo "pip3"
    elif check_command pip; then
        echo "pip"
    else
        echo ""
    fi
}

#==============================================================================
# Dependency Checking
#==============================================================================

check_dependencies() {
    print_step "Checking system dependencies..."
    echo ""

    local os=$(detect_os)
    local all_ok=true

    # Check Python
    PYTHON_CMD=$(get_python_command)
    if [ -n "$PYTHON_CMD" ]; then
        local py_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
        print_success "Python: $py_version"
    else
        print_error "Python 3.8+ not found"
        all_ok=false
    fi

    # Check pip
    PIP_CMD=$(get_pip_command)
    if [ -n "$PIP_CMD" ]; then
        print_success "pip: installed"
    else
        print_error "pip not found"
        all_ok=false
    fi

    # Check Git
    if check_command git; then
        local git_version=$(git --version | cut -d' ' -f3)
        print_success "Git: $git_version"
    else
        print_error "Git not found"
        all_ok=false
    fi

    # Check Go
    if check_command go; then
        local go_version=$(go version | cut -d' ' -f3 | sed 's/go//')
        print_success "Go: $go_version"
    else
        print_warning "Go not found (required for AI commits)"
        print_info "Install from: https://golang.org/dl/"
    fi

    # Check Ollama (optional)
    if check_command ollama; then
        print_success "Ollama: installed"
    else
        print_info "Ollama not found (optional, for AI commits)"
        print_info "Install from: https://ollama.ai"
    fi

    # Check GitHub CLI (optional)
    if check_command gh; then
        print_success "GitHub CLI: installed"
    else
        print_info "GitHub CLI not found (optional, for pull-repos)"
        print_info "Install from: https://cli.github.com/"
    fi

    echo ""

    if [ "$all_ok" = false ]; then
        print_error "Missing required dependencies. Please install them and try again."
        echo ""
        print_info "Installation guides:"
        echo "  - Python: https://www.python.org/downloads/"
        echo "  - Git: https://git-scm.com/downloads"
        echo ""
        exit 1
    fi
}

#==============================================================================
# Installation Functions
#==============================================================================

cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

download_iskra() {
    print_step "Downloading Iskra..."

    mkdir -p "$TEMP_DIR"

    if git clone --quiet "$REPO_URL" "$TEMP_DIR" 2>&1 | tee /tmp/git-clone.log >/dev/null; then
        print_success "Downloaded successfully"
    else
        print_error "Failed to download Iskra"
        cat /tmp/git-clone.log
        exit 1
    fi
}

install_python_package() {
    print_step "Installing Iskra Python package..."

    cd "$TEMP_DIR/python"

    if $PIP_CMD install -e . >/tmp/pip-install.log 2>&1; then
        print_success "Iskra installed successfully"
    else
        print_error "Installation failed"
        echo ""
        print_info "Error log:"
        tail -20 /tmp/pip-install.log
        exit 1
    fi
}

verify_installation() {
    print_step "Verifying installation..."
    echo ""

    local all_ok=true

    # Check commands
    if check_command iskra; then
        print_success "iskra command available"
    else
        print_error "iskra command not found"
        all_ok=false
    fi

    if check_command iskra-init; then
        print_success "iskra-init command available"
    else
        print_error "iskra-init command not found"
        all_ok=false
    fi

    if check_command ai_commit; then
        print_success "ai_commit command available"
    else
        print_warning "ai_commit command not found (requires Go)"
    fi

    if check_command pull-repos; then
        print_success "pull-repos command available"
    else
        print_warning "pull-repos command not found"
    fi

    echo ""

    if [ "$all_ok" = false ]; then
        print_warning "Some commands are not available. You may need to add pip install location to PATH."
        echo ""
        print_info "Try adding this to your shell profile (~/.bashrc or ~/.zshrc):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
}

#==============================================================================
# Configuration Setup
#==============================================================================

setup_configuration() {
    print_step "Setting up configuration..."
    echo ""

    # Ask for base directory
    local default_base_dir="$HOME/Projects"
    local base_dir=$(ask_input "Base directory for repositories" "$default_base_dir")

    # Create directory if it doesn't exist
    if [ ! -d "$base_dir" ]; then
        if ask_yes_no "Directory doesn't exist. Create it?"; then
            mkdir -p "$base_dir"
            print_success "Created $base_dir"
        fi
    fi

    # Ask about AI commits
    local use_ai="true"
    if ! ask_yes_no "Enable AI-powered commit messages?" "y"; then
        use_ai="false"
    fi

    # Ask about auto-push
    local auto_push="true"
    if ! ask_yes_no "Automatically push after commits?" "y"; then
        auto_push="false"
    fi

    # Ask about confirmations
    local require_confirmation="true"
    if ! ask_yes_no "Require confirmation before operations?" "y"; then
        require_confirmation="false"
    fi

    echo ""
    print_step "Initializing Iskra..."

    # Run iskra-init
    if check_command iskra-init; then
        iskra-init init --base-dir "$base_dir" -y >/dev/null 2>&1 || true

        # Update config with user preferences
        local config_file="$CONFIG_DIR/config.yaml"
        if [ -f "$config_file" ]; then
            # Simple sed replacements (this assumes the config structure)
            sed -i.bak "s/base_dir: .*/base_dir: $base_dir/" "$config_file" 2>/dev/null || true
            sed -i.bak "s/use_ai_commit: .*/use_ai_commit: $use_ai/" "$config_file" 2>/dev/null || true
            sed -i.bak "s/auto_push: .*/auto_push: $auto_push/" "$config_file" 2>/dev/null || true
            sed -i.bak "s/require_confirmation: .*/require_confirmation: $require_confirmation/" "$config_file" 2>/dev/null || true
            rm -f "$config_file.bak"

            print_success "Configuration saved"
        fi
    fi
}

setup_ollama() {
    if ! check_command ollama; then
        return
    fi

    echo ""
    if ask_yes_no "Setup Ollama for AI commits?" "y"; then
        print_step "Setting up Ollama..."

        # Check if Ollama is running
        if ! pgrep -x "ollama" >/dev/null; then
            print_info "Starting Ollama service..."
            ollama serve >/dev/null 2>&1 &
            sleep 2
        fi

        # Check available models
        print_info "Checking available models..."
        local models=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')

        if [ -z "$models" ]; then
            print_info "No models found. Downloading recommended model..."
            echo ""
            echo -e "${DIM}This may take a few minutes...${RESET}"

            if ollama pull mistral; then
                print_success "Model 'mistral' downloaded successfully"
            else
                print_warning "Failed to download model. You can do this later with: ollama pull mistral"
            fi
        else
            print_success "Found existing models:"
            echo "$models" | while read -r model; do
                echo "  - $model"
            done
        fi
    fi
}

#==============================================================================
# Post-Installation
#==============================================================================

show_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}${SPARKLES} Installation Complete! ${SPARKLES}${RESET}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${BOLD}${ROCKET} Quick Start:${RESET}"
    echo ""
    echo -e "  ${CYAN}1.${RESET} View tracked repositories:"
    echo -e "     ${DIM}\$ iskra-init list${RESET}"
    echo ""
    echo -e "  ${CYAN}2.${RESET} Process all repositories:"
    echo -e "     ${DIM}\$ iskra${RESET}"
    echo ""
    echo -e "  ${CYAN}3.${RESET} Get help:"
    echo -e "     ${DIM}\$ iskra --help${RESET}"
    echo ""
    echo -e "${BOLD}${BRAIN} AI Commits:${RESET}"
    echo ""
    if check_command ollama; then
        echo -e "  ${GREEN}${CHECK}${RESET} Ollama is installed and ready"
        echo -e "  ${DIM}Start using AI commits with: iskra${RESET}"
    else
        echo -e "  ${YELLOW}⚠${RESET}  Install Ollama for AI commit messages:"
        echo -e "     ${DIM}https://ollama.ai${RESET}"
    fi
    echo ""
    echo -e "${BOLD}${FOLDER} Configuration:${RESET}"
    echo ""
    echo -e "  ${DIM}Config dir: $CONFIG_DIR${RESET}"
    echo -e "  ${DIM}Global config: $CONFIG_DIR/config.yaml${RESET}"
    echo -e "  ${DIM}Tracked repos: $CONFIG_DIR/repos.json${RESET}"
    echo ""
    echo -e "${BOLD}${PACKAGE} Useful Commands:${RESET}"
    echo ""
    echo -e "  ${CYAN}iskra --dry-run${RESET}        Preview operations"
    echo -e "  ${CYAN}iskra --status-only${RESET}    Show git status only"
    echo -e "  ${CYAN}iskra --pull${RESET}           Pull before committing"
    echo -e "  ${CYAN}iskra-init add PATH${RESET}    Add a repository"
    echo -e "  ${CYAN}pull-repos${RESET}             Clone GitHub repos"
    echo ""
    echo -e "${BOLD}${WRENCH} Documentation:${RESET}"
    echo ""
    echo -e "  ${DIM}https://github.com/NoamFav/Iskra${RESET}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${DIM}Thank you for installing Iskra! ${STAR}${RESET}"
    echo ""
}

show_error_help() {
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}Installation Failed${RESET}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${BOLD}Common Issues:${RESET}"
    echo ""
    echo -e "  ${YELLOW}1.${RESET} Commands not found after installation:"
    echo -e "     Add pip install location to PATH:"
    echo -e "     ${DIM}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    echo ""
    echo -e "  ${YELLOW}2.${RESET} Permission denied:"
    echo -e "     Try installing with:"
    echo -e "     ${DIM}pip3 install --user -e .${RESET}"
    echo ""
    echo -e "  ${YELLOW}3.${RESET} Go binary build fails:"
    echo -e "     Ensure Go 1.22+ is installed:"
    echo -e "     ${DIM}https://golang.org/dl/${RESET}"
    echo ""
    echo -e "${BOLD}Get Help:${RESET}"
    echo ""
    echo -e "  ${CYAN}GitHub Issues:${RESET} https://github.com/NoamFav/Iskra/issues"
    echo -e "  ${CYAN}Email:${RESET}         noamfav@nf-software.com"
    echo ""
}

#==============================================================================
# Main Installation Flow
#==============================================================================

main() {
    print_header

    echo -e "${BOLD}Welcome to the Iskra installer!${RESET}"
    echo ""
    echo "This wizard will:"
    echo "  • Check system dependencies"
    echo "  • Download and install Iskra"
    echo "  • Configure your preferences"
    echo "  • Setup AI commit integration"
    echo ""

    if ! ask_yes_no "Continue with installation?" "y"; then
        echo ""
        echo "Installation cancelled."
        exit 0
    fi

    echo ""

    # Main installation steps
    check_dependencies
    download_iskra
    install_python_package
    verify_installation
    setup_configuration
    setup_ollama

    # Show completion message
    show_next_steps
}

#==============================================================================
# Run installer
#==============================================================================

if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this installer as root"
    exit 1
fi

main "$@"
