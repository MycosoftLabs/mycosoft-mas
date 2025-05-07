#!/bin/bash
set -e

# Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Clone MAS repo (replace with your repo URL)
git clone https://github.com/yourusername/your-mas-repo.git
cd your-mas-repo

# Python setup
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Start Docker services
docker-compose up -d

# Run backend (adjust as needed)
# python mycosoft_mas/core/myca_main.py &

# Run tests
pytest || python run_tests.py 