#!/bin/bash
#
# Build script for SeeWhozThere React Dashboard
#
# This script builds the React frontend and copies it to the FastAPI static directory
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
echo -e "${BLUE}SeeWhozThere Dashboard Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}ERROR: Node.js is not installed${NC}"
    echo -e "${YELLOW}Please install Node.js 18+ first:${NC}"
    echo -e "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo -e "  sudo apt-get install -y nodejs"
    exit 1
fi

echo -e "${GREEN}Node.js version: $(node --version)${NC}"
echo -e "${GREEN}npm version: $(npm --version)${NC}"
echo ""

# Navigate to frontend directory
cd "${SCRIPT_DIR}/frontend"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}[1/3] Installing dependencies...${NC}"
    npm install
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
    echo ""
fi

# Build the React app
echo -e "${BLUE}[2/3] Building React app...${NC}"
npm run build
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Copy build to FastAPI static directory
echo -e "${BLUE}[3/3] Copying build to FastAPI...${NC}"

# Create static directory if it doesn't exist
mkdir -p "${SCRIPT_DIR}/app/static/dashboard"

# Remove old build
rm -rf "${SCRIPT_DIR}/app/static/dashboard"/*

# Copy new build
cp -r dist/* "${SCRIPT_DIR}/app/static/dashboard/"

echo -e "${GREEN}✓ Build copied to app/static/dashboard${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Build Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}The React dashboard has been built and is ready to serve.${NC}"
echo ""
echo -e "To start the server:"
echo -e "  ${BLUE}python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7222${NC}"
echo ""
echo -e "Then visit:"
echo -e "  ${BLUE}http://YOUR_PI_IP:7222/dashboard${NC}"
echo ""
