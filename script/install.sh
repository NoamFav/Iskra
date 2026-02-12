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
RELEASE_URL="https://github.com/NoamFav/Iskra/releases/download/v${ISKRA_VERSION}"

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
        linux*)   echo "linux" ;;
        darwin*)  echo "macos" ;;
        msys*|cygwin*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

detect_arch() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)   echo "amd64" ;;
        aarch64|arm64)  echo "arm64" ;;
        *)              echo "unknown" ;;
    esac
}

get_platform_suffix() {
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [ "$os" = "unknown" ] || [ "$arch" = "unknown" ]; then
        error_exit "Unsupported platform: $os $arch"
    fi
    
    echo "${os}-${arch}"
}

#==============================================================================
# Dependency Checking
#==============================================================================

check_dependencies() {
    print_step "Checking dependencies..."
    echo ""
    
    local missing=0
    
    # Check Python 3.8+
    if check_command python3; then
        local py_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        local py_major=$(echo "$py_version" | cut -d. -f1)
        local py_minor=$(echo "$py_version" | cut -d. -f2)
        
        if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 8 ]; then
            print_success "Python ${py_version}"
        else
            print_error "Python 3.8+ required (found $py_version)"
            missing=1
        fi
    else
        print_error "Python 3.8+ not found"
        missing=1
    fi
    
    # Check Git
    if check_command git; then
        local git_version=$(git --version | cut -d' ' -f3)
        print_success "Git ${git_version}"
    else
        print_error "Git not found"
        missing=1
    fi
    
    # Optional: Go for AI commits
    if check_command go; then
        print_success "Go (for AI commits)"
    else
        print_warning "Go not found (AI commits disabled)"
        print_info "Install from: https://golang.org/dl/"
    fi
    
    echo ""
    
    if [ $missing -ne 0 ]; then
        error_exit "Missing required dependencies. Please install Python 3.8+ and Git."
    fi
}

#==============================================================================
# Download and Install
#==============================================================================

download_release() {
    print_step "Downloading Iskra v${ISKRA_VERSION}..."
    
    local platform=$(get_platform_suffix)
    local tarball="iskra-${ISKRA_VERSION}-${platform}.tar.gz"
    local download_url="${RELEASE_URL}/${tarball}"
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    if check_command curl; then
        curl -fsSL "$download_url" -o "$tarball" || error_exit "Download failed"
    elif check_command wget; then
        wget -q "$download_url" -O "$tarball" || error_exit "Download failed"
    else
        error_exit "Neither curl nor wget found"
    fi
    
    print_success "Downloaded"
    
    print_step "Extracting..."
    tar -xzf "$tarball" || error_exit "Extraction failed"
    rm "$tarball"
    
    print_success "Extracted to $INSTALL_DIR"
}

install_binaries() {
    print_step "Installing binaries..."
    
    mkdir -p "$BIN_DIR"
    
    # Install Python wrapper scripts
    cat > "$BIN_DIR/iskra" << 'EOFWRAPPER'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.iskra/lib'))
from iskra.iskra import main
if __name__ == '__main__':
    main()
EOFWRAPPER
    
    cat > "$BIN_DIR/iskra-init" << 'EOFWRAPPER'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.iskra/lib'))
from iskra.init import main
if __name__ == '__main__':
    main()
EOFWRAPPER
    
    cat > "$BIN_DIR/iskra-clone" << 'EOFWRAPPER'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.iskra/lib'))
from iskra.clone_repos import main
if __name__ == '__main__':
    main()
EOFWRAPPER
    
    cat > "$BIN_DIR/iskra-gh" << 'EOFWRAPPER'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.iskra/lib'))
from iskra.gh import main
if __name__ == '__main__':
    sys.exit(main())
EOFWRAPPER
    
    # Make executable
    chmod +x "$BIN_DIR/iskra" "$BIN_DIR/iskra-init" "$BIN_DIR/iskra-clone" "$BIN_DIR/iskra-gh"
    
    # Install Go binary if exists
    if [ -f "$INSTALL_DIR/bin/ai_commit" ]; then
        cp "$INSTALL_DIR/bin/ai_commit" "$BIN_DIR/ai_commit"
        chmod +x "$BIN_DIR/ai_commit"
        print_success "Installed ai_commit"
    fi
    
    print_success "Installed to $BIN_DIR"
}

setup_path() {
    print_step "Configuring PATH..."
    
    local shell_rc=""
    local shell_name=$(basename "$SHELL")
    
    case "$shell_name" in
        bash)
            shell_rc="$HOME/.bashrc"
            [ -f "$HOME/.bash_profile" ] && shell_rc="$HOME/.bash_profile"
            ;;
        zsh)
            shell_rc="$HOME/.zshrc"
            ;;
        fish)
            shell_rc="$HOME/.config/fish/config.fish"
            ;;
        *)
            shell_rc="$HOME/.profile"
            ;;
    esac
    
    local path_line='export PATH="$HOME/.local/bin:$PATH"'
    
    if [ -f "$shell_rc" ]; then
        if ! grep -q "$HOME/.local/bin" "$shell_rc" 2>/dev/null; then
            echo "" >> "$shell_rc"
            echo "# Added by Iskra installer" >> "$shell_rc"
            echo "$path_line" >> "$shell_rc"
            print_success "Added to $shell_rc"
        else
            print_info "PATH already configured in $shell_rc"
        fi
    else
        print_warning "Could not find shell config file"
        print_info "Add this to your shell config: $path_line"
    fi
    
    export PATH="$BIN_DIR:$PATH"
}

#==============================================================================
# Initial Configuration
#==============================================================================

initialize_config() {
    print_step "Creating configuration..."
    
    mkdir -p "$CONFIG_DIR/logs"
    
    # Create default config
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
    
    # Create empty repos file
    echo '{}' > "$CONFIG_DIR/repos.json"
    
    print_success "Configuration created at $CONFIG_DIR"
}

#==============================================================================
# Verification
#==============================================================================

verify_installation() {
    print_step "Verifying installation..."
    echo ""
    
    local all_ok=true
    
    if check_command iskra; then
        print_success "iskra command"
    else
        print_error "iskra command not found"
        all_ok=false
    fi
    
    if check_command iskra-init; then
        print_success "iskra-init command"
    else
        print_error "iskra-init command not found"
        all_ok=false
    fi
    
    if check_command iskra-clone; then
        print_success "iskra-clone command"
    else
        print_warning "iskra-clone command not found"
    fi
    
    if check_command iskra-gh; then
        print_success "iskra-gh command"
    else
        print_warning "iskra-gh command not found"
    fi
    
    if check_command ai_commit; then
        print_success "ai_commit command"
    else
        print_warning "ai_commit not available (requires Go)"
    fi
    
    echo ""
    
    if [ "$all_ok" = false ]; then
        print_warning "Some commands not found. Try restarting your shell or run:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
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
    echo -e "     ${DIM}source ~/.bashrc  ${RESET}${DIM}# or ~/.zshrc${RESET}"
    echo ""
    echo -e "  ${CYAN}2.${RESET} Initialize Iskra:"
    echo -e "     ${DIM}iskra-init init${RESET}"
    echo ""
    echo -e "  ${CYAN}3.${RESET} Process repositories:"
    echo -e "     ${DIM}iskra${RESET}"
    echo ""
    echo -e "${BOLD}📚 Documentation:${RESET}"
    echo ""
    echo -e "  ${DIM}https://github.com/NoamFav/Iskra${RESET}"
    echo ""
    echo -e "${BOLD}🛠  Useful Commands:${RESET}"
    echo ""
    echo -e "  ${CYAN}iskra --help${RESET}           Show all options"
    echo -e "  ${CYAN}iskra --status-only${RESET}    Check repository status"
    echo -e "  ${CYAN}iskra --dry-run${RESET}        Preview operations"
    echo -e "  ${CYAN}iskra-init list${RESET}        List tracked repos"
    echo -e "  ${CYAN}iskra-gh prs${RESET}           View pull requests"
    echo ""
    
    if ! check_command ollama; then
        echo -e "${BOLD}🤖 Enable AI Commits:${RESET}"
        echo ""
        echo -e "  Install Ollama for AI-powered commit messages:"
        echo -e "  ${DIM}https://ollama.ai${RESET}"
        echo ""
    fi
    
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "${DIM}Thank you for installing Iskra! ⚡${RESET}"
    echo ""
}

#==============================================================================
# Main Installation Flow
#==============================================================================

main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        error_exit "Please do not run this installer as root"
    fi
    
    print_header
    
    echo -e "${BOLD}Installing Iskra v${ISKRA_VERSION}${RESET}"
    echo ""
    
    # Main steps
    check_dependencies
    download_release
    install_binaries
    setup_path
    initialize_config
    verify_installation
    
    # Show completion
    show_next_steps
}

#==============================================================================
# Run
#==============================================================================

main "$@"