#!/bin/bash
# YouTube AI Studio - Script de inicialização
cd "$(dirname "$0")"

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "🔧 Criando ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

# Verificar FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg não encontrado. Instale-o para edição de vídeo:"
    echo "   sudo apt install ffmpeg  # Linux"
    echo "   brew install ffmpeg      # macOS"
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado. Copie do .env.example:"
    echo "   cp .env.example .env"
    echo "   Edite o arquivo .env com sua OPENAI_API_KEY"
    exit 1
fi

echo "🎬 YouTube AI Studio - Iniciando..."
echo "📡 Servidor: http://localhost:${PORT:-8000}"
echo ""

python backend/main.py
