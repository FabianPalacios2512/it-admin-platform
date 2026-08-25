<template>
  <div class="overflow-x-auto w-full">
    <table class="w-full text-left border-collapse whitespace-nowrap">
      <thead class="bg-neutral-100 border-b border-neutral-300">
        <tr>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Origen</th>
          <th class="py-2.5 px-1 w-6"></th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Destino</th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Aplicación</th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">TX ↑</th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">RX ↓</th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">Sesión</th>
          <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-center">Estado</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading && !rows.length">
          <td colspan="8" class="py-12 text-center text-neutral-400">
            <i class="fas fa-circle-notch fa-spin mb-2 text-lg"></i>
            <p class="text-xs">Consultando sesiones reales del FortiGate…</p>
            <p class="text-[11px] mt-1">La primera lectura tarda unos segundos; luego se sirve desde caché.</p>
          </td>
        </tr>
        <tr v-else-if="error && !rows.length">
          <td colspan="8" class="py-10 text-center">
            <p class="text-xs text-red-600 font-medium">{{ error }}</p>
          </td>
        </tr>
        <tr
          v-for="row in rows"
          :key="row.id"
          class="border-b border-neutral-100 last:border-0 hover:bg-neutral-50/80 transition-colors cursor-pointer"
          :class="row.status === 'closed' ? 'opacity-40' : ''"
          @click="emit('select', row)"
        >
          <td class="py-2 px-3 align-top">
            <div class="font-mono text-sm font-semibold text-neutral-900">{{ row.srcIp }}</div>
            <div class="text-[11px] text-neutral-500 truncate max-w-[170px]">{{ row.srcUser || row.srcHost }}</div>
          </td>
          <td class="py-2 px-1 text-center text-neutral-300 align-top pt-3">
            <i class="fas fa-arrow-right text-[10px]"></i>
          </td>
          <td class="py-2 px-3 align-top">
            <div class="font-mono text-sm text-neutral-800">{{ row.dstIp }}</div>
            <div class="text-[11px] text-neutral-500 truncate max-w-[190px]">{{ row.dstHost }}</div>
          </td>
          <td class="py-2 px-3 align-top">
            <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-[11px] font-semibold" :class="appMeta(row.app).badge">
              <i :class="appMeta(row.app).icon" class="text-[11px]"></i>
              {{ row.app }}
            </span>
            <div v-if="row.risk && row.risk !== 'none'" class="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold" :class="row.risk === 'high' ? 'text-red-600' : 'text-amber-600'">
              <span class="w-1.5 h-1.5 rounded-full animate-pulse" :class="row.risk === 'high' ? 'bg-red-500' : 'bg-amber-500'"></span>
              {{ row.risk === 'high' ? 'Riesgo alto' : 'Riesgo medio' }}
            </div>
          </td>
          <td class="py-2 px-3 text-right font-mono text-sm text-neutral-600 align-top">{{ formatBytes(row.txBytes) }}</td>
          <td class="py-2 px-3 text-right font-mono text-sm font-semibold text-neutral-900 align-top">{{ formatBytes(row.rxBytes) }}</td>
          <td class="py-2 px-3 text-right font-mono text-xs text-neutral-500 align-top">{{ formatDuration(row.sessionSeconds) }}</td>
          <td class="py-2 px-3 text-center align-top">
            <span v-if="row.status === 'closed'" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-neutral-100 text-neutral-500 rounded-sm">Cerrada</span>
            <span v-else-if="row.blocked" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-red-50 text-red-600 border border-red-200 rounded-sm">Cuarentena</span>
            <span v-else class="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase text-emerald-700">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Activa
            </span>
          </td>
        </tr>
        <tr v-if="!loading && !error && !rows.length">
          <td colspan="8" class="py-10 text-center text-sm text-neutral-400">
            <i class="fas fa-search text-2xl mb-2 opacity-20 block"></i>
            {{ emptyMessage }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  emptyMessage: { type: String, default: 'La API no devolvió sesiones para este firewall.' },
});

const emit = defineEmits(['select']);

const KB = 1024;
const MB = 1024 ** 2;
const GB = 1024 ** 3;

const APP_CATALOG = {
  Steam: { icon: 'fab fa-steam', badge: 'bg-indigo-50 text-indigo-600' },
  'Windows Update': { icon: 'fab fa-microsoft', badge: 'bg-blue-50 text-blue-600' },
  'Microsoft 365': { icon: 'fab fa-microsoft', badge: 'bg-blue-50 text-blue-600' },
  Netflix: { icon: 'fas fa-film', badge: 'bg-red-50 text-red-600' },
  YouTube: { icon: 'fab fa-youtube', badge: 'bg-red-50 text-red-600' },
  Zoom: { icon: 'fas fa-video', badge: 'bg-sky-50 text-sky-600' },
  Dropbox: { icon: 'fab fa-dropbox', badge: 'bg-blue-50 text-blue-600' },
  Spotify: { icon: 'fab fa-spotify', badge: 'bg-emerald-50 text-emerald-600' },
  BitTorrent: { icon: 'fas fa-share-nodes', badge: 'bg-red-50 text-red-600' },
  TOR: { icon: 'fas fa-mask', badge: 'bg-amber-50 text-amber-600' },
  HTTPS: { icon: 'fas fa-lock', badge: 'bg-neutral-100 text-neutral-600' },
  Facebook: { icon: 'fab fa-facebook', badge: 'bg-blue-50 text-blue-600' },
  Instagram: { icon: 'fab fa-instagram', badge: 'bg-pink-50 text-pink-600' },
  DNS: { icon: 'fas fa-network-wired', badge: 'bg-neutral-100 text-neutral-600' },
  Discord: { icon: 'fab fa-discord', badge: 'bg-indigo-50 text-indigo-600' },
  Google: { icon: 'fab fa-google', badge: 'bg-red-50 text-red-600' },
  Cloudflare: { icon: 'fas fa-cloud', badge: 'bg-orange-50 text-orange-600' },
};

function appMeta(name) {
  const key = Object.keys(APP_CATALOG).find((k) => String(name || '').toLowerCase().includes(k.toLowerCase()));
  return (key && APP_CATALOG[key]) || { icon: 'fas fa-diagram-project', badge: 'bg-neutral-100 text-neutral-600' };
}

function formatBytes(bytes) {
  const n = Number(bytes) || 0;
  if (n >= GB) return `${(n / GB).toFixed(2)} GB`;
  if (n >= MB) return `${(n / MB).toFixed(1)} MB`;
  if (n >= KB) return `${(n / KB).toFixed(0)} KB`;
  return `${Math.round(n)} B`;
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}
</script>
