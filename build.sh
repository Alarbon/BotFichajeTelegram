#!/usr/bin/env bash

echo "▶️ Instalando Python 3.11"
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

echo "🔁 Usando Python 3.11"
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
