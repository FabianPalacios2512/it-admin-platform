<template>
  <teleport to="body">
    <transition name="drawer">
      <div v-if="isOpen" class="fixed inset-0 z-[9999] flex justify-end">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/20" @click="$emit('close')"></div>
        <!-- Drawer Panel 75% ancho -->
        <div class="drawer-panel relative bg-white h-full w-[75vw] max-w-6xl shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden">

          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50 shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
                <i class="fas fa-phone-volume text-emerald-600 text-sm"></i>
              </div>
              <div>
                <h2 class="text-[13px] font-bold text-slate-800 tracking-wide leading-none">LLAMADAS ACTIVAS</h2>
                <p class="text-[10px] text-slate-400 font-mono mt-0.5">Asterisk · core show channels concise · Solo lectura</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-1.5 text-[10px] text-emerald-600 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>{{ calls.length }} canal{{ calls.length !== 1 ? 'es' : '' }}</span>
              </div>
              <span v-if="lastRefresh" class="text-[10px] text-slate-400 font-mono">{{ lastRefresh }}</span>
              <button @click="fetchCalls" :disabled="loading" class="text-slate-400 hover:text-blue-600 transition-colors p-2 rounded-lg hover:bg-blue-50 disabled:opacity-50" title="Refrescar">
                <i class="fas fa-sync-alt text-xs" :class="{ 'animate-spin': loading }"></i>
              </button>
              <button @click="$emit('close')" class="text-slate-400 hover:text-slate-600 transition-colors p-2 rounded-lg hover:bg-slate-100" title="Cerrar">
                <i class="fas fa-times text-sm"></i>
              </button>
            </div>
          </div>

          <!-- Leyenda de estados -->
          <div class="flex items-center gap-6 px-5 py-2 bg-slate-50/50 border-b border-slate-100 shrink-0 flex-wrap">
            <span class="text-[9px] font-bold uppercase tracking-widest text-slate-400">Estados:</span>
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-700">En curso</span>
              <span class="text-[9px] text-slate-500">Hablando activamente</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-100 text-amber-700">Sonando</span>
              <span class="text-[9px] text-slate-500">Timbrando, esperando respuesta</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-slate-100 text-slate-500">Cerrando</span>
              <span class="text-[9px] text-slate-500">Colgando / finalizando</span>
            </div>
          </div>

          <!-- KPI Bar -->
          <div v-if="calls.length > 0" class="grid grid-cols-4 border-b border-slate-100 bg-white shrink-0">
            <div v-for="stat in summaryStats" :key="stat.label" class="px-5 py-3 border-r border-slate-100 last:border-0">
              <div class="text-[9px] uppercase tracking-widest text-slate-400 font-bold mb-0.5">{{ stat.label }}</div>
              <div class="text-xl font-black tracking-tight" :class="stat.color">{{ stat.value }}</div>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="loading && calls.length === 0" class="flex-1 flex items-center justify-center">
            <div class="text-center">
              <div class="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p class="text-sm text-slate-500">Consultando canales en Asterisk...</p>
            </div>
          </div>

          <!-- Error -->
          <div v-else-if="error" class="flex-1 flex items-center justify-center px-6">
            <div class="text-center">
              <i class="fas fa-exclamation-triangle text-amber-400 text-3xl mb-3 block"></i>
              <p class="text-sm font-semibold text-slate-700 mb-1">No se pudo obtener la informacion</p>
              <p class="text-xs text-slate-500 mb-4">{{ error }}</p>
              <button @click="fetchCalls" class="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition-colors">
                <i class="fas fa-sync-alt mr-1.5"></i> Reintentar
              </button>
            </div>
          </div>

          <!-- Empty -->
          <div v-else-if="!loading && calls.length === 0" class="flex-1 flex items-center justify-center">
            <div class="text-center text-slate-400">
              <div class="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-phone-slash text-2xl opacity-40"></i>
              </div>
              <p class="text-sm font-semibold text-slate-600">Sin llamadas activas</p>
              <p class="text-xs text-slate-400 mt-1">No hay canales abiertos en este momento</p>
            </div>
          </div>

          <!-- Tabla -->
          <div v-else class="flex-1 overflow-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead class="sticky top-0 bg-slate-50 border-b border-slate-200 z-10">
                <tr>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Canal<span class="block text-[8px] font-normal text-slate-400 normal-case">ID en Asterisk</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Troncal<span class="block text-[8px] font-normal text-slate-400 normal-case">Linea SIP usada</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Num. que llama<span class="block text-[8px] font-normal text-slate-400 normal-case">CallerID</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Destino<span class="block text-[8px] font-normal text-slate-400 normal-case">Extension marcada</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Flujo<span class="block text-[8px] font-normal text-slate-400 normal-case">Contexto enrutamiento</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                    Accion<span class="block text-[8px] font-normal text-slate-400 normal-case">Que hace Asterisk</span>
                  </th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest text-right">Duracion</th>
                  <th class="py-2.5 px-4 text-[9px] font-bold text-slate-500 uppercase tracking-widest text-center">Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(call, idx) in sortedCalls"
                  :key="call.channel"
                  class="border-b border-slate-50 hover:bg-blue-50/30 transition-colors"
                  :class="idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/20'"
                >
                  <td class="py-2.5 px-4 font-mono text-[10px] text-slate-500">
                    <span class="truncate block max-w-[160px]" :title="call.channel">{{ shortChannel(call.channel) }}</span>
                  </td>
                  <td class="py-2.5 px-4">
                    <span class="px-2 py-0.5 rounded text-[9px] font-bold" :class="trunkBadgeClass(call.trunk)">{{ call.trunk }}</span>
                  </td>
                  <td class="py-2.5 px-4 font-mono text-[11px] text-slate-700 font-semibold">{{ call.callerid || '—' }}</td>
                  <td class="py-2.5 px-4 font-mono text-[11px] text-blue-600 font-bold">
                    {{ call.extension === 's' ? 'IVR' : (call.extension || '—') }}
                  </td>
                  <td class="py-2.5 px-4 text-[10px] text-slate-500">
                    <span class="truncate max-w-[120px] block" :title="call.context">{{ friendlyContext(call.context) }}</span>
                  </td>
                  <td class="py-2.5 px-4 text-[10px] text-slate-600">
                    <span class="font-medium">{{ friendlyApp(call.application) }}</span>
                    <span v-if="call.app_data && call.app_data !== '(Outgoing Line)'" class="block text-[8px] text-slate-400 truncate max-w-[120px]" :title="call.app_data">{{ call.app_data }}</span>
                  </td>
                  <td class="py-2.5 px-4 text-right">
                    <span class="font-mono text-[11px] font-bold" :class="durationClass(call.duration_sec)">{{ call.duration }}</span>
                  </td>
                  <td class="py-2.5 px-4 text-center">
                    <span class="px-2.5 py-1 rounded-full text-[9px] font-bold inline-flex items-center gap-1" :class="stateClass(call.state)">
                      <span class="w-1.5 h-1.5 rounded-full" :class="stateDot(call.state)"></span>
                      {{ friendlyState(call.state) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Footer -->
          <div class="px-5 py-2.5 border-t border-slate-100 bg-slate-50 text-[9px] text-slate-400 flex justify-between items-center shrink-0">
            <span><i class="fas fa-lock mr-1"></i> Solo lectura · No modifica nada en el PBX</span>
            <span v-if="lastRefresh"><i class="fas fa-clock mr-1"></i> Auto-refresh 15s · Ultima: {{ lastRefresh }}</span>
          </div>

        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';

const props = defineProps({ isOpen: { type: Boolean, default: false } });
const emit = defineEmits(['close']);

const calls = ref([]);
const loading = ref(false);
const error = ref(null);
const lastRefresh = ref('');
let refreshTimer = null;

const shortChannel = (ch) =>
  ch.replace(/^(?:SIP|PJSIP)\//i, '').replace(/-([a-f0-9]{7,})$/i, (_, h) => `-...${h.slice(-4)}`);

const friendlyContext = (ctx) => ({
  'from-trunk': 'Entrante troncal',
  'macro-dialout-trunk': 'Saliente troncal',
  'from-internal': 'Llamada interna',
  'from-ivr': 'Desde IVR',
  'ivr-4': 'IVR principal',
  'default': 'Predeterminado',
}[ctx] || ctx);

const friendlyApp = (app) => ({
  'Dial': 'Marcando',
  'AppDial': 'En llamada',
  'BackGround': 'Reproduciendo audio',
  'Playback': 'Reproduciendo audio',
  'Queue': 'En cola de espera',
  'AGI': 'Script IVR',
  'VoiceMail': 'Buzon de voz',
  'Hangup': 'Colgando',
  'Answer': 'Contestando',
}[app] || app);

const friendlyState = (state) => ({
  Up: 'En curso', Ring: 'Sonando', Down: 'Cerrando', Ringing: 'Sonando', 'On Hold': 'En espera'
}[state] || state);

const stateClass = (state) => {
  if (state === 'Up') return 'bg-emerald-100 text-emerald-700';
  if (state === 'Ring' || state === 'Ringing') return 'bg-amber-100 text-amber-700';
  if (state === 'Down') return 'bg-slate-100 text-slate-500';
  return 'bg-blue-100 text-blue-700';
};
const stateDot = (state) => {
  if (state === 'Up') return 'bg-emerald-500';
  if (state === 'Ring' || state === 'Ringing') return 'bg-amber-500 animate-pulse';
  return 'bg-slate-400';
};
const durationClass = (sec) => {
  if (sec > 3600) return 'text-red-500';
  if (sec > 1800) return 'text-amber-500';
  if (sec > 300) return 'text-slate-700';
  return 'text-emerald-600';
};
const trunkColors = ['bg-blue-100 text-blue-700','bg-purple-100 text-purple-700','bg-indigo-100 text-indigo-700','bg-teal-100 text-teal-700','bg-rose-100 text-rose-700'];
const trunkColorMap = {};
let trunkColorIdx = 0;
const trunkBadgeClass = (trunk) => {
  if (trunk === 'Interna' || trunk === '3519' || trunk === '190.145.227.29') return 'bg-slate-100 text-slate-600';
  if (!trunkColorMap[trunk]) { trunkColorMap[trunk] = trunkColors[trunkColorIdx++ % trunkColors.length]; }
  return trunkColorMap[trunk];
};

const sortedCalls = computed(() =>
  [...calls.value].sort((a, b) => {
    const order = { Up: 0, Ring: 1, Ringing: 1, Down: 2 };
    const oa = order[a.state] ?? 3, ob = order[b.state] ?? 3;
    return oa !== ob ? oa - ob : b.duration_sec - a.duration_sec;
  })
);

const summaryStats = computed(() => {
  const total = calls.value.length;
  const upCalls = calls.value.filter(c => c.state === 'Up').length;
  const ringing = calls.value.filter(c => c.state === 'Ring' || c.state === 'Ringing').length;
  const longest = calls.value.reduce((max, c) => c.duration_sec > max ? c.duration_sec : max, 0);
  const fmt = (s) => `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
  return [
    { label: 'Total canales', value: total, color: 'text-slate-800' },
    { label: 'En curso (hablando)', value: upCalls, color: 'text-emerald-600' },
    { label: 'Sonando (timbrando)', value: ringing, color: 'text-amber-500' },
    { label: 'Mas larga', value: longest ? fmt(longest) : '—', color: 'text-blue-600' },
  ];
});

const fetchCalls = async () => {
  loading.value = true;
  error.value = null;
  try {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/v1/zabbix/pbx/active-calls', {
      headers: { 'Authorization': `Bearer ${token}` },
      cache: 'no-store'
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`HTTP ${res.status}: ${txt.slice(0, 120)}`);
    }
    const data = await res.json();
    calls.value = data.calls || [];
    lastRefresh.value = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    console.error('[ActiveCallsDrawer] error:', e);
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

watch(() => props.isOpen, (open) => {
  if (open) {
    calls.value = [];
    error.value = null;
    fetchCalls();
    refreshTimer = setInterval(fetchCalls, 15000);
  } else {
    clearInterval(refreshTimer);
  }
});
onUnmounted(() => clearInterval(refreshTimer));
</script>

<style scoped>
.drawer-enter-active { transition: opacity 0.25s ease; }
.drawer-leave-active { transition: opacity 0.2s ease; }
.drawer-enter-active .drawer-panel { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-leave-active .drawer-panel { transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-enter-from { opacity: 0; }
.drawer-leave-to { opacity: 0; }
.drawer-enter-from .drawer-panel { transform: translateX(100%); }
.drawer-leave-to .drawer-panel { transform: translateX(100%); }
</style>
