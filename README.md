# YouTube AI Studio 🎬

Sistema multi-agente com IA que automatiza a criação de vídeos para YouTube, com uma interface gamificada de escritório onde os agentes trabalham.

## Arquitetura

```
                    ┌──────────────────────┐
                    │   Interface Web       │
                    │  (Escritório Game)    │
                    └──────────┬───────────┘
                               │ WebSocket
                    ┌──────────▼───────────┐
                    │   Orquestrador (CEO) │
                    │  - Contrata agentes  │
                    │  - Coordena pipeline │
                    │  - Garante qualidade │
                    └──────────┬───────────┘
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│  Jornalista     │  │  Roteirista     │  │  Designer       │
│  (Notícias RSS) │  │  (Script)       │  │  (Imagens)      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                     │                     │
┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│  Locutor        │  │  Editor         │  │                  │
│  (Voz/gTTS)     │──▶│  (Vídeo/MoviePy)│  │                  │
└─────────────────┘  └─────────────────┘  └──────────────────┘
```

## Agentes

| Agente | Função | Tecnologia |
|--------|--------|------------|
| **Orquestrador** (CEO) | Contrata, coordena e garante qualidade | GPT-4o |
| **Repórter Tech** (Jornalista) | Busca últimas notícias de tecnologia | RSS Feeds + GPT-4o |
| **Roteirista** (Criativo) | Cria roteiro para narração | GPT-4o |
| **Locutor** (Voz) | Gera áudio da narração | gTTS |
| **Designer** (Imagens) | Busca imagens com créditos | Unsplash API |
| **Editor** (Vídeo) | Compõe o vídeo final | MoviePy + FFmpeg |

## Fluxo de Produção

1. **Contratação** - O Orquestrador entrevista e contrata cada agente
2. **Coleta** - Jornalista busca notícias reais de feeds RSS
3. **Roteiro** - Roteirista cria texto para narração
4. **Imagens** - Designer busca imagens com atribuição
5. **Voz** - Locutor gera áudio com gTTS
6. **Edição** - Editor compõe vídeo final com imagens + áudio

## Requisitos

- Python 3.10+
- [OpenAI API Key](https://platform.openai.com/api-keys)
- FFmpeg (para edição de vídeo)

## Instalação

```bash
# Clonar o projeto
cd youtube-ai-studio

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r backend/requirements.txt

# Configurar chave da API
cp .env.example .env
# Edite .env com sua OPENAI_API_KEY

# Verificar FFmpeg
ffmpeg -version
```

## Uso

```bash
# Ativar ambiente
source venv/bin/activate

# Iniciar servidor
python backend/main.py

# Acessar no navegador
# http://localhost:8000
```

## Interface Web

O escritório virtual mostra:
- 🏢 **Escritório** com mesas e agentes animados
- 👔 **CEO** no centro coordenando a equipe
- 📋 **Log** em tempo real de cada agente
- 🎯 **Entrevistas** visuais durante a contratação
- 🎬 **Status** da produção do vídeo

### Como usar na interface:

1. Clique em **"Contratar Equipe"** para iniciar as entrevistas
2. Aguarde o Orquestrador contratar cada agente
3. Clique em **"Iniciar Produção"** para começar o pipeline
4. Acompanhe os agentes trabalhando em tempo real
5. O vídeo final será gerado em `output/videos/`

## Estrutura

```
youtube-ai-studio/
├── backend/
│   ├── main.py              # Servidor FastAPI + WebSocket
│   ├── requirements.txt     # Dependências Python
│   └── agents/
│       ├── base.py          # Classe base dos agentes
│       ├── orchestrator.py  # CEO - coordena tudo
│       ├── news_gatherer.py # Busca notícias
│       ├── script_writer.py # Cria roteiros
│       ├── voice_artist.py  # Gera áudio
│       ├── image_designer.py# Busca imagens
│       └── video_editor.py  # Edita vídeo
├── web/
│   ├── index.html           # Interface gamificada
│   ├── style.css            # Estilo do escritório
│   └── script.js            # Conexão WebSocket + UI
├── output/
│   ├── videos/              # Vídeos gerados
│   ├── audio/               # Áudio da narração
│   └── images/              # Imagens coletadas
├── .env                     # Configuração (API keys)
└── README.md
```
