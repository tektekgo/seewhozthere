#!/bin/bash
#
# SeeWhozThere Setup Script
#
# This script sets up a Python virtual environment with all required
# dependencies pinned to compatible versions.
#
# IMPORTANT: This script must be run BEFORE install_service.sh
#
# Usage:
#   ./setup.sh
#
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="${SCRIPT_DIR}/venv"

echo -e "${BLUE}========================================"
echo -e "SeeWhozThere Setup"
echo -e "========================================${NC}"
echo ""

# Step 1: Check Python version
echo -e "${BLUE}[1/5] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
echo ""

# Step 2: Create virtual environment
echo -e "${BLUE}[2/5] Creating virtual environment...${NC}"
if [ -d "${VENV_DIR}" ]; then
    echo -e "${YELLOW}  Virtual environment already exists. Skipping creation.${NC}"
else
    python3 -m venv "${VENV_DIR}"
    echo -e "${GREEN}✓ Virtual environment created at ${VENV_DIR}${NC}"
fi
echo ""

# Step 3: Activate virtual environment
echo -e "${BLUE}[3/5] Activating virtual environment...${NC}"
source "${VENV_DIR}/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${BLUE}[4/5] Installing Python dependencies...${NC}"
echo -e "${YELLOW}  Note: numpy is pinned to < 2.0 for Hailo SDK compatibility${NC}"
pip install --upgrade pip -q
pip install -r "${SCRIPT_DIR}/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 5: Verify critical dependencies
echo -e "${BLUE}[5/5] Verifying critical dependencies...${NC}"

# Check numpy version
NUMPY_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "NOT INSTALLED")
if python3 -c "import numpy; v=numpy.__version__; assert int(v.split('.')[0]) < 2" 2>/dev/null; then
    echo -e "${GREEN}  ✓ numpy ${NUMPY_VERSION} (compatible with Hailo SDK)${NC}"
else
    echo -e "${RED}  ✗ numpy ${NUMPY_VERSION} is NOT compatible with Hailo SDK (must be < 2.0)${NC}"
    exit 1
fi

# Check OpenCV
CV_VERSION=$(python3 -c "import cv2; print(cv2.__version__)" 2>/dev/null || echo "NOT INSTALLED")
if [ "${CV_VERSION}" != "NOT INSTALLED" ]; then
    echo -e "${GREEN}  ✓ OpenCV ${CV_VERSION}${NC}"
else
    echo -e "${RED}  ✗ OpenCV not installed${NC}"
    exit 1
fi

# Check FastAPI
FASTAPI_VERSION=$(python3 -c "import fastapi; print(fastapi.__version__)" 2>/dev/null || echo "NOT INSTALLED")
if [ "${FASTAPI_VERSION}" != "NOT INSTALLED" ]; then
    echo -e "${GREEN}  ✓ FastAPI ${FASTAPI_VERSION}${NC}"
else
    echo -e "${RED}  ✗ FastAPI not installed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================"
echo -e "Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${GREEN}Virtual environment is ready at: ${VENV_DIR}${NC}"
echo ""
echo -e "${YELLOW}To activate the virtual environment manually:${NC}"
echo -e "  source ${VENV_DIR}/bin/activate"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Configure cameras:  cp config.ini.example config.ini && nano config.ini"
echo -e "  2. Build dashboard:    ./build_frontend.sh"
echo -e "  3. Install service:    ./install_service.sh"
echo -e "  4. Access dashboard:   http://$(hostname -I | awk '{print $1}'):7222/dashboard"
echo ""
