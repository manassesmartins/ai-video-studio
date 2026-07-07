const PixelSelect = {
    _active: null,

    toggle(btn) {
        PixelSelect.closeAll();
        const wrapper = btn.closest('.pixel-select');
        if (!wrapper) return;

        const currentVal = wrapper.dataset.value || '';
        const rawOpts = wrapper._options || [];

        const sorted = rawOpts
            .slice()
            .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));

        const overlay = document.createElement('div');
        overlay.className = 'pixel-select-overlay';
        overlay.onclick = e => { if (e.target === overlay) PixelSelect.closeAll(); };

        const popup = document.createElement('div');
        popup.className = 'pixel-select-popup';

        const header = document.createElement('div');
        header.className = 'pixel-select-popup-header';
        const title = document.createElement('span');
        title.className = 'pixel-select-popup-title';
        title.textContent = '📋 Selecione um modelo';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'pixel-select-popup-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = PixelSelect.closeAll;
        header.appendChild(title);
        header.appendChild(closeBtn);

        const list = document.createElement('div');
        list.className = 'pixel-select-popup-list';

        sorted.forEach(opt => {
            const el = document.createElement('div');
            el.className = 'pixel-select-popup-option' + (opt.value === currentVal ? ' selected' : '');
            el.dataset.value = opt.value;
            el.textContent = opt.label;
            el.onclick = () => {
                wrapper.dataset.value = opt.value;
                wrapper.querySelector('.pixel-select-text').textContent = opt.label;
                PixelSelect.closeAll();
            };
            list.appendChild(el);
        });

        popup.appendChild(header);
        popup.appendChild(list);
        overlay.appendChild(popup);
        document.body.appendChild(overlay);
        PixelSelect._active = overlay;
    },

    closeAll() {
        if (PixelSelect._active) {
            PixelSelect._active.remove();
            PixelSelect._active = null;
        }
    },

    render(opts, currentValue) {
        const display = opts.find(o => o.value === currentValue)?.label || currentValue || '—';
        return `<div class="pixel-select" data-value="${currentValue || ''}">
            <button type="button" class="pixel-select-btn" onclick="PixelSelect.toggle(this)">
                <span class="pixel-select-text">${display}</span>
                <span class="pixel-select-arrow">▼</span>
            </button>
        </div>`;
    }
};

document.addEventListener('click', e => {
    if (!e.target.closest('.pixel-select, .pixel-select-overlay')) PixelSelect.closeAll();
});

let logEntries = 0;
let company = {
    level: 1, xp: 0, xpNext: 100, videos: 0,
    revenue: 0, agents: 0, quality: 0, working: false
};

function callAPI(method, ...args) {
    return new Promise((resolve, reject) => {
        const w = window;
        if (w.pywebview && w.pywebview.api && typeof w.pywebview.api[method] === 'function') {
            w.pywebview.api[method](...args).then(resolve).catch(reject);
        } else {
            reject(new Error('Bridge not ready'));
        }
    });
}

const tryAPI = (method, ...args) => callAPI(method, ...args).catch(() => {});

function checkBridge() {
    if (window.pywebview && window.pywebview.api) {
        document.getElementById('connectionStatus').textContent = '\uD83D\uDFE2 Operacional';
        document.getElementById('connectionStatus').className = 'connected';
        setTimeout(() => callAPI('start_hiring'), 500);
    } else {
        document.getElementById('connectionStatus').textContent = '\uD83D\uDD34 Bridge indispon\u00EDvel';
        document.getElementById('connectionStatus').className = '';
        setTimeout(checkBridge, 500);
    }
}

const AGENT_KEYS = {
    'Jornalista de Tecnologia': 'reporter', 'Roteirista Criativo': 'script',
    'Artista de Voz': 'voice', 'Designer de Imagens': 'designer',
    'Editor de V\u00EDdeo': 'editor', 'CEO / Coordenador': 'orchestrator'
};
const NAME_TO_KEY = {
    'Repórter Tech': 'reporter', 'Roteirista': 'script',
    'Locutor': 'voice', 'Designer': 'designer',
    'Editor': 'editor', 'Orquestrador': 'orchestrator'
};

function $(id) { return document.getElementById(id); }

function updateCompanyUI() {
    $('companyLevel').textContent = `Nv. ${company.level}`;
    $('levelBadge').textContent = `Nv. ${company.level}`;
    $('xpDisplay').textContent = `${company.xp} / ${company.xpNext} XP`;
    $('xpBar').style.width = `${(company.xp / company.xpNext) * 100}%`;
    $('videoCount').textContent = company.videos;
    $('dashVideos').textContent = company.videos;
    $('agentCount').textContent = company.agents;
    $('dashAgents').textContent = company.agents;
    $('revenueDisplay').textContent = `$${company.revenue}`;
    $('dashRevenue').textContent = `$${company.revenue}`;
    $('dashQuality').textContent = `${company.quality}%`;
}

function updateAgentXP(key, pct) {
    const fill = document.getElementById(`xp-${key}`);
    if (fill) fill.style.width = `${Math.min(pct, 100)}%`;
}

function resetAgentProgress(key) {
    const actionEl = document.getElementById(`action-${key}`);
    if (actionEl) actionEl.textContent = '';
    const progEl = document.getElementById(`prog-${key}`);
    if (progEl) progEl.style.width = '0%';
}

function resetAllAgents() {
    ['orchestrator', 'reporter', 'script', 'voice', 'designer', 'editor'].forEach(k => {
        resetAgentProgress(k);
        updateAgentStatus(k, 'idle', true);
        const bubble = $(`bubble-${k}`);
        if (bubble) { bubble.style.display = 'none'; }
    });
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'company_update':
            if (msg.level) company.level = msg.level;
            if (msg.xp !== undefined) company.xp = msg.xp;
            if (msg.xpNext) company.xpNext = msg.xpNext;
            if (msg.videos !== undefined) company.videos = msg.videos;
            if (msg.revenue !== undefined) company.revenue = msg.revenue;
            if (msg.agents !== undefined) company.agents = msg.agents;
            if (msg.quality !== undefined) company.quality = msg.quality;
            updateCompanyUI();
            break;
        case 'level_up':
            addLog(`🎉 <strong>AI STUDIO CORP EVOLUIU PARA NÍVEL ${msg.level}!</strong>`, 'hire');
            $('boardStatus').textContent = msg.unlock || 'Novas possibilidades desbloqueadas!';
            showBubble('orchestrator', `Nível ${msg.level}! 🏆`, 5000);
            company.level = msg.level;
            updateCompanyUI();
            break;
        case 'status_update':
            addLog(`<span class="log-msg">${msg.message}</span>`);
            break;
        case 'agent_xp':
            updateAgentXP(msg.key, msg.pct);
            break;
        case 'reset_all_agents':
            resetAllAgents();
            break;
        case 'agent_speaks':
            const speakKey = AGENT_KEYS[msg.role] || 'orchestrator';
            showBubble(speakKey, msg.text, msg.duration || 3000);
            break;
        case 'pipeline_start':
            $('btnProduce').disabled = true;
            $('btnProduce').textContent = '⏳ Produzindo...';
            $('companyStatus').textContent = '⚙️ Produzindo';
            $('companyStatus').style.color = '#fdcb6e';
            addLog('🚀 <span class="log-msg">Iniciando ciclo de produção...</span>', 'hire');
            resetAllAgents();
            break;
        case 'stage_update':
            $('boardStatus').textContent = msg.stage;
            addLog(`📋 <span class="log-msg">${msg.stage}</span>`);
            const stageKey = NAME_TO_KEY[msg.agent] || AGENT_KEYS[msg.agent] || msg.agent;
            if (stageKey) { updateAgentStatus(stageKey, 'working', true); showBubble(stageKey, 'Trabalhando... ⚙️', 2000); }
            break;
        case 'news_collected':
            addLog(`📰 <span class="log-msg">${msg.count} notícias coletadas!</span>`, 'agent-reporter');
            showBubble('reporter', `${msg.count} notícias! 📰`, 3000);
            updateAgentStatus('reporter', 'idle', true);
            resetAgentProgress('reporter');
            break;
        case 'script_created':
            addLog(`✍️ <span class="log-msg">Roteiro criado com ${msg.segments_count} segmentos!</span>`, 'agent-script');
            showBubble('script', 'Roteiro pronto! ✍️', 3000);
            updateAgentStatus('script', 'idle', true);
            resetAgentProgress('script');
            break;
        case 'images_prepared':
            addLog(`🎨 <span class="log-msg">${msg.count} imagens preparadas!</span>`, 'agent-designer');
            showBubble('designer', 'Imagens prontas! 🎨', 3000);
            updateAgentStatus('designer', 'idle', true);
            resetAgentProgress('designer');
            break;
        case 'audio_generated':
            addLog(`🎙️ <span class="log-msg">Narração gravada! ${msg.files_count} arquivos.</span>`, 'agent-voice');
            showBubble('voice', 'Gravação concluída! 🎙️', 3000);
            updateAgentStatus('voice', 'idle', true);
            resetAgentProgress('voice');
            break;
        case 'video_complete':
            addLog(`🎬 <span class="log-msg">${msg.message}</span>`, 'agent-editor');
            showBubble('editor', 'Vídeo finalizado! 🎬', 4000);
            updateAgentStatus('editor', 'idle', true);
            resetAgentProgress('editor');
            addMiniLog('✅ Vídeo produzido com sucesso!');
            if (msg.output_dir) {
                const btn = document.createElement('button');
                btn.className = 'btn-open-folder';
                btn.innerHTML = '📂 Abrir pasta de vídeos';
                btn.onclick = () => tryAPI('open_output_folder');
                document.getElementById('miniLog').appendChild(btn);
            }
            break;
        case 'pipeline_complete':
            addLog(`🏆 <strong>${msg.message}</strong>`, 'hire');
            showBubble('orchestrator', 'Mais um ciclo completo! 🎉', 3000);
            addMiniLog('🔄 Ciclo de produção concluído');
            $('btnProduce').disabled = false;
            $('btnProduce').textContent = '🎬 Iniciar Produção';
            $('companyStatus').textContent = '✅ Pronto';
            $('companyStatus').style.color = '#00b894';
            resetAllAgents();
            break;
        case 'hire_request':
            showHireModal(msg.candidate);
            addLog(`🤝 Orquestrador: "${msg.candidate.msg}"`, 'hire');
            break;
        case 'hire_result':
            if (msg.hired) {
                addLog(`✅ <strong>${msg.name}</strong> contratado como ${msg.role}!`, 'hire');
                const k = AGENT_KEYS[msg.role];
                if (k) updateAgentStatus(k, 'idle', true);
            } else {
                addLog(`❌ Contratação de <strong>${msg.name}</strong> recusada.`, 'error');
            }
            break;
        case 'hiring_complete':
            addLog('🏢 <strong>Time completo! Clique em "Iniciar Produção" para começar.</strong>', 'hire');
            break;
    }
}

function addLog(message, agentClass = '') {
    const panel = $('logPanel');
    const empty = panel.querySelector('.log-empty');
    if (empty) empty.remove();
    const entry = document.createElement('div');
    entry.className = `log-entry ${agentClass}`;
    entry.innerHTML = message;
    panel.appendChild(entry);
    panel.scrollTop = panel.scrollHeight;
    logEntries++;
    $('logCount').textContent = logEntries;
}

function addMiniLog(text) {
    const container = $('miniLog');
    const entry = document.createElement('div');
    entry.className = 'mini-log-entry';
    entry.textContent = text;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
    if (container.children.length > 20) container.removeChild(container.firstChild);
}

function updateAgentStatus(agentKey, status, hired = false) {
    const statusEl = $(`status-${agentKey}`);
    if (statusEl) {
        if (hired) { statusEl.textContent = '✅ Ativo'; statusEl.style.color = '#00b894'; }
        else if (status === 'working') { statusEl.textContent = '⚙️ Trabalhando'; statusEl.style.color = '#00cec9'; }
        else if (['searching', 'analyzing', 'writing', 'recording', 'composing', 'downloading', 'thinking'].includes(status)) {
            statusEl.textContent = `🔄 ${status.charAt(0).toUpperCase() + status.slice(1)}`;
            statusEl.style.color = '#fdcb6e';
        } else if (status === 'interviewing') { statusEl.textContent = '🎯 Entrevista'; statusEl.style.color = '#6c5ce7'; }
        else if (status === 'idle') { statusEl.textContent = hired ? '💤 Descansando' : '⏳ Disponível'; statusEl.style.color = hired ? '#8888b8' : '#5555a0'; }
    }
    const desk = $(`desk-${agentKey}`);
    if (desk) {
        const ws = ['working', 'searching', 'analyzing', 'writing', 'recording', 'composing', 'downloading', 'thinking', 'interviewing'];
        desk.classList.toggle('working', ws.includes(status));
        desk.classList.toggle('hired', hired);
    }
}

function showBubble(agentKey, text, duration = 3000) {
    const bubble = $(`bubble-${agentKey}`);
    if (!bubble) return;
    bubble.textContent = text;
    bubble.style.display = 'block';
    clearTimeout(bubble._timeout);
    bubble._timeout = setTimeout(() => { bubble.style.display = 'none'; }, duration);
}

function showHireModal(candidate) {
    $('candidateEmoji').textContent = candidate.emoji || '🤖';
    $('candidateName').textContent = candidate.name;
    $('candidateRole').textContent = candidate.role;
    $('candidateDesc').textContent = candidate.desc;
    $('candidateSkills').innerHTML = (candidate.skills || []).map(s => `<span class="skill-tag">${s}</span>`).join('');
    $('orchestratorMsg').textContent = `💬 Orquestrador: "${candidate.msg}"`;
    $('hireModal').classList.add('show');
    $('hireModal').dataset.candidate = JSON.stringify(candidate);
}

function approveHire() {
    const data = $('hireModal').dataset.candidate;
    $('hireModal').classList.remove('show');
    tryAPI('approve_hire', data);
}

function rejectHire() {
    const data = $('hireModal').dataset.candidate;
    $('hireModal').classList.remove('show');
    tryAPI('reject_hire', data);
}

function startProduction() { tryAPI('start_production'); }

function toggleSettings() {
    const modal = $('settingsModal');
    if (modal.classList.contains('show')) { hideSettings(); return; }
    modal.classList.add('show');
    callAPI('get_settings_full').then(s => {
        settingsCache = s;
        callAPI('get_providers_schema').then(schema => renderSettings(schema, s));
    }).catch(() => {
        $('settingsBody').innerHTML = '<p style="color:var(--coral);text-align:center;padding:20px">Erro ao carregar configurações</p>';
    });
}

function hideSettings() {
    stopTestAudio();
    $('settingsModal').classList.remove('show');
}

let settingsCache = {};
let _currentTestAudio = null;

function stopTestAudio() {
    if (_currentTestAudio) {
        _currentTestAudio.pause();
        _currentTestAudio = null;
    }
}

const CATEGORY_OPTS = [
    { value: 'Todas', label: '🌐 Todas as Categorias' },
    { value: 'Tecnologia', label: '💻 Tecnologia' },
    { value: 'Ciência', label: '🔬 Ciência' },
    { value: 'Política', label: '🏛️ Política' },
    { value: 'Economia', label: '📊 Economia' },
    { value: 'Saúde', label: '🏥 Saúde' },
    { value: 'Esportes', label: '⚽ Esportes' },
    { value: 'Entretenimento', label: '🎬 Entretenimento' },
    { value: 'Mundo', label: '🌍 Mundo' },
];

function switchSettingsTab(tabId) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.settings-tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.settings-tab[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');
}

function renderSettings(schema, full) {
    const body = $('settingsBody');
    const meta = schema._meta || {};
    const newsCount = meta.news_count || 5;
    const newsCategory = meta.news_category || 'Tecnologia';
    const rssFeeds = meta.rss_feeds || [];
    const apiKey = meta.openrouter_api_key || '';
    const availableModels = meta.available_models || [];
    const video = meta.video || {};
    const audio = meta.audio || {};
    const image = meta.image || {};

    const THEME_OPTS = [
        { value: 'default', label: '🎮 Retro Game' },
        { value: 'matrix', label: '💚 Matrix' },
        { value: 'ocean', label: '🌊 Oceano' },
        { value: 'sunset', label: '🌅 Pôr do Sol' },
        { value: 'mono', label: '⚪ Monocromático' },
        { value: 'midnight', label: '🌙 Meia-Noite' },
    ];

    const SCALE_OPTS = [
        { value: String(0.7), label: '70% (Muito Pequeno)' },
        { value: String(0.85), label: '85% (Pequeno)' },
        { value: String(1.0), label: '100% (Normal)' },
        { value: String(1.15), label: '115% (Grande)' },
        { value: String(1.3), label: '130% (Muito Grande)' },
        { value: String(1.5), label: '150% (Enorme)' },
    ];

    const RES_OPTS = [
        { label: '3840x2160 (4K)', w: 3840, h: 2160 },
        { label: '2560x1440 (QHD)', w: 2560, h: 1440 },
        { label: '1920x1080 (Full HD)', w: 1920, h: 1080 },
        { label: '1280x720 (HD)', w: 1280, h: 720 },
        { label: '854x480 (SD)', w: 854, h: 480 },
    ];
    const FPS_OPTS = [24, 25, 30, 48, 50, 60];
    const CODEC_OPTS = ['libx264', 'libx265', 'libvpx-vp9', 'h264_nvenc'];
    const VID_FORMATS = ['mp4', 'webm', 'avi', 'mkv'];
    const SAMPLERATES = [22050, 44100, 48000, 96000];
    const AUDIO_BITRATES = ['96k', '128k', '192k', '256k', '320k'];
    const IMG_FORMATS = ['jpg', 'png', 'webp'];

    const sel = (curr, opts, valKey) => opts.map(o => {
        const v = valKey ? o[valKey] : o;
        const label = valKey ? o.label : o;
        return `<option value="${v}" ${curr == v ? 'selected' : ''}>${label}</option>`;
    }).join('');

    const curRes = RES_OPTS.find(r => r.w === (video.width || 1920) && r.h === (video.height || 1080)) || RES_OPTS[2];

    const modelOpts = availableModels.length
        ? availableModels.map(m => `<option value="${m}">${m}</option>`).join('')
        : '<option value="">— sem modelos —</option>';

    const isLocal = (role) => schema[role] && schema[role].providers && schema[role].providers[0] === 'local';
    const FREE_PREFS = {
        'CEO / Coordenador': ['qwen/qwen3-next-80b-a3b-instruct:free', 'nvidia/nemotron-3-ultra-550b-a55b:free', 'google/gemma-4-31b-it:free'],
        'Jornalista de Tecnologia': ['qwen/qwen3-next-80b-a3b-instruct:free', 'google/gemma-4-26b-a4b-it:free', 'nvidia/nemotron-3-nano-30b-a3b:free'],
        'Roteirista Criativo': ['qwen/qwen3-next-80b-a3b-instruct:free', 'google/gemma-4-26b-a4b-it:free', 'nvidia/nemotron-3-ultra-550b-a55b:free'],
        'Designer de Imagens': ['qwen/qwen3-next-80b-a3b-instruct:free', 'google/gemma-4-26b-a4b-it:free', 'nvidia/nemotron-3-nano-30b-a3b:free'],
    };
    const pickFreeModel = (role) => {
        const prefs = FREE_PREFS[role] || ['qwen/qwen3-next-80b-a3b-instruct:free'];
        for (const m of prefs) {
            if (availableModels.includes(m)) return m;
        }
        return availableModels[0] || 'qwen/qwen3-next-80b-a3b-instruct:free';
    };
    const getSavedModel = (role) => {
        const cfg = schema[role];
        const saved = (cfg && cfg.saved_model) || (cfg && cfg.default_model) || '';
        if (saved && availableModels.includes(saved)) return saved;
        return pickFreeModel(role);
    };

    let agentCards = '';
    const agentOrder = ['CEO / Coordenador', 'Jornalista de Tecnologia', 'Roteirista Criativo',
                        'Artista de Voz', 'Designer de Imagens', 'Editor de Vídeo'];
    agentOrder.forEach(role => {
        const cfg = schema[role];
        if (!cfg) return;
        const actionsHtml = (cfg.actions || []).map(a => `<span class="action-tag">${a.name}</span>`).join('');

        let extraHtml = '';
        if (cfg.extra_fields) {
            Object.entries(cfg.extra_fields).forEach(([key, field]) => {
                const savedVal = cfg[key] !== undefined ? cfg[key] : field.default;
                if (field.type === 'boolean') {
                    const checked = savedVal === true || savedVal === 'true' ? 'checked' : '';
                    extraHtml += `<div class="settings-row">
                        <label>${field.label}</label>
                        <label class="switch">
                            <input type="checkbox" class="s-${key}" ${checked}>
                            <span class="switch-slider"></span>
                        </label>
                    </div>`;
                } else if (field.type === 'text') {
                    extraHtml += `<div class="settings-row" style="flex-wrap:wrap">
                        <label>${field.label}</label>
                        <textarea class="s-${key}" rows="2" style="flex:1;min-width:180px;font-family:inherit;resize:vertical">${savedVal}</textarea>
                    </div>`;
                } else if (field.options && field.options.length) {
                    extraHtml += `<div class="settings-row">
                        <label>${field.label}</label>
                        <select class="s-${key}">${field.options.map(o => {
                            const parts = o.split('|');
                            const val = parts[0];
                            const label = parts[1] || parts[0];
                            return `<option value="${val}" ${savedVal === val ? 'selected' : ''}>${label}</option>`;
                        }).join('')}</select>
                    </div>`;
                } else {
                    extraHtml += `<div class="settings-row">
                        <label>${field.label}</label>
                        <select class="s-${key}">${modelOpts}</select>
                    </div>`;
                }
            });
        }
        if (isLocal(role)) {
            agentCards += `
                <div class="settings-agent-card" data-role="${role}">
                    <div class="settings-agent-header">
                        <span class="emoji">${cfg.emoji || '🤖'}</span>
                        <div class="info"><strong>${cfg.label || role}</strong><span>${role}</span></div>
                    </div>
                    <div class="settings-row">
                        <label>Processamento</label>
                        <span style="font-size:12px;color:var(--text-secondary)">🎬 Local (MoviePy)</span>
                    </div>
                    ${extraHtml}
                    ${actionsHtml ? `<div class="settings-actions">${actionsHtml}</div>` : ''}
                </div>`;
        } else {
            const savedModel = getSavedModel(role);
            const testVoiceBtn = role === 'Artista de Voz' ? `
                <button class="btn-rss-add" style="margin-top:4px" onclick="testVoice()">▶️ Testar Voz</button>
                <span id="voiceTestStatus" style="font-size:10px;color:var(--text-secondary);align-self:center"></span>` : '';
            const fireBtn = `
                <button class="btn-rss-add fire-agent-btn" onclick="fireAgent('${role}')">🔥 Demitir</button>`;
            agentCards += `
                <div class="settings-agent-card" data-role="${role}">
                    <div class="settings-agent-header">
                        <span class="emoji">${cfg.emoji || '🤖'}</span>
                        <div class="info"><strong>${cfg.label || role}</strong><span>${role}</span></div>
                    </div>
                    <div class="settings-row">
                        <label>Modelo</label>
                        <select class="s-model">${modelOpts}</select>
                    </div>
                    <div class="settings-row">
                        <label>Temp.</label>
                        <input class="s-temp" type="number" step="0.1" min="0" max="2" value="0.7" style="flex:0.3">
                    </div>
                    ${extraHtml}
                    ${testVoiceBtn}
                    ${fireBtn}
                    ${actionsHtml ? `<div class="settings-actions">${actionsHtml}</div>` : ''}
                </div>`;
        }
    });

    const curTheme = meta.theme || 'default';
    const curFontScale = String(meta.font_scale !== undefined ? meta.font_scale : 1.0);
    const curLayoutScale = String(meta.layout_scale !== undefined ? meta.layout_scale : 1.0);

    const themeSel = (curr, opts) => opts.map(o =>
        `<option value="${o.value}" ${curr === o.value ? 'selected' : ''}>${o.label}</option>`
    ).join('');

    const catSel = (curr, opts) => opts.map(o =>
        `<option value="${o.value}" ${curr === o.value ? 'selected' : ''}>${o.label}</option>`
    ).join('');

    body.innerHTML = `
        <div class="settings-tabs">
            <button class="settings-tab active" data-tab="aparencia" onclick="switchSettingsTab('aparencia')">🎨 Aparência</button>
            <button class="settings-tab" data-tab="api" onclick="switchSettingsTab('api')">🔑 API</button>
            <button class="settings-tab" data-tab="fontes" onclick="switchSettingsTab('fontes')">📡 Fontes</button>
            <button class="settings-tab" data-tab="video" onclick="switchSettingsTab('video')">🎬 Vídeo</button>
            <button class="settings-tab" data-tab="audio" onclick="switchSettingsTab('audio')">🎵 Áudio</button>
            <button class="settings-tab" data-tab="imagem" onclick="switchSettingsTab('imagem')">🖼️ Imagem</button>
            <button class="settings-tab" data-tab="agentes" onclick="switchSettingsTab('agentes')">🤖 Agentes</button>
        </div>

        <div class="settings-modal-scroll">
            <!-- Aba: Aparência -->
            <div class="settings-tab-content active" id="tab-aparencia">
                <div class="settings-agent-card">
                    <div class="settings-row">
                        <label>Tema</label>
                        <select class="s-theme">${themeSel(curTheme, THEME_OPTS)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Fonte</label>
                        <select class="s-font-scale">${themeSel(curFontScale, SCALE_OPTS)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Layout</label>
                        <select class="s-layout-scale">${themeSel(curLayoutScale, SCALE_OPTS)}</select>
                    </div>
                </div>
            </div>

            <!-- Aba: API -->
            <div class="settings-tab-content" id="tab-api">
                <div class="settings-agent-card api-keys-card">
                    <div class="settings-row">
                        <label>OpenRouter</label>
                        <input class="s-apikey-openrouter" type="password" value="${apiKey}" placeholder="sk-or-v1-...">
                        <button class="btn-icon" style="padding:2px 6px;font-size:10px" onclick="this.previousElementSibling.type=this.previousElementSibling.type==='password'?'text':'password'">👁️</button>
                    </div>
                    <div style="margin-top:6px;display:flex;gap:6px">
                        <button class="btn-rss-add" onclick="fetchModels()">🔄 Buscar Modelos</button>
                        <span id="modelStatus" style="font-size:10px;color:var(--text-secondary);align-self:center">${availableModels.length ? `${availableModels.length} modelos disponíveis` : ''}</span>
                    </div>
                </div>
            </div>

            <!-- Aba: Fontes e Notícias -->
            <div class="settings-tab-content" id="tab-fontes">
                <div class="settings-agent-card" data-role="_meta">
                    <div class="settings-row">
                        <label>Categoria</label>
                        <select class="s-news-category">${catSel(newsCategory, CATEGORY_OPTS)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Notícias</label>
                        <input class="s-news-count" type="range" min="1" max="20" value="${newsCount}"
                               oninput="document.getElementById('newsCountDisplay').textContent=this.value">
                        <span id="newsCountDisplay" style="min-width:24px;text-align:center;font-weight:700">${newsCount}</span>
                    </div>
                </div>
                <div class="settings-agent-card" data-role="_rss">
                    <div class="settings-agent-header">
                        <span class="emoji">📡</span>
                        <div class="info"><strong>Fontes RSS</strong><span>Feeds de notícias</span></div>
                    </div>
                    <div class="rss-list">
                        ${rssFeeds.map((url, i) => `
                            <div class="rss-item">
                                <span class="rss-url" title="${url}">${url}</span>
                                <button class="rss-remove" onclick="removeRssFeed(${i})">✕</button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="rss-add-row">
                        <input class="rss-input" id="rssInput" placeholder="https://exemplo.com/feed" onkeydown="if(event.key==='Enter')addRssFeed()">
                        <button class="btn-rss-add" onclick="addRssFeed()">+ Adicionar</button>
                    </div>
                </div>
            </div>

            <!-- Aba: Vídeo -->
            <div class="settings-tab-content" id="tab-video">
                <div class="settings-agent-card">
                    <div class="settings-row">
                        <label>Resolução</label>
                        <select class="s-vid-res">${RES_OPTS.map(r => `<option value="${r.w}x${r.h}" ${r.w === curRes.w && r.h === curRes.h ? 'selected' : ''}>${r.label}</option>`).join('')}</select>
                    </div>
                    <div class="settings-row">
                        <label>FPS</label>
                        <select class="s-vid-fps">${sel(video.fps || 30, FPS_OPTS)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Codec</label>
                        <select class="s-vid-codec">${sel(video.codec || 'libx264', CODEC_OPTS)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Bitrate</label>
                        <select class="s-vid-bitrate">${sel(video.bitrate || '5000k', AUDIO_BITRATES)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Formato</label>
                        <select class="s-vid-format">${sel(video.format || 'mp4', VID_FORMATS)}</select>
                    </div>
                </div>
            </div>

            <!-- Aba: Áudio -->
            <div class="settings-tab-content" id="tab-audio">
                <div class="settings-agent-card">
                    <div class="settings-row">
                        <label>Taxa (Hz)</label>
                        <select class="s-aud-samplerate">${sel(audio.sample_rate || 44100, SAMPLERATES)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Bitrate</label>
                        <select class="s-aud-bitrate">${sel(audio.bitrate || '192k', AUDIO_BITRATES)}</select>
                    </div>
                    <div class="settings-row">
                        <label>Codec</label>
                        <select class="s-aud-codec">
                            <option value="aac" ${(audio.codec||'aac')==='aac'?'selected':''}>AAC</option>
                            <option value="mp3" ${audio.codec==='mp3'?'selected':''}>MP3</option>
                            <option value="opus" ${audio.codec==='opus'?'selected':''}>Opus</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <label>Canais</label>
                        <select class="s-aud-channels">
                            <option value="1" ${(audio.channels||2)===1?'selected':''}>Mono</option>
                            <option value="2" ${(audio.channels||2)===2?'selected':''}>Estéreo</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Aba: Imagem -->
            <div class="settings-tab-content" id="tab-imagem">
                <div class="settings-agent-card">
                    <div class="settings-row">
                        <label>Resolução</label>
                        <select class="s-img-res">${RES_OPTS.map(r => `<option value="${r.w}x${r.h}" ${r.w === (image.width||1920) && r.h === (image.height||1080) ? 'selected' : ''}>${r.label}</option>`).join('')}</select>
                    </div>
                    <div class="settings-row">
                        <label>Formato</label>
                        <select class="s-img-format">${sel(image.format || 'jpg', IMG_FORMATS)}</select>
                    </div>
                </div>
            </div>

            <!-- Aba: Agentes -->
            <div class="settings-tab-content" id="tab-agentes">
                <p style="font-size:10px;color:var(--text-secondary);margin-bottom:8px">Selecione o modelo OpenRouter para cada agente. <strong>Salve as configurações</strong> após escolher.</p>
                ${agentCards}
            </div>
        </div>
    `;

    document.querySelectorAll('.settings-agent-card[data-role]:not([data-role^="_"])').forEach(card => {
        const role = card.dataset.role;
        if (isLocal(role)) return;
        const saved = getSavedModel(role);
        const sel = card.querySelector('.s-model');
        if (sel && saved && availableModels.includes(saved)) {
            sel.value = saved;
        } else if (sel && availableModels.length > 0) {
            sel.value = availableModels.includes('openai/gpt-4o-mini') ? 'openai/gpt-4o-mini' : availableModels[0];
        }
    });

    body.querySelectorAll('select').forEach(sel => {
        const cls = sel.className;
        const opts = Array.from(sel.options).map(o => ({ value: o.value, label: o.text }));
        const val = sel.value;
        const div = document.createElement('div');
        div.innerHTML = PixelSelect.render(opts, val);
        const pixel = div.firstElementChild;
        pixel.className = 'pixel-select ' + cls;
        pixel._options = opts;
        sel.parentNode.replaceChild(pixel, sel);
    });
}

function applyVisualSettings(theme, fontScale, layoutScale) {
    document.body.dataset.theme = theme;
    document.documentElement.style.setProperty('--font-scale', fontScale);
    document.documentElement.style.setProperty('--layout-scale', layoutScale);
}

function fetchModels() {
    const key = document.querySelector('.s-apikey-openrouter')?.value || '';
    if (!key) {
        document.getElementById('modelStatus').textContent = '⚠️ Insira a chave primeiro';
        return;
    }
    document.getElementById('modelStatus').textContent = '🔄 Buscando modelos...';
    tryAPI('update_settings_full', { openrouter_api_key: key });
    callAPI('fetch_available_models').then(models => {
        if (models && models.length) {
            document.getElementById('modelStatus').textContent = `✅ ${models.length} modelos disponíveis`;
            refreshSettings();
        } else {
            document.getElementById('modelStatus').textContent = '❌ Nenhum modelo encontrado';
        }
    }).catch(() => {
        document.getElementById('modelStatus').textContent = '❌ Erro ao buscar modelos';
    });
}

function addRssFeed() {
    const input = $('rssInput');
    const url = input.value.trim();
    if (!url) return;
    callAPI('add_rss_feed', url).then(ok => {
        if (ok) {
            input.value = '';
            refreshSettings();
        }
    });
}

function removeRssFeed(index) {
    callAPI('get_settings_full').then(full => {
        const feeds = full.rss_feeds || [];
        const url = feeds[index];
        if (url) {
            callAPI('remove_rss_feed', url).then(ok => {
                if (ok) refreshSettings();
            });
        }
    });
}

function refreshSettings() {
    callAPI('get_settings_full').then(s => {
        settingsCache = s;
        callAPI('get_providers_schema').then(schema => renderSettings(schema, s));
    });
}

function psVal(sel) {
    const el = document.querySelector(sel);
    if (!el) return '';
    return el.value !== undefined ? el.value : (el.dataset.value || '');
}

function testVoice() {
    stopTestAudio();
    const card = document.querySelector('.settings-agent-card[data-role="Artista de Voz"]');
    if (!card) return;
    const model = card.querySelector('.s-model')?.value || '';
    const voice = card.querySelector('.s-voice')?.value || 'pt-BR-FranciscaNeural';
    const text = 'Olá, esta é a nova voz do seu narrador. Como está soando?';
    const status = document.getElementById('voiceTestStatus');
    if (status) status.textContent = '🔄 Gerando áudio de teste...';
    tryAPI('test_voice', { text, voice, model }).then(res => {
        if (res && res.path) {
            if (status) status.textContent = '✅ Tocando...';
            const audioUrl = res.data || 'file://' + res.path;
            _currentTestAudio = new Audio(audioUrl);
            _currentTestAudio.play().then(() => {
                _currentTestAudio.onended = () => {
                    _currentTestAudio = null;
                    if (status) status.textContent = '✅ Teste concluído';
                };
            }).catch(e => {
                _currentTestAudio = null;
                if (status) status.textContent = '❌ Erro ao tocar: ' + e.message;
            });
        } else {
            if (status) status.textContent = '❌ ' + (res ? res.message : 'Falha ao gerar áudio');
        }
    }).catch(() => {
        if (status) status.textContent = '❌ Erro na requisição';
    });
}

function fireAgent(role) {
    if (!confirm(`🔥 Tem certeza que deseja demitir ${role}?`)) return;
    callAPI('fire_agent', { role }).then(ok => {
        if (ok) {
            addLog(`🔥 <strong>${role}</strong> foi demitido.`, 'error');
            refreshSettings();
        }
    });
}

function saveSettings() {
    const body = $('settingsBody');
    const payload = { video: {}, audio: {}, image: {} };

    const theme = psVal('.s-theme') || 'default';
    const fontScale = parseFloat(psVal('.s-font-scale')) || 1.0;
    const layoutScale = parseFloat(psVal('.s-layout-scale')) || 1.0;
    payload.theme = theme;
    payload.font_scale = fontScale;
    payload.layout_scale = layoutScale;
    applyVisualSettings(theme, fontScale, layoutScale);

    const apiKey = body.querySelector('.s-apikey-openrouter')?.value || '';
    if (apiKey) payload.openrouter_api_key = apiKey;

    body.querySelectorAll('.settings-agent-card').forEach(card => {
        const role = card.dataset.role;
        if (role === '_meta') {
            const nc = parseInt(card.querySelector('.s-news-count')?.value) || 5;
            const cat = card.querySelector('.s-news-category')?.value || 'Tecnologia';
            payload.news_count = nc;
            payload.news_category = cat;
            tryAPI('update_agent_config', '_meta', { news_count: nc, news_category: cat });
        }
        if (role && !role.startsWith('_')) {
            const modelEl = card.querySelector('.s-model');
            let model = modelEl ? modelEl.value : '';
            const temp = parseFloat(card.querySelector('.s-temp')?.value) || 0.7;
            const isLocal = !modelEl || !model;
            if (!isLocal && !model) {
                model = pickFreeModel(role);
                if (modelEl) modelEl.value = model;
            }
            const cfg = isLocal ? { provider: 'local', model: 'moviepy' } : { model, temperature: temp, provider: 'openrouter' };
            card.querySelectorAll('[class^="s-"], [class*=" s-"]').forEach(el => {
                const cls = el.className.split(' ').find(c => c.startsWith('s-')) || '';
                if (cls === 's-model' || cls === 's-temp') return;
                if (cls) {
                    if (el.type === 'checkbox') {
                        cfg[cls.substring(2)] = el.checked;
                    } else {
                        cfg[cls.substring(2)] = el.value || el.dataset.value || '';
                    }
                }
            });
            tryAPI('update_agent_config', role, cfg);
        }
    });

    const vRes = (psVal('.s-vid-res') || '1920x1080').split('x');
    payload.video = {
        width: parseInt(vRes[0]), height: parseInt(vRes[1]),
        fps: parseInt(psVal('.s-vid-fps')) || 30,
        codec: psVal('.s-vid-codec') || 'libx264',
        bitrate: psVal('.s-vid-bitrate') || '5000k',
        format: psVal('.s-vid-format') || 'mp4',
    };
    payload.audio = {
        sample_rate: parseInt(psVal('.s-aud-samplerate')) || 44100,
        bitrate: psVal('.s-aud-bitrate') || '192k',
        codec: psVal('.s-aud-codec') || 'aac',
        channels: parseInt(psVal('.s-aud-channels')) || 2,
    };
    const iRes = (psVal('.s-img-res') || '1920x1080').split('x');
    payload.image = {
        width: parseInt(iRes[0]), height: parseInt(iRes[1]),
        format: psVal('.s-img-format') || 'jpg',
    };

    tryAPI('update_settings_full', payload);
    $('settingsModal').classList.remove('show');
}

document.addEventListener('DOMContentLoaded', () => {
    updateCompanyUI();
    checkBridge();
    callAPI('get_settings_full').then(s => {
        applyVisualSettings(
            s.theme || 'default',
            s.font_scale || 1.0,
            s.layout_scale || 1.0
        );
    }).catch(() => {});
    callAPI('get_agents_status').then(agents => {
        if (agents) agents.forEach(a => {
            const k = AGENT_KEYS[a.role];
            if (k) updateAgentStatus(k, a.status, a.hired);
        });
    });
    setInterval(() => {
        const now = new Date();
        $('clock').textContent = now.toTimeString().split(' ')[0];
        $('companyTime').textContent = now.toLocaleDateString('pt-BR') + ' ' + now.toTimeString().split(' ')[0];
    }, 1000);
});
