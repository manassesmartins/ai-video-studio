let ws = null;
let reconnectTimer = null;
let logEntries = 0;
let hiredAgents = 0;
let pipelineRunning = false;

const AGENT_KEYS = {
    'Jornalista de Tecnologia': 'reporter',
    'Roteirista Criativo': 'script',
    'Artista de Voz': 'voice',
    'Designer de Imagens': 'designer',
    'Editor de Vídeo': 'editor',
    'CEO / Coordenador': 'orchestrator'
};

function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('connectionStatus').textContent = '🟢 Conectado';
        document.getElementById('connectionStatus').className = 'connected';
        updateClock();
    };

    ws.onclose = () => {
        document.getElementById('connectionStatus').textContent = '🔴 Desconectado';
        document.getElementById('connectionStatus').className = '';
        reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch (e) {
            console.error('Erro ao processar mensagem:', e);
        }
    };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'status_update':
            handleStatusUpdate(msg);
            break;
        case 'hiring_start':
            handleHiringStart(msg);
            break;
        case 'job_created':
            handleJobCreated(msg);
            break;
        case 'interview_start':
            handleInterviewStart(msg);
            break;
        case 'interview_result':
            handleInterviewResult(msg);
            break;
        case 'hiring_complete':
            handleHiringComplete(msg);
            break;
        case 'pipeline_start':
            handlePipelineStart(msg);
            break;
        case 'stage_update':
            handleStageUpdate(msg);
            break;
        case 'news_collected':
            handleNewsCollected(msg);
            break;
        case 'script_created':
            handleScriptCreated(msg);
            break;
        case 'images_prepared':
            handleImagesPrepared(msg);
            break;
        case 'audio_generated':
            handleAudioGenerated(msg);
            break;
        case 'video_complete':
            handleVideoComplete(msg);
            break;
        case 'pipeline_complete':
            handlePipelineComplete(msg);
            break;
        case 'error':
            handleError(msg);
            break;
        case 'hiring_required':
            handleHiringRequired(msg);
            break;
        case 'agents_status':
            updateAllAgentStatus(msg.agents);
            break;
        case 'task_start':
            handleTaskStart(msg);
            break;
        case 'task_complete':
            handleTaskComplete(msg);
            break;
    }
}

function updateClock() {
    const now = new Date();
    const time = now.toTimeString().split(' ')[0];
    document.getElementById('clock').textContent = time;
    setTimeout(updateClock, 1000);
}

function addLog(message, agentClass = '') {
    const panel = document.getElementById('logPanel');
    const empty = panel.querySelector('.log-empty');
    if (empty) empty.remove();

    const entry = document.createElement('div');
    entry.className = `log-entry ${agentClass}`;
    entry.innerHTML = message;
    panel.appendChild(entry);
    panel.scrollTop = panel.scrollHeight;

    logEntries++;
    document.getElementById('logCount').textContent = logEntries;
}

function updateAgentStatus(agentKey, status, hired = false) {
    const statusEl = document.getElementById(`status-${agentKey}`);
    if (statusEl) {
        if (hired) {
            statusEl.textContent = '✅ Contratado';
            statusEl.style.color = '#4caf7d';
        } else if (status === 'working') {
            statusEl.textContent = '⚙️ Trabalhando...';
            statusEl.style.color = '#e67e22';
        } else if (status === 'searching' || status === 'analyzing' || status === 'writing' || status === 'recording' || status === 'composing') {
            statusEl.textContent = `🔍 ${status.charAt(0).toUpperCase() + status.slice(1)}...`;
            statusEl.style.color = '#e67e22';
        } else if (status === 'interviewing') {
            statusEl.textContent = '🎯 Entrevistando...';
            statusEl.style.color = '#9b59b6';
        } else if (status === 'hiring') {
            statusEl.textContent = '🏢 Contratando...';
            statusEl.style.color = '#9b59b6';
        } else if (status === 'idle') {
            statusEl.textContent = hired ? '✅ Contratado' : '⏳ Aguardando';
            statusEl.style.color = hired ? '#4caf7d' : '#8888bb';
        }
    }

    const desk = document.getElementById(`desk-${agentKey}`);
    if (desk) {
        if (status === 'working' || status === 'searching' || status === 'analyzing' || status === 'writing' || status === 'recording' || status === 'composing' || status === 'downloading') {
            desk.classList.add('working');
        } else {
            desk.classList.remove('working');
        }
        if (hired) {
            desk.classList.add('hired');
        }
    }
}

function updateAllAgentStatus(agents) {
    if (!Array.isArray(agents)) return;
    agents.forEach(agent => {
        const key = AGENT_KEYS[agent.role];
        if (key) {
            updateAgentStatus(key, agent.status, agent.hired);
        }
    });
}

function showBubble(agentKey, text, duration = 3000) {
    const bubble = document.getElementById(`bubble-${agentKey}`);
    if (!bubble) return;

    bubble.textContent = text;
    bubble.style.display = 'block';

    clearTimeout(bubble._timeout);
    bubble._timeout = setTimeout(() => {
        bubble.style.display = 'none';
    }, duration);
}

function showHiringBanner(show) {
    const banner = document.getElementById('hiringBanner');
    banner.style.display = show ? 'flex' : 'none';
}

function updateHiringProgress(percent, status) {
    document.getElementById('hiringBar').style.width = `${percent}%`;
    document.getElementById('hiringStatus').textContent = status;
}

function handleStatusUpdate(msg) {
    addLog(`<span class="log-msg">${msg.message}</span>`);
    if (msg.orchestrator_status) {
        updateAgentStatus('orchestrator', msg.orchestrator_status, true);
    }
    if (msg.hiring_complete) {
        document.getElementById('btnPipeline').disabled = false;
    }
}

function handleHiringStart(msg) {
    showHiringBanner(true);
    updateHiringProgress(5, 'Abrindo processo seletivo...');
    addLog(`🏢 <strong>Orquestrador</strong>: "Vamos contratar nossa equipe!"`, 'agent-orchestrator');
}

function handleJobCreated(msg) {
    const roles = {
        'Jornalista de Tecnologia': '📰',
        'Roteirista Criativo': '✍️',
        'Artista de Voz': '🎙️',
        'Designer de Imagens': '🎨',
        'Editor de Vídeo': '🎬'
    };
    const icon = roles[msg.role] || '📋';
    addLog(`${icon} <span class="log-agent">Vaga:</span> <span class="log-msg">${msg.role}</span>`, 'hire');
}

function handleInterviewStart(msg) {
    const pct = 20 + (hiredAgents * 15);
    updateHiringProgress(pct, `Entrevistando: ${msg.agent_name} para ${msg.role}`);
    showBubble('orchestrator', `Entrevistando ${msg.agent_name}...`, 2000);
    addLog(`🎯 <span class="log-agent">Orquestrador:</span> <span class="log-msg">Entrevistando ${msg.agent_name} para ${msg.role}...</span>`, 'agent-orchestrator');
}

function handleInterviewResult(msg) {
    const key = AGENT_KEYS[msg.role];
    if (msg.hired) {
        hiredAgents++;
        updateAgentStatus(key, 'idle', true);
        showBubble(key, `Contratado! 🎉`, 3000);
        addLog(`✅ <span class="log-agent">${msg.agent_name}</span> <span class="log-msg">foi CONTRATADO para ${msg.role}! (Nota: ${msg.score}/10)</span>`, 'hire');
        addLog(`💬 <span class="log-agent">Orquestrador:</span> <span class="log-msg">"Bem-vindo ao time, ${msg.agent_name}!"</span>`, 'agent-orchestrator');
        showBubble('orchestrator', `${msg.agent_name} contratado! 🎉`, 2000);
    } else {
        addLog(`❌ <span class="log-agent">${msg.agent_name}</span> <span class="log-msg">NÃO foi contratado para ${msg.role}. Motivo: ${msg.reason}</span>`, 'error');
    }
}

function handleHiringComplete(msg) {
    updateHiringProgress(100, 'Equipe completa! 🎉');
    setTimeout(() => showHiringBanner(false), 2000);

    addLog(`🎉 <strong>Processo seletivo concluído!</strong> ${msg.team_size}/${msg.total} agentes contratados!`, 'hire');
    addLog(`🚀 <span class="log-agent">Orquestrador:</span> <span class="log-msg">"Equipe formada! Prontos para produzir!"</span>`, 'agent-orchestrator');

    document.getElementById('btnPipeline').disabled = false;
    document.getElementById('btnHire').disabled = true;
    showBubble('orchestrator', 'Equipe formada! 🚀', 3000);
    updateAgentStatus('orchestrator', 'idle', true);
}

function handlePipelineStart(msg) {
    pipelineRunning = true;
    document.getElementById('btnPipeline').disabled = true;
    addLog(`🎬 <strong>${msg.message}</strong>`, 'hire');
    showBubble('orchestrator', 'Mãos à obra! 🎬', 3000);
    document.getElementById('boardStatus').textContent = '🎬 Produzindo vídeo...';
}

function handleStageUpdate(msg) {
    document.getElementById('boardStatus').textContent = msg.stage;
    addLog(`📋 <span class="log-msg">${msg.stage}</span>`);

    const agentKey = AGENT_KEYS[msg.agent] || Object.keys(AGENT_KEYS).find(k => msg.agent.includes(k) || k.includes(msg.agent));
    if (agentKey) {
        updateAgentStatus(agentKey, 'working', true);
        showBubble(agentKey, 'Trabalhando... ⚙️', 2000);
    }
}

function handleNewsCollected(msg) {
    const list = document.getElementById('outputNewsList');
    list.innerHTML = '';

    msg.items.forEach((item) => {
        const el = document.createElement('div');
        el.className = 'news-item';
        el.innerHTML = `
            <div class="news-title">📰 ${item.title}</div>
            <div class="news-source">${item.source} - <a href="${item.url}" target="_blank">Ler original</a></div>
        `;
        list.appendChild(el);
    });

    document.querySelector('.output-placeholder').style.display = 'none';
    document.getElementById('outputContent').style.display = 'block';

    addLog(`📰 <span class="log-msg">${msg.count} notícias coletadas!</span>`, 'agent-reporter');
    showBubble('reporter', `${msg.count} notícias encontradas! 📰`, 3000);
    updateAgentStatus('reporter', 'idle', true);
}

function handleScriptCreated(msg) {
    addLog(`✍️ <span class="log-msg">Roteiro criado com ${msg.segments_count} segmentos!</span>`, 'agent-script');
    showBubble('script', 'Roteiro pronto! ✍️', 3000);
    updateAgentStatus('script', 'idle', true);
}

function handleImagesPrepared(msg) {
    const list = document.getElementById('outputNewsList');
    const items = list.querySelectorAll('.news-item');
    msg.images.forEach((img, i) => {
        if (items[i]) {
            items[i].innerHTML += `
                <div class="news-source" style="color:#e84393">🖼️ ${img.credit}</div>
            `;
        }
    });

    addLog(`🎨 <span class="log-msg">${msg.count} imagens preparadas com créditos!</span>`, 'agent-designer');
    showBubble('designer', 'Imagens prontas! 🎨', 3000);
    updateAgentStatus('designer', 'idle', true);
}

function handleAudioGenerated(msg) {
    addLog(`🎙️ <span class="log-msg">Narração gravada! ${msg.files_count} arquivos de áudio gerados.</span>`, 'agent-voice');
    showBubble('voice', 'Gravação concluída! 🎙️', 3000);
    updateAgentStatus('voice', 'idle', true);
}

function handleVideoComplete(msg) {
    addLog(`🎬 <span class="log-msg">${msg.message}</span>`, 'agent-editor');
    showBubble('editor', 'Vídeo finalizado! 🎬', 4000);
    updateAgentStatus('editor', 'idle', true);

    if (msg.video_path) {
        const videoContainer = document.getElementById('outputVideo');
        videoContainer.innerHTML = `
            <div style="margin-top:12px;padding:12px;background:rgba(76,175,125,0.1);border-radius:8px;border:1px solid var(--accent-green);text-align:center">
                <div style="font-size:48px;margin-bottom:8px">🎉</div>
                <strong>VÍDEO FINALIZADO!</strong>
                <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">${msg.video_path}</div>
            </div>
        `;
    }

    document.getElementById('boardStatus').textContent = '✅ Vídeo concluído!';
    document.getElementById('btnReset').style.display = 'inline-block';
}

function handlePipelineComplete(msg) {
    addLog(`🎉 <strong>${msg.message}</strong>`, 'hire');
    showBubble('orchestrator', 'Missão cumprida! 🎉', 4000);
    pipelineRunning = false;
}

function handleError(msg) {
    addLog(`❌ <span class="log-msg">${msg.message}</span>`, 'error');
    showBubble('orchestrator', 'Erro! Verifique o log.', 3000);
}

function handleHiringRequired(msg) {
    addLog(`⚠️ <span class="log-msg">${msg.message}</span>`, 'error');
}

function handleTaskStart(msg) {
    const key = AGENT_KEYS[msg.role];
    if (key) {
        updateAgentStatus(key, 'working', true);
        showBubble(key, msg.task.substring(0, 40) + '...', 3000);
    }
}

function handleTaskComplete(msg) {
    const key = AGENT_KEYS[msg.role];
    if (key) {
        updateAgentStatus(key, 'idle', true);
        showBubble(key, 'Tarefa concluída! ✅', 2000);
    }
}

function startHiring() {
    document.getElementById('btnHire').disabled = true;
    send({ action: 'start_hiring' });
}

function startPipeline() {
    send({ action: 'start_pipeline', news_count: 5 });
    document.getElementById('btnPipeline').disabled = true;
}

function resetAll() {
    location.reload();
}

connect();
