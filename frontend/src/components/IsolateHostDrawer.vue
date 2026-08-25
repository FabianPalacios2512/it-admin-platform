<template>
  <transition
    enter-active-class="transition-opacity duration-300 ease-in-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-200 ease-in-out"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="open" class="fixed inset-0 bg-slate-900/40 z-[95]" @click="emit('close')"></div>
  </transition>

  <transition
    enter-active-class="transform transition ease-out duration-300"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transform transition ease-in duration-200"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="open"
      class="fixed inset-y-0 right-0 z-[100] w-[min(920px,94vw)] bg-white shadow-[-16px_0_40px_-12px_rgba(0,0,0,0.12)] flex flex-col"
    >
      <header class="shrink-0 px-6 pt-5 pb-0">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">{{ action === 'mac' ? 'Bloqueo MAC' : 'Cuarentena' }}</h2>
            <p class="mt-1 text-[12px] text-slate-500 max-w-xl">
              {{ action === 'mac'
                ? 'Usa la cuarentena nativa de FortiOS (user quarantine + drop). Corta la MAC, aísla la IP y cierra las sesiones vivas para que ping y navegación mueran ya.'
                : 'Capa 3: se aísla la IP actual en user/banned. El equipo pierde internet y LAN hasta que expire o lo liberes.' }}
            </p>
          </div>
          <button type="button" class="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg" @click="emit('close')">
            <i class="fas fa-xmark"></i>
          </button>
        </div>
        <div class="mt-4 flex gap-1 border-b border-slate-200/70">
          <button
            type="button"
            class="px-3 py-2.5 text-[11px] uppercase tracking-wide border-b-2"
            :class="action === 'quarantine' ? 'border-blue-600 text-slate-900 font-semibold' : 'border-transparent text-slate-500'"
            @click="action = 'quarantine'"
          >Cuarentena (IP)</button>
          <button
            type="button"
            class="px-3 py-2.5 text-[11px] uppercase tracking-wide border-b-2"
            :class="action === 'mac' ? 'border-blue-600 text-slate-900 font-semibold' : 'border-transparent text-slate-500'"
            @click="action = 'mac'"
          >Bloqueo MAC</button>
        </div>
      </header>

      <div class="flex-1 min-h-0 overflow-y-auto px-6 py-4">
        <div class="flex items-center gap-3 mb-3">
          <input
            v-model="hostQuery"
            type="text"
            placeholder="Buscar hostname, IP o MAC…"
            class="flex-1 px-0 py-2 text-sm font-mono text-slate-800 outline-none border-b border-slate-100 focus:border-slate-400"
          />
          <input
            v-if="action === 'mac'"
            v-model="manualMac"
            type="text"
            placeholder="MAC suelta AA:BB:…"
            class="w-52 px-0 py-2 text-sm font-mono text-slate-800 outline-none border-b border-slate-100 focus:border-slate-400"
          />
          <input
            v-else
            v-model="manualIp"
            type="text"
            placeholder="IP suelta 192.168.…"
            class="w-44 px-0 py-2 text-sm font-mono text-slate-800 outline-none border-b border-slate-100 focus:border-slate-400"
          />
        </div>

        <p v-if="inventoryLoading" class="text-xs text-slate-400 py-10 text-center">Cargando equipos de este FortiGate…</p>
        <p v-else-if="inventoryError" class="text-xs text-red-600 py-4">{{ inventoryError }}</p>
        <table v-else class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-100">
              <th class="py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Equipo</th>
              <th class="py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">IP</th>
              <th class="py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">MAC</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="host in filteredInventory"
              :key="host.key"
              class="border-b border-slate-50 hover:bg-slate-50/80 cursor-pointer"
              :class="selectedHost?.key === host.key ? 'bg-slate-50' : ''"
              @click="selectedHost = host"
            >
              <td class="py-2.5 pr-3 text-sm font-medium text-slate-800">{{ host.hostname || 'Sin nombre' }}</td>
              <td class="py-2.5 pr-3 font-mono text-xs text-slate-700">{{ host.ip || '—' }}</td>
              <td class="py-2.5 font-mono text-xs text-slate-500">{{ host.mac || '—' }}</td>
            </tr>
            <tr v-if="!filteredInventory.length">
              <td colspan="3" class="py-10 text-center text-sm text-slate-400">No hay equipos visibles en este FortiGate.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="shrink-0 px-6 py-4 border-t border-slate-100 flex flex-wrap items-center gap-3">
        <select
          v-if="action === 'quarantine'"
          v-model.number="duration"
          class="text-xs text-slate-700 bg-transparent outline-none"
        >
          <option v-for="opt in durations" :key="opt.seconds" :value="opt.seconds">{{ opt.label }}</option>
        </select>
        <input
          v-model="reason"
          type="text"
          placeholder="Motivo / ticket"
          class="flex-1 min-w-[140px] text-xs text-slate-700 outline-none"
        />
        <button type="button" class="text-xs font-medium text-slate-500 hover:text-slate-900" @click="emit('close')">Cancelar</button>
        <button
          type="button"
          :disabled="!canSubmit || processing"
          class="px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-40"
          @click="submit"
        >
          {{ processing ? 'Aplicando…' : (action === 'mac' ? 'Bloquear MAC' : 'Poner en cuarentena') }}
        </button>
      </footer>
    </aside>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import fortigateService from '../services/fortigate.service';

const props = defineProps({
  open: { type: Boolean, default: false },
  defaultAction: { type: String, default: 'quarantine' },
  defaultFirewallIp: { type: String, default: '' },
  liveHosts: { type: Array, default: () => [] },
  seedHost: { type: Object, default: null },
  processing: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'isolate']);

const durations = [
  { label: '15 minutos', seconds: 900 },
  { label: '1 hora', seconds: 3600 },
  { label: '8 horas', seconds: 28800 },
  { label: 'Permanente', seconds: 0 },
];

const action = ref('quarantine');
const hostQuery = ref('');
const selectedHost = ref(null);
const manualIp = ref('');
const manualMac = ref('');
const duration = ref(3600);
const reason = ref('');
const dhcpLeases = ref([]);
const inventoryLoading = ref(false);
const inventoryError = ref('');

const inventory = computed(() => {
  const byKey = new Map();
  const push = (row) => {
    const ip = String(row.ip || '').trim();
    const mac = normalizeMac(row.mac);
    const key = ip || mac;
    if (!key) return;
    const prev = byKey.get(key) || {};
    byKey.set(key, {
      key,
      ip: ip || prev.ip || '',
      mac: mac || prev.mac || '',
      hostname: row.hostname || prev.hostname || '',
    });
  };
  dhcpLeases.value.forEach((lease) => push({
    ip: lease.ip,
    mac: lease.mac,
    hostname: lease.hostname || lease.host || '',
  }));
  props.liveHosts.forEach((host) => push({
    ip: host.ip,
    mac: host.mac,
    hostname: host.label || host.hostname,
  }));
  return [...byKey.values()].sort((a, b) => String(a.hostname || a.ip).localeCompare(String(b.hostname || b.ip)));
});

const filteredInventory = computed(() => {
  const q = hostQuery.value.trim().toLowerCase();
  if (!q) return inventory.value;
  return inventory.value.filter((host) => (
    host.ip.toLowerCase().includes(q)
    || host.mac.toLowerCase().includes(q)
    || String(host.hostname || '').toLowerCase().includes(q)
  ));
});

const canSubmit = computed(() => {
  if (action.value === 'mac') {
    return Boolean(normalizeMac(manualMac.value) || selectedHost.value?.mac);
  }
  return Boolean(manualIp.value.trim() || selectedHost.value?.ip);
});

watch(() => props.open, (open) => {
  if (!open) return;
  action.value = props.defaultAction === 'mac' ? 'mac' : 'quarantine';
  duration.value = 3600;
  reason.value = '';
  applySeedHost();
  if (props.defaultFirewallIp) loadInventory(props.defaultFirewallIp);
});

watch(() => props.defaultFirewallIp, (ip) => {
  if (props.open && ip) loadInventory(ip);
});

async function loadInventory(ip) {
  inventoryLoading.value = true;
  inventoryError.value = '';
  dhcpLeases.value = [];
  try {
    const diag = await fortigateService.getDiagnostics(ip);
    dhcpLeases.value = Array.isArray(diag?.dhcp_leases) ? diag.dhcp_leases : [];
  } catch (error) {
    inventoryError.value = error.message || 'No se pudo leer el inventario de este FortiGate.';
  } finally {
    inventoryLoading.value = false;
    applySeedHost();
  }
}

function applySeedHost() {
  const seed = props.seedHost;
  if (!seed) {
    hostQuery.value = '';
    selectedHost.value = null;
    manualIp.value = '';
    manualMac.value = '';
    return;
  }
  const mac = normalizeMac(seed.mac);
  hostQuery.value = seed.hostname || seed.ip || mac;
  manualIp.value = String(seed.ip || '').trim();
  manualMac.value = mac;
  selectedHost.value = {
    key: seed.ip || mac,
    ip: String(seed.ip || '').trim(),
    mac,
    hostname: seed.hostname || '',
  };
}

function normalizeMac(value) {
  const hex = String(value || '').toLowerCase().replace(/[^0-9a-f]/g, '');
  if (hex.length !== 12) return '';
  return hex.match(/.{2}/g).join(':');
}

function submit() {
  if (!canSubmit.value) return;
  const host = selectedHost.value || {};
  emit('isolate', {
    action: action.value,
    firewallIp: props.defaultFirewallIp,
    ip: manualIp.value.trim() || host.ip || '',
    mac: normalizeMac(manualMac.value) || host.mac || '',
    hostname: host.hostname || '',
    duration: duration.value,
    reason: reason.value.trim(),
  });
}
</script>
