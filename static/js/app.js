const API_BASE = '/api/v1';

// --- Utilidades ---
async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

function formatTimestamp(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('pt-BR', {
    weekday: 'short', month: '2-digit', day: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatTakeTimestamp(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp * 1000);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  const time = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (sameDay) return `Hoje, ${time}`;
  return `${date.toLocaleDateString('pt-BR')}, ${time}`;
}

function getHealthColorClass(value) {
  if (value < 75) return 'text-green-400';
  if (value < 90) return 'text-yellow-400';
  return 'text-red-500 font-bold';
}

// --- Saudabilidade ---
async function updateHealth() {
  try {
    const data = await api('/health');
    const set = (sel, text, value) => {
      const el = document.querySelector(sel);
      if (!el) return;
      el.textContent = text;
      el.className = 'font-semibold ' + getHealthColorClass(value);
    };
    set('#stat-load .value', data.load.toFixed(2), data.load * 10);
    set('#stat-mem .value', data.mem_usage.toFixed(1) + '%', data.mem_usage);
    set('#stat-disk .value', data.disk_usage.toFixed(1) + '%', data.disk_usage);
  } catch (e) { /* servidor ainda não respondeu */ }
}
setInterval(updateHealth, 60000);
updateHealth();

// --- Desligamento ---
async function shutdownSystem() {
  if (!confirm('Desligar o sistema agora?')) return;
  try { await api('/shutdown', { method: 'POST' }); }
  catch (e) { alert('Comando enviado.'); }
}

// --- Cabeçalho compartilhado ---
function renderHeader() {
  const header = document.getElementById('app-header');
  if (!header) return;
  const page = header.dataset.page || 'dashboard';

  const pills = `
    <div class="flex bg-card rounded-full border border-custom overflow-hidden text-xs font-mono font-medium text-gray-300">
      <div class="px-4 py-2 border-r border-custom flex items-center gap-2" id="stat-load" title="Carga do Sistema">
        <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path></svg>
        <span class="value font-semibold text-gray-300">--</span>
      </div>
      <div class="px-4 py-2 border-r border-custom flex items-center gap-2" id="stat-mem" title="Uso de Memória">
        <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
        <span class="value font-semibold text-gray-300">--%</span>
      </div>
      <div class="px-4 py-2 flex items-center gap-2" id="stat-disk" title="Espaço em Disco">
        <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
        <span class="value font-semibold text-gray-300">--%</span>
      </div>
    </div>`;

  const links = `
    <a href="/" class="text-sm font-medium ${page === 'dashboard' ? 'text-white' : 'text-gray-400 hover:text-white'} transition-colors">Painel</a>
    <a href="/sessions" class="text-sm font-medium ${page === 'sessions' || page === 'session-detail' ? 'text-white' : 'text-gray-400 hover:text-white'} transition-colors">Sessões</a>`;

  header.innerHTML = `
    <nav class="border-b border-custom bg-surface">
      <div class="max-w-7xl mx-auto px-4 md:px-6 h-20 flex items-center justify-between">
        <a href="/" class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-500">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path>
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold tracking-tight text-white">O Gravador Sem Cabeça</h1>
            <p class="text-xs text-gray-400 font-medium mt-0.5">Controle Remoto v1.0.4</p>
          </div>
        </a>

        <div class="hidden lg:flex items-center gap-6 ml-6">
          ${links}
        </div>

        <div class="flex items-center gap-4">
          ${pills}
          <button onclick="shutdownSystem()" class="bg-[#e53935] hover:bg-red-500 text-white font-semibold py-2 px-5 rounded-full text-sm transition-colors flex items-center gap-2 ml-2 shadow-[0_0_15px_rgba(229,57,53,0.3)]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
            Desligar Sistema
          </button>
        </div>
      </div>
      <div class="lg:hidden flex items-center gap-6 px-6 pb-3">
        ${links}
      </div>
    </nav>`;

  updateHealth();
}

document.addEventListener('DOMContentLoaded', renderHeader);
