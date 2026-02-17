#!/bin/bash
#
# SeeWhozThere Service Installation Script
#
# This script installs SeeWhozThere as a systemd service that starts automatically on boot.
# It creates two services:
#   1. seewhozthere.service - Face detection and recognition processor
#   2. seewhozthere-web.service - Web dashboard
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SeeWhozThere Service Installation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}ERROR: Do not run this script as root or with sudo${NC}"
    echo -e "${YELLOW}Run it as your normal user: ./install_service.sh${NC}"
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)
echo -e "${GREEN}Installing for user: ${CURRENT_USER}${NC}"
echo ""

# Update service files with correct paths and user
echo -e "${BLUE}[1/6] Updating service files...${NC}"

# Create temporary service files with correct user and paths
sed "s|User=pi|User=${CURRENT_USER}|g; s|Group=pi|Group=${CURRENT_USER}|g; s|/home/pi/seewhozthere|${SCRIPT_DIR}|g" \
    "${SCRIPT_DIR}/seewhozthere.service" > /tmp/seewhozthere.service

sed "s|User=pi|User=${CURRENT_USER}|g; s|Group=pi|Group=${CURRENT_USER}|g; s|/home/pi/seewhozthere|${SCRIPT_DIR}|g" \
    "${SCRIPT_DIR}/seewhozthere-web.service" > /tmp/seewhozthere-web.service

echo -e "${GREEN}✓ Service files updated${NC}"
echo ""

# Create data directory
echo -e "${BLUE}[2/6] Creating data directory...${NC}"
mkdir -p "${SCRIPT_DIR}/data"
mkdir -p "${SCRIPT_DIR}/data/snapshots"
mkdir -p "${SCRIPT_DIR}/data/thumbnails"
mkdir -p "${SCRIPT_DIR}/data/encodings"
echo -e "${GREEN}✓ Data directory created${NC}"
echo ""

# Install service files
echo -e "${BLUE}[3/6] Installing systemd service files...${NC}"
sudo cp /tmp/seewhozthere.service /etc/systemd/system/
sudo cp /tmp/seewhozthere-web.service /etc/systemd/system/
echo -e "${GREEN}✓ Service files installed${NC}"
echo ""

# Reload systemd
echo -e "${BLUE}[4/6] Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"
echo ""

# Enable services
echo -e "${BLUE}[5/6] Enabling services to start on boot...${NC}"
sudo systemctl enable seewhozthere.service
sudo systemctl enable seewhozthere-web.service
echo -e "${GREEN}✓ Services enabled${NC}"
echo ""

# Start services
echo -e "${BLUE}[6/6] Starting services...${NC}"
sudo systemctl start seewhozthere.service
sudo systemctl start seewhozthere-web.service
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Check status
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Installation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${GREEN}Service Status:${NC}"
echo ""

# Check processor service
if sudo systemctl is-active --quiet seewhozthere.service; then
    echo -e "  Face Detection: ${GREEN}✓ Running${NC}"
else
    echo -e "  Face Detection: ${RED}✗ Not Running${NC}"
fi

# Check web service
if sudo systemctl is-active --quiet seewhozthere-web.service; then
    echo -e "  Web Dashboard:  ${GREEN}✓ Running${NC}"
else
    echo -e "  Web Dashboard:  ${RED}✗ Not Running${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  ${YELLOW}View status:${NC}"
echo -e "    sudo systemctl status seewhozthere"
echo -e "    sudo systemctl status seewhozthere-web"
echo ""
echo -e "  ${YELLOW}View logs:${NC}"
echo -e "    sudo journalctl -u seewhozthere -f"
echo -e "    sudo journalctl -u seewhozthere-web -f"
echo -e "    tail -f ${SCRIPT_DIR}/data/service.log"
echo -e "    tail -f ${SCRIPT_DIR}/data/web.log"
echo ""
echo -e "  ${YELLOW}Stop services:${NC}"
echo -e "    sudo systemctl stop seewhozthere"
echo -e "    sudo systemctl stop seewhozthere-web"
echo ""
echo -e "  ${YELLOW}Restart services:${NC}"
echo -e "    sudo systemctl restart seewhozthere"
echo -e "    sudo systemctl restart seewhozthere-web"
echo ""
echo -e "  ${YELLOW}Disable auto-start:${NC}"
echo -e "    sudo systemctl disable seewhozthere"
echo -e "    sudo systemctl disable seewhozthere-web"
echo ""
echo -e "${GREEN}Web Dashboard: ${BLUE}http://$(hostname -I | awk '{print $1}'):7222${NC}"
echo ""
echo -e "${GREEN}The system will now start automatically on boot!${NC}"
echo ""

# Clean up
rm -f /tmp/seewhozthere.service /tmp/seewhozthere-web.service
