#!/bin/bash
# AI Studio Corp - Launcher Nativo
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "🔧 Criando ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

export GI_TYPELIB_PATH="/usr/lib/girepository-1.0:/usr/lib64/girepository-1.0"

python app.py
