#!/bin/bash

# -----------------------------
# AnnounceMate Setup & Run
# -----------------------------

# 1. Create venv
python3 -m venv venv
echo "Virtual environment created."

# 2. Activate venv
source venv/bin/activate
echo "Virtual environment activated."

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install requirements
pip install -r requirements.txt

# 5. Run AnnounceMate
python -m announce_mate.main
