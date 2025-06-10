#!/bin/bash

# ThyWill One-Command Ubuntu Installer
# Usage: curl -sSL https://raw.githubusercontent.com/gulkily/thywill/main/install.sh | bash
# Or: wget -qO- https://raw.githubusercontent.com/gulkily/thywill/main/install.sh | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

header() {
    echo -e "${BOLD}${CYAN}$1${NC}"
}

# Configuration
REPO_URL="https://github.com/gulkily/thywill.git"  # Update this
INSTALL_DIR="$HOME/thywill"
PRODUCTION_DIR="/home/thywill/thywill"

main() {
    header "ThyWill One-Command Ubuntu Installer"
    echo ""
    log "This script will:"
    echo "  ✓ Install all system dependencies"
    echo "  ✓ Clone ThyWill repository"
    echo "  ✓ Set up development environment"
    echo "  ✓ Optionally set up production environment"
    echo ""
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        error "Please don't run this script as root"
        echo "Run as your normal user - it will prompt for sudo when needed"
        exit 1
    fi
    
    # Check Ubuntu version
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        warning "This script is designed for Ubuntu. Proceeding anyway..."
    fi
    
    # Prompt for installation type
    echo "Installation options:"
    echo "1) Development only (recommended for local development)"
    echo "2) Development + Production (sets up systemd service, nginx, etc.)"
    echo "3) Production only (for server deployment)"
    read -p "Choose option (1-3): " install_type
    
    case $install_type in
        1) install_development ;;
        2) install_development && install_production ;;
        3) install_production_only ;;
        *) error "Invalid option"; exit 1 ;;
    esac
}

install_development() {
    header "Installing Development Environment"
    
    # Update system
    log "Updating system packages..."
    sudo apt update
    
    # Install system dependencies
    log "Installing system dependencies..."
    sudo apt install -y \
        python3 python3-pip python3-venv python3-dev \
        git curl sqlite3 build-essential \
        software-properties-common
    
    # Clone repository
    if [ -d "$INSTALL_DIR" ]; then
        log "Directory $INSTALL_DIR already exists, updating..."
        cd "$INSTALL_DIR"
        git pull
    else
        log "Cloning ThyWill repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    # Make CLI executable
    chmod +x thywill
    
    # Run setup
    log "Running ThyWill setup..."
    ./thywill setup
    
    # Install globally
    log "Installing ThyWill CLI globally..."
    ./thywill install
    
    success "Development environment setup complete!"
    echo ""
    echo "You can now use these commands:"
    echo "  thywill start          # Start development server"
    echo "  thywill help           # See all commands"
    echo "  cd $INSTALL_DIR        # Go to project directory"
}

install_production_only() {
    header "Installing Production Environment"
    
    # Check if we should create thywill user
    if [ "$USER" != "thywill" ]; then
        log "Creating thywill user..."
        if ! id "thywill" &>/dev/null; then
            sudo adduser --disabled-password --gecos "" thywill
        fi
        
        # Install to production directory
        install_dir="$PRODUCTION_DIR"
        log "Installing to production directory: $install_dir"
        
        # Create directory and set permissions
        sudo mkdir -p "$install_dir"
        
        # Clone or copy repository
        if [ -d "$INSTALL_DIR" ]; then
            log "Copying from development directory..."
            sudo cp -r "$INSTALL_DIR/." "$install_dir/"
        else
            log "Cloning repository to production directory..."
            sudo git clone "$REPO_URL" "$install_dir"
        fi
        
        sudo chown -R thywill:thywill "$install_dir"
        
        # Switch to thywill user for setup
        log "Switching to thywill user for setup..."
        sudo -u thywill bash -c "cd $install_dir && chmod +x thywill && ./thywill setup"
    else
        # Already thywill user
        install_development
    fi
}

install_production() {
    header "Setting up Production Environment"
    
    # Install nginx if not present
    if ! command -v nginx >/dev/null 2>&1; then
        log "Installing nginx..."
        sudo apt install -y nginx
    fi
    
    # Run production setup
    if [ "$USER" == "thywill" ]; then
        ./thywill setup
    else
        # Set up production user and environment
        install_production_only
    fi
    
    success "Production environment setup complete!"
    echo ""
    echo "Production commands:"
    echo "  sudo systemctl status thywill  # Check service status"
    echo "  thywill health                 # Check application health"
    echo "  thywill deploy                 # Deploy updates"
    echo "  thywill backup daily           # Create backup"
}

cleanup_on_error() {
    error "Installation failed!"
    echo ""
    echo "You can try:"
    echo "1. Re-run the installer"
    echo "2. Check the logs above for specific errors"
    echo "3. Manual installation: git clone $REPO_URL && cd thywill && ./thywill setup"
}

# Set up error handling
trap cleanup_on_error ERR

# Run main installation
main "$@"

echo ""
success "ThyWill installation complete!"
echo ""
echo "Documentation:"
echo "  docs/DEPLOYMENT_WORKFLOW.md   # Deployment guide"
echo "  deployment/DEPLOYMENT_GUIDE.md # Backup and rollback guide"
echo ""
echo "Get started:"
echo "  thywill help                   # See all commands"
echo "  thywill start                  # Start development server"
