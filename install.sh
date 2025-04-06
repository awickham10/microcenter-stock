#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Microcenter Stock Checker...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Get the actual user who ran sudo
ACTUAL_USER=$SUDO_USER
if [ -z "$ACTUAL_USER" ]; then
    echo -e "${RED}Could not determine the actual user${NC}"
    exit 1
fi

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${YELLOW}Setting up log directory...${NC}"
mkdir -p /var/log/microcenter
chown $ACTUAL_USER:$ACTUAL_USER /var/log/microcenter

echo -e "${YELLOW}Installing system service...${NC}"
cp "$SCRIPT_DIR/microcenter-stock.service" /etc/systemd/system/
# Update the service file with the correct user and path
sed -i "s|User=administrator|User=$ACTUAL_USER|g" /etc/systemd/system/microcenter-stock.service
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" /etc/systemd/system/microcenter-stock.service
sed -i "s|ExecStart=.*|ExecStart=$SCRIPT_DIR/.venv/bin/python3 $SCRIPT_DIR/stock_checker.py|g" /etc/systemd/system/microcenter-stock.service

echo -e "${YELLOW}Checking if config.env exists...${NC}"
if [ ! -f "$SCRIPT_DIR/config.env" ]; then
    if [ -f "$SCRIPT_DIR/config.env.example" ]; then
        echo -e "${YELLOW}Creating config.env from example...${NC}"
        cp "$SCRIPT_DIR/config.env.example" "$SCRIPT_DIR/config.env"
        chown $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/config.env"
        echo -e "${YELLOW}Please edit config.env with your settings before starting the service${NC}"
    else
        echo -e "${RED}No config.env or config.env.example found${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload

echo -e "${YELLOW}Enabling service...${NC}"
systemctl enable microcenter-stock

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${YELLOW}To start the service:${NC} sudo systemctl start microcenter-stock"
echo -e "${YELLOW}To check status:${NC} sudo systemctl status microcenter-stock"
echo -e "${YELLOW}To view logs:${NC} sudo journalctl -u microcenter-stock -f" 