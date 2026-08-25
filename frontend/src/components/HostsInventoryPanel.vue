<template>
  <div class="flex flex-col gap-5">
    <div class="w-full max-w-2xl bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex items-center gap-3">
      <i class="fas fa-magnifying-glass text-slate-400 text-[13px]"></i>
      <input
        v-model="hostSearch"
        type="text"
        placeholder="Buscar por IP, Hostname, MAC o Fabricante (ej. NVR, Hikvision, Windows)..."
        class="flex-1 bg-transparent text-sm text-slate-800 placeholder:text-slate-400 outline-none"
      />
    </div>

    <p v-if="loading" class="text-[13px] text-slate-400">Leyendo inventario de este FortiGate…</p>
    <p v-else-if="error" class="text-[13px] text-red-600">{{ error }}</p>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="border-b border-slate-200">
            <th class="text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-transparent py-3 pr-4">Dispositivo</th>
            <th class="text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-transparent py-3 pr-4">Identidad</th>
            <th class="text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-transparent py-3 pr-4">MAC Address</th>
            <th class="text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-transparent py-3 pr-4">Conexión</th>
            <th class="text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-transparent py-3 w-24"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="host in filteredHosts"
            :key="host.mac || host.ip"
            class="border-b border-slate-100 hover:bg-white transition-colors duration-150"
          >
            <td class="py-3 pr-4">
              <div class="text-[13px] font-semibold text-slate-900">{{ host.hostname || 'Sin nombre' }}</div>
              <div class="font-mono text-[12px] text-blue-600">{{ host.ip || '—' }}</div>
            </td>
            <td class="py-3 pr-4">
              <div class="flex items-start gap-2.5">
                <span class="mt-0.5 w-7 h-7 rounded-lg bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
                  <i :class="hostIcon(host)" class="text-[12px]"></i>
                </span>
                <div>
                  <div class="text-[13px] font-medium text-slate-800">{{ host.os || 'Sin perfilar' }}</div>
                  <div class="text-[12px] text-slate-400">{{ host.vendor || '—' }}</div>
                </div>
              </div>
            </td>
            <td class="py-3 pr-4 font-mono text-sm text-slate-500">{{ host.mac || '—' }}</td>
            <td class="py-3 pr-4 text-[13px] text-slate-600">{{ host.iface || '—' }}</td>
            <td class="py-3 text-right">
              <div class="relative inline-flex justify-end">
                <button
                  type="button"
                  class="hover:bg-slate-200 rounded p-1 text-slate-400"
                  title="Acciones"
                  @click.stop="toggleMenu(host)"
                >
                  <i class="fas fa-ellipsis-vertical text-[12px]"></i>
                </button>
                <div
                  v-if="openMenuMac === (host.mac || host.ip)"
                  class="absolute right-0 top-8 z-20 w-40 bg-white rounded-lg shadow-[0_8px_24px_-8px_rgba(0,0,0,0.18)] border border-slate-100 py-1"
                >
                  <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-[12px] text-slate-700 hover:bg-slate-50"
                    @click.stop="onViewTraffic(host)"
                  >
                    Ver tráfico
                  </button>
                  <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-[12px] text-red-600 hover:bg-red-50"
                    @click.stop="onIsolate(host)"
                  >
                    Aislar
                  </button>
                </div>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredHosts.length">
            <td colspan="5" class="py-12 text-center text-[13px] text-slate-400">
              {{ hostSearch.trim()
                ? `Ningún equipo coincide con “${hostSearch}”.`
                : 'Este FortiGate no reporta equipos en DHCP ni en device inventory.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import fortigateService from '../services/fortigate.service';

const props = defineProps({
  firewallIp: { type: String, default: '' },
});

const emit = defineEmits(['view-traffic', 'isolate']);

const hosts = ref([]);
const loading = ref(false);
const error = ref('');
const hostSearch = ref('');
const openMenuMac = ref('');

const filteredHosts = computed(() => {
  const q = hostSearch.value.trim().toLowerCase();
  if (!q) return hosts.value;
  return hosts.value.filter((host) => (
    String(host.hostname || '').toLowerCase().includes(q)
    || String(host.ip || '').toLowerCase().includes(q)
    || String(host.mac || '').toLowerCase().includes(q)
    || String(host.os || '').toLowerCase().includes(q)
    || String(host.vendor || '').toLowerCase().includes(q)
    || String(host.iface || '').toLowerCase().includes(q)
  ));
});

const hostCount = computed(() => hosts.value.length);

async function loadHosts() {
  if (!props.firewallIp) {
    hosts.value = [];
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const res = await fortigateService.getHosts(props.firewallIp);
    hosts.value = Array.isArray(res?.hosts) ? res.hosts : [];
  } catch (err) {
    hosts.value = [];
    error.value = err.message || 'No se pudo leer el inventario de este FortiGate.';
  } finally {
    loading.value = false;
  }
}

function hostIcon(host) {
  const blob = `${host.os} ${host.vendor} ${host.hostname}`.toLowerCase();
  if (/(hikvision|camera|nvr|ipcamera)/.test(blob)) return 'fas fa-video';
  if (/windows/.test(blob)) return 'fab fa-windows';
  if (/(apple|ios|iphone|mac)/.test(blob)) return 'fab fa-apple';
  if (/android/.test(blob)) return 'fab fa-android';
  if (/linux/.test(blob)) return 'fab fa-linux';
  if (/vmware|virtual/.test(blob)) return 'fas fa-server';
  return 'fas fa-desktop';
}

function toggleMenu(host) {
  const key = host.mac || host.ip;
  openMenuMac.value = openMenuMac.value === key ? '' : key;
}

function closeMenu() {
  openMenuMac.value = '';
}

function onViewTraffic(host) {
  closeMenu();
  emit('view-traffic', host);
}

function onIsolate(host) {
  closeMenu();
  emit('isolate', host);
}

watch(() => props.firewallIp, loadHosts, { immediate: true });
defineExpose({ hostCount, reload: loadHosts });

onMounted(() => document.addEventListener('click', closeMenu));
onUnmounted(() => document.removeEventListener('click', closeMenu));
</script>
