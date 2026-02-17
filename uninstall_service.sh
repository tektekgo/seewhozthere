#!/bin/bash
#
# SeeWhozThere Service Uninstallation Script
#
# This script removes the SeeWhozThere systemd services.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SeeWhozThere Service Uninstallation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}ERROR: Do not run this script as root or with sudo${NC}"
    echo -e "${YELLOW}Run it as your normal user: ./uninstall_service.sh${NC}"
    exit 1
fi

# Confirm uninstallation
echo -e "${YELLOW}This will stop and remove the SeeWhozThere services.${NC}"
echo -e "${YELLOW}Your data and configuration will NOT be deleted.${NC}"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Uninstallation cancelled.${NC}"
    exit 0
fi

echo ""

# Stop services
echo -e "${BLUE}[1/4] Stopping services...${NC}"
sudo systemctl stop seewhozthere.service 2>/dev/null || true
sudo systemctl stop seewhozthere-web.service 2>/dev/null || true
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""

# Disable services
echo -e "${BLUE}[2/4] Disabling services...${NC}"
sudo systemctl disable seewhozthere.service 2>/dev/null || true
sudo systemctl disable seewhozthere-web.service 2>/dev/null || true
echo -e "${GREEN}✓ Services disabled${NC}"
echo ""

# Remove service files
echo -e "${BLUE}[3/4] Removing service files...${NC}"
sudo rm -f /etc/systemd/system/seewhozthere.service
sudo rm -f /etc/systemd/system/seewhozthere-web.service
echo -e "${GREEN}✓ Service files removed${NC}"
echo ""

# Reload systemd
echo -e "${BLUE}[4/4] Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Uninstallation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Services have been removed.${NC}"
echo -e "${YELLOW}Your data and configuration are still in the project directory.${NC}"
echo ""
echo -e "To run SeeWhozThere manually:"
echo -e "  ${BLUE}python3 run_service.py${NC}"
echo ""
