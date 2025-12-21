const API_BASE = '/api/v1';

// Lógica de Saúde do Sistema
function getHealthColorClass(value) {
    if (value < 75) return 'health-green';
    if (value < 90) return 'health-yellow';
    return 'health-red';
}

async function updateHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (!response.ok) return;
        const data = await response.json();

        // Atualiza Carga (Load) - Formatado 2 casas decimais
        const loadEl = document.querySelector('#stat-load .value');
        loadEl.textContent = data.load.toFixed(2);
        loadEl.className = 'value ' + getHealthColorClass(data.load * 10); // Escala arbitrária para cores no load se necessário

        // Atualiza Memória - 1 casa decimal + %
        const memEl = document.querySelector('#stat-mem .value');
        memEl.textContent = data.mem_usage.toFixed(1) + '%';
        memEl.className = 'value ' + getHealthColorClass(data.mem_usage);

        // Atualiza Disco - 1 casa decimal + %
        const diskEl = document.querySelector('#stat-disk .value');
        diskEl.textContent = data.disk_usage.toFixed(1) + '%';
        diskEl.className = 'value ' + getHealthColorClass(data.disk_usage);

    } catch (error) {
        console.error('Erro ao buscar saúde do sistema:', error);
    }
}

// Configura o intervalo de atualização (1 minuto = 60000ms)
setInterval(updateHealth, 60000);
updateHealth(); // Executa imediatamente ao carregar

// --- Lógica Restante do Sistema ---
const select = document.getElementById('deviceSelect');
const btnRecord = document.getElementById('btnRecord');
const statusMsg = document.getElementById('statusMsg');
const lastRecordResult = document.getElementById('lastRecordResult');
const tableBodyRecordings = document.querySelector('#recordingsTable tbody');
const tableBodyHistory = document.querySelector('#historyTable tbody');

const STATE_ICONS = {
    'recording': '<span class="text-lg leading-none state-recording">🔴</span>',
    'new': '<span class="text-lg leading-none state-new">🟡</span>',
    'stopped': '<span class="text-lg leading-none state-stopped">✅</span>'
};

function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp * 1000); 
    return date.toLocaleString('pt-BR', { weekday: 'short', month: '2-digit', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

async function shutdownSystem() {
    if (!confirm("Desligar o sistema agora?")) return;
    try { await fetch(`${API_BASE}/shutdown`, { method: 'POST' }); } 
    catch (e) { alert('Comando enviado.'); }
}

async function loadDevices() {
    try {
        const res = await fetch(`${API_BASE}/devices`);
        const data = await res.json();
        select.innerHTML = '<option value="" disabled selected>Selecione um dispositivo</option>'; 
        data.devices.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.name; opt.textContent = `${d.name}`;
            select.appendChild(opt);
        });
    } catch (e) { statusMsg.textContent = 'Erro ao carregar dispositivos.'; }
}

btnRecord.addEventListener('click', async () => {
    if (!select.value) return;
    btnRecord.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/record`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device: select.value })
        });
        if (res.ok) {
            const d = await res.json();
            lastRecordResult.innerHTML = `Gravação <strong>${d.id.substring(0,8)}</strong> iniciada.`;
            lastRecordResult.classList.remove('hidden');
            loadRecordings();
        }
    } finally { btnRecord.disabled = false; }
});

function createTableRow(rec, isHistory = false) {
    const tr = document.createElement('tr');
    tr.className = "hover:bg-gray-50 transition-colors";

    const tdAction = tr.insertCell();
    tdAction.className = 'px-4 py-3 flex justify-center items-center gap-2'; 

    const link = document.createElement('a');
    link.href = `/api/v1/result/${rec.id}`;
    link.className = 'w-9 h-9 flex items-center justify-center bg-cyan-50 text-cyan-600 rounded-lg border border-cyan-100 hover:bg-cyan-100';
    link.innerHTML = '⤓';
    tdAction.appendChild(link);
    
    if (!isHistory) {
        const btnStop = document.createElement('button');
        btnStop.innerHTML = '⏹';
        if (rec.state === 'recording') {
            btnStop.className = 'w-9 h-9 flex items-center justify-center bg-red-50 text-red-600 rounded-lg border border-red-100 hover:bg-red-100';
            btnStop.onclick = () => stopRecording(rec.id);
        } else {
            btnStop.className = 'w-9 h-9 flex items-center justify-center bg-gray-50 text-gray-400 rounded-lg cursor-not-allowed';
        }
        tdAction.appendChild(btnStop);
    }

    tr.insertCell().innerHTML = `<span class="px-4 py-3 text-sm font-mono text-gray-500">${rec.id.substring(0, 8)}</span>`;
    tr.insertCell().innerHTML = `<span class="px-4 py-3 text-sm font-medium">${rec.device_name}</span>`;
    tr.insertCell().innerHTML = `<span class="px-4 py-3 text-sm">${STATE_ICONS[rec.state] || rec.state}</span>`;
    tr.insertCell().innerHTML = `<span class="px-4 py-3 text-sm text-gray-400">${formatTimestamp(isHistory ? rec.last_modification : rec.created_at)}</span>`;
    
    return tr;
}

async function loadRecordings() {
    try {
        const res = await fetch(`${API_BASE}/recordings`);
        const data = await res.json();
        const list = data.recordings || data;
        tableBodyRecordings.innerHTML = '';
        list.sort((a,b) => b.created_at - a.created_at).forEach(r => tableBodyRecordings.appendChild(createTableRow(r, false)));
    } catch (e) {}
}

async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/history`);
        const data = await res.json();
        const list = data.history || data;
        tableBodyHistory.innerHTML = '';
        list.sort((a,b) => b.created_at - a.created_at).forEach(r => tableBodyHistory.appendChild(createTableRow(r, true)));
    } catch (e) {}
}

async function stopRecording(id) {
    await fetch(`${API_BASE}/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id }) 
    });
    loadRecordings(); loadHistory();
}

loadDevices(); loadRecordings(); loadHistory();