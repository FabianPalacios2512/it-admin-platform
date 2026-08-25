<template>
  <div class="w-full flex flex-col gap-4">
    <div v-if="!embedded" class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-neutral-900">Diagnóstico de aplicaciones</h1>
        <p class="text-xs text-neutral-500 mt-0.5">Cuando reportan que un sistema de la empresa está lento, no el tráfico genérico del FortiGate.</p>
      </div>
      <button
        type="button"
        @click="emit('refresh')"
        :disabled="isRefreshing"
        class="px-3 py-1.5 text-xs font-semibold border border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 rounded-sm inline-flex items-center gap-1.5"
      >
        <i class="fas fa-sync-alt text-[10px]" :class="isRefreshing ? 'fa-spin' : ''"></i>
        Actualizar
      </button>
    </div>

    <div class="bg-white border border-neutral-200 rounded-md shadow-sm overflow-hidden">
      <div class="px-4 py-3 border-b border-neutral-200 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="text-xs font-semibold uppercase tracking-wide text-neutral-800">Catálogo (tú lo cargas)</h2>
          <p class="text-[11px] text-neutral-500 mt-0.5">
            El sistema no adivina Adinfo ni el POS. Pega el dominio (acepta subdominios y rutas) o una IP si En vivo solo muestra IP.
          </p>
        </div>
        <button
          type="button"
          class="px-3 py-1.5 text-[11px] font-semibold border border-neutral-300 rounded-sm hover:bg-neutral-50"
          @click="showConfig = !showConfig"
        >{{ showConfig ? 'Ocultar formulario' : 'Agregar / editar' }}</button>
      </div>

      <div v-if="showConfig" class="p-4 grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-4 border-b border-neutral-100">
        <form class="space-y-3" @submit.prevent="saveForm">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-[11px] text-neutral-500 mb-1">Nombre de la app</span>
              <input v-model="form.name" type="text" required placeholder="105 POS Pro" class="w-full text-xs border border-neutral-300 rounded-sm px-2 py-1.5" />
            </label>
            <label class="block">
              <span class="block text-[11px] text-neutral-500 mb-1">Para qué es</span>
              <input v-model="form.role" type="text" placeholder="Punto de venta" class="w-full text-xs border border-neutral-300 rounded-sm px-2 py-1.5" />
            </label>
          </div>
          <label class="block">
            <span class="block text-[11px] text-neutral-500 mb-1">Dominios (uno por línea). Ejemplo: 105pos.pro</span>
            <textarea v-model="form.domains" rows="3" placeholder="105pos.pro" class="w-full text-xs font-mono border border-neutral-300 rounded-sm px-2 py-1.5"></textarea>
          </label>
          <label class="block">
            <span class="block text-[11px] text-neutral-500 mb-1">IPs (si En vivo no muestra el dominio, solo la IP)</span>
            <textarea v-model="form.ips" rows="2" placeholder="104.17.253.239" class="w-full text-xs font-mono border border-neutral-300 rounded-sm px-2 py-1.5"></textarea>
          </label>
          <div class="flex flex-wrap gap-2">
            <button type="submit" class="px-3 py-1.5 text-xs font-semibold bg-neutral-900 text-white rounded-sm">
              {{ form.id ? 'Guardar cambios' : 'Agregar aplicación' }}
            </button>
            <button v-if="form.id" type="button" class="px-3 py-1.5 text-xs font-semibold border border-neutral-300 rounded-sm" @click="resetForm">Cancelar edición</button>
          </div>
        </form>

        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500 mb-2">Destinos que sí se ven ahora en En vivo</div>
          <p class="text-[11px] text-neutral-500 mb-2">Si alguien ya abrió el POS y aquí no sale 105pos.pro, el FortiGate está mostrando otro host o una IP. Clic para cargarlo al formulario.</p>
          <div v-if="!liveDestinations.length" class="text-xs text-neutral-400 py-6 text-center border border-dashed border-neutral-200 rounded-sm">
            No hay destinos en esta ventana. Abre la app desde un PC detrás de este FortiGate y pulsa Actualizar.
          </div>
          <div v-else class="max-h-48 overflow-y-auto border border-neutral-200 rounded-sm divide-y divide-neutral-100">
            <button
              v-for="dest in liveDestinations"
              :key="dest.host"
              type="button"
              class="w-full text-left px-3 py-1.5 hover:bg-neutral-50 flex items-center justify-between gap-2"
              @click="addLiveDest(dest.host)"
            >
              <span class="font-mono text-[11px] text-neutral-800 truncate">{{ dest.host }}</span>
              <span class="text-[10px] text-neutral-400 shrink-0">{{ dest.sessions }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="bg-neutral-50 text-[10px] uppercase tracking-wider text-neutral-500">
              <th class="px-4 py-2 font-semibold">Aplicación</th>
              <th class="px-4 py-2 font-semibold">Se busca</th>
              <th class="px-4 py-2 w-28"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in catalog" :key="app.id" class="border-t border-neutral-100">
              <td class="px-4 py-2">
                <div class="text-xs font-semibold text-neutral-900">{{ app.name }}</div>
                <div class="text-[11px] text-neutral-500">{{ app.role || '—' }}</div>
              </td>
              <td class="px-4 py-2 font-mono text-[11px]" :class="(app.domains.length || app.ips.length) ? 'text-neutral-700' : 'text-amber-700'">
                {{ scopeLabel(app) }}
              </td>
              <td class="px-4 py-2 text-right whitespace-nowrap">
                <button type="button" class="text-[11px] font-semibold text-neutral-600 hover:text-neutral-900 mr-3" @click="editApp(app)">Editar</button>
                <button type="button" class="text-[11px] font-semibold text-red-600 hover:text-red-800" @click="deleteApp(app)">Quitar</button>
              </td>
            </tr>
            <tr v-if="!catalog.length">
              <td colspan="3" class="px-4 py-6 text-center text-xs text-neutral-400">No hay apps. Agrega Adinfo, Wolkvox, el POS, etc.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-200 rounded-md px-4 py-3 text-sm text-red-800">{{ error }}</div>

    <div v-else-if="!sessionsReady" class="flex flex-col items-center justify-center py-16 text-neutral-400 bg-white border border-neutral-200 rounded-md">
      <i class="fas fa-satellite-dish text-3xl mb-3 text-neutral-300"></i>
      <p class="text-sm font-medium text-neutral-600">Esperando telemetría de API...</p>
      <p class="text-xs mt-1">Mismas sesiones que En vivo. Sin filas ahí, no hay diagnóstico aquí.</p>
    </div>

    <template v-else>
      <p class="text-[11px] text-neutral-500">
        Elige la app del ticket. Aquí solo cuenta si hay sesión hacia ese dominio y cuánto mueve. El ranking de YouTube o radio no es salud del WAN.
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <button
          v-for="card in catalogCards"
          :key="card.id"
          type="button"
          class="text-left bg-white border rounded-md shadow-sm overflow-hidden transition-colors"
          :class="selectedId === card.id ? 'border-neutral-900' : 'border-neutral-200 hover:border-neutral-400'"
          @click="selectedId = card.id"
        >
          <header class="px-4 py-3 border-b border-neutral-100 flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h2 class="text-sm font-semibold text-neutral-900">{{ card.name }}</h2>
              <p class="text-[11px] text-neutral-500 mt-0.5">{{ card.role }}</p>
              <p class="mt-1 font-mono text-[10px]" :class="(card.domains?.length || card.ips?.length) ? 'text-neutral-500' : 'text-amber-700'">{{ scopeLabel(card) }}</p>
            </div>
            <span class="shrink-0 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm" :class="statusClass(card.verdict.code)">
              {{ card.verdict.label }}
            </span>
          </header>
          <div class="grid grid-cols-2 gap-px bg-neutral-100">
            <div class="bg-white px-4 py-3">
              <div class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">PCs usando esto</div>
              <div class="mt-1 font-mono text-xl font-semibold text-neutral-900">{{ card.hosts }}</div>
            </div>
            <div class="bg-white px-4 py-3">
              <div class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Consumo hacia la app</div>
              <div class="mt-1 font-mono text-xl font-semibold text-neutral-900">{{ formatBytes(card.bytes) }}</div>
            </div>
          </div>
          <p class="px-4 py-2.5 text-[11px] text-neutral-600 border-t border-neutral-100 leading-snug">{{ card.verdict.headline }}</p>
        </button>
      </div>

      <div v-if="selected" class="bg-white border border-neutral-200 rounded-md shadow-sm overflow-hidden">
        <div class="px-4 py-3 border-b border-neutral-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-semibold text-neutral-900">Diagnóstico · {{ selected.name }}</h3>
            <p class="text-[11px] text-neutral-500 mt-0.5">Respuesta para el ticket: “{{ selected.name }} está lento, revisa qué pasa”.</p>
          </div>
          <button type="button" class="text-[11px] font-semibold text-neutral-500 hover:text-neutral-800" @click="selectedId = ''">Cerrar</button>
        </div>

        <div class="px-4 py-4 border-b border-neutral-100 bg-neutral-50">
          <p class="text-sm text-neutral-800 leading-relaxed">{{ selected.verdict.detail }}</p>
        </div>

        <section>
            <h4 class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 border-b border-neutral-100">Quién está en {{ selected.name }} ahora</h4>
            <table class="w-full text-left">
              <thead>
                <tr class="text-[10px] uppercase tracking-wider text-neutral-400">
                  <th class="px-4 py-2 font-semibold">Equipo</th>
                  <th class="px-4 py-2 font-semibold">Destino</th>
                  <th class="px-4 py-2 font-semibold text-right">Consumo</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in selected.users" :key="row.id" class="border-t border-neutral-50">
                  <td class="px-4 py-2">
                    <div class="font-mono text-xs font-semibold text-neutral-900">{{ row.srcIp }}</div>
                    <div class="text-[11px] text-neutral-500">{{ row.srcUser || row.srcHost || '—' }}</div>
                  </td>
                  <td class="px-4 py-2 font-mono text-[11px] text-neutral-700">{{ row.dstIp }}</td>
                  <td class="px-4 py-2 text-right font-mono text-xs text-neutral-800">{{ formatBytes(row.txBytes + row.rxBytes) }}</td>
                </tr>
                <tr v-if="!selected.users.length">
                  <td colspan="3" class="px-4 py-8 text-center text-xs text-neutral-400">Nadie de este FortiGate tiene sesión abierta hacia {{ selected.name }}.</td>
                </tr>
              </tbody>
            </table>
          </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import {
  catalog,
  upsertApp,
  removeApp,
  sessionMatchesApp,
  scopeLabel,
  sessionHosts,
} from '../config/businessSaas';

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  isRefreshing: { type: Boolean, default: false },
  error: { type: String, default: '' },
  embedded: { type: Boolean, default: false },
  hasLoaded: { type: Boolean, default: false },
});

const emit = defineEmits(['refresh']);
const selectedId = ref('');
const showConfig = ref(false);
const form = ref({ id: '', name: '', role: '', domains: '', ips: '' });

const KB = 1024;
const MB = 1024 ** 2;
const GB = 1024 ** 3;

const sessionsReady = computed(() => props.hasLoaded || props.sessions.length > 0);
const liveSessions = computed(() => (props.sessions || []).filter((row) => row.status !== 'closed'));

const liveDestinations = computed(() => {
  const groups = new Map();
  for (const row of liveSessions.value) {
    for (const host of sessionHosts(row)) {
      if (!groups.has(host)) groups.set(host, 0);
      groups.set(host, groups.get(host) + 1);
    }
  }
  return [...groups.entries()]
    .map(([host, sessions]) => ({ host, sessions }))
    .sort((a, b) => b.sessions - a.sessions)
    .slice(0, 40);
});

function formatBytes(bytes) {
  const n = Number(bytes) || 0;
  if (n >= GB) return `${(n / GB).toFixed(2)} GB`;
  if (n >= MB) return `${(n / MB).toFixed(1)} MB`;
  if (n >= KB) return `${(n / KB).toFixed(0)} KB`;
  return `${Math.round(n)} B`;
}

function uniqueHosts(rows) {
  return new Set(rows.map((row) => row.srcIp).filter(Boolean)).size;
}

function bytesOf(rows) {
  return rows.reduce((sum, row) => sum + Number(row.txBytes || 0) + Number(row.rxBytes || 0), 0);
}

function diagnose(app, matched) {
  const hosts = uniqueHosts(matched);
  const bytes = bytesOf(matched);
  const hasScope = (app.domains || []).length || (app.ips || []).length;

  if (!hasScope) {
    return {
      code: 'idle',
      label: 'Sin configurar',
      headline: 'Falta el dominio o la IP.',
      detail: `Carga el dominio de ${app.name} (como 105pos.pro). Sin eso no se puede saber qué sesiones son de esta app.`,
    };
  }

  if (!matched.length) {
    return {
      code: 'idle',
      label: 'Sin tráfico',
      headline: 'Nadie tiene sesión abierta hacia este dominio ahora.',
      detail: `No hay conversación hacia ${scopeLabel(app)} en este FortiGate. Si el usuario dice que está lento, o no está saliendo por aquí, o el destino en En vivo es otra IP y hay que agregarla.`,
    };
  }

  return {
    code: 'ok',
    label: 'En uso',
    headline: `${hosts} PC(s) · ${formatBytes(bytes)} hacia la app.`,
    detail: `Hay sesión hacia ${app.name}. Eso solo dice que la red está llegando al destino, no si la app “va lenta” en el servidor. Si el ticket es lentitud con ${formatBytes(bytes)} de consumo, el cuello casi nunca es este FortiGate: mira esos PCs o el servicio del proveedor.`,
  };
}

const catalogCards = computed(() =>
  catalog.value.map((app) => {
    const matched = liveSessions.value.filter((row) => sessionMatchesApp(row, app));
    return {
      ...app,
      hosts: uniqueHosts(matched),
      bytes: bytesOf(matched),
      users: matched.slice().sort((a, b) => (b.txBytes + b.rxBytes) - (a.txBytes + a.rxBytes)),
      verdict: diagnose(app, matched),
    };
  })
);

const selected = computed(() => catalogCards.value.find((card) => card.id === selectedId.value) || null);

function statusClass(code) {
  if (code === 'idle') return 'bg-neutral-100 text-neutral-600';
  return 'bg-emerald-100 text-emerald-800 border border-emerald-200';
}

function resetForm() {
  form.value = { id: '', name: '', role: '', domains: '', ips: '' };
}

function editApp(app) {
  showConfig.value = true;
  form.value = {
    id: app.id,
    name: app.name,
    role: app.role,
    domains: (app.domains || []).join('\n'),
    ips: (app.ips || []).join('\n'),
  };
}

function saveForm() {
  const saved = upsertApp({
    id: form.value.id || undefined,
    name: form.value.name,
    role: form.value.role,
    domains: form.value.domains,
    ips: form.value.ips,
    labels: catalog.value.find((row) => row.id === form.value.id)?.labels || [],
  });
  selectedId.value = saved.id;
  resetForm();
}

function deleteApp(app) {
  if (!window.confirm(`¿Quitar ${app.name} del catálogo?`)) return;
  removeApp(app.id);
  if (selectedId.value === app.id) selectedId.value = '';
  if (form.value.id === app.id) resetForm();
}

function addLiveDest(host) {
  showConfig.value = true;
  const ipv4 = /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
  if (ipv4) {
    const current = form.value.ips ? `${form.value.ips}\n${host}` : host;
    form.value.ips = [...new Set(current.split(/\s+/).filter(Boolean))].join('\n');
  } else {
    const current = form.value.domains ? `${form.value.domains}\n${host}` : host;
    form.value.domains = [...new Set(current.split(/\s+/).filter(Boolean))].join('\n');
  }
}

watch(catalogCards, (cards) => {
  if (selectedId.value && !cards.some((card) => card.id === selectedId.value)) selectedId.value = '';
});
</script>
