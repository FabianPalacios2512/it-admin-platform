<template>
  <div class="w-full flex flex-col gap-4">
    <!-- Tabla Principal -->
    <div class="bg-white rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] overflow-hidden flex-1 relative border border-slate-200">
      
      <!-- Search Toolbar -->
      <div class="px-4 py-3 border-b border-slate-100 flex justify-between items-center bg-white z-[2]">
        <div class="relative">
          <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          </span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Buscar por Nombre o IP..." 
            class="pl-9 pr-3 py-1.5 border border-slate-200 rounded-lg text-[13px] text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64 bg-slate-50 hover:bg-white transition-colors" 
          />
        </div>

        <button 
          @click="() => fetchFortigates(false)" 
          :disabled="isLoading"
          class="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all flex items-center gap-2"
        >
          <svg v-if="isLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <i v-else class="fas fa-sync-alt"></i>
          Actualizar Datos Reales
        </button>
      </div>
        <div class="overflow-x-auto w-full">
          <table class="w-full text-left border-collapse whitespace-nowrap">
            <thead class="sticky top-0 bg-slate-50 z-10 border-b border-slate-200 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <tr>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-left w-1/4">Servidor / Estado</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest w-1/6">Recursos</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center w-1/12">Sesiones</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center w-1/12">VPN IPsec</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center w-1/12">Seguridad</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center w-1/12">Alertas</th>
                <th class="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right w-1/6">Tráfico Total</th>
                <th class="py-3 px-4 w-8"></th>
              </tr>
            </thead>
            
            <tbody>
              <!-- Skeleton Loader (Skeleton State) -->
              <template v-if="isLoading && fortigates.length === 0">
                <tr v-for="i in 15" :key="'skel'+i" class="border-b border-slate-100 last:border-0">
                  <td class="py-3 px-4"><div class="h-4 w-1/2 bg-slate-200 rounded animate-pulse mb-2"></div><div class="h-3 w-1/3 bg-slate-200 rounded animate-pulse"></div></td>
                  <td class="py-3 px-4"><div class="h-2 w-full bg-slate-200 rounded animate-pulse mb-2"></div><div class="h-2 w-full bg-slate-200 rounded animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-6 w-10 bg-slate-200 rounded mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-5 w-12 bg-slate-200 rounded-full mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-4 w-6 bg-slate-200 rounded mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-4 w-6 bg-slate-200 rounded mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-right"><div class="h-4 w-20 bg-slate-200 rounded ml-auto animate-pulse"></div></td>
                  <td class="py-3 px-4"></td>
                </tr>
              </template>
              
              <!-- Data Rows -->
              <template v-else-if="filteredFortigates.length > 0">
                <tr 
                  v-for="fg in filteredFortigates" 
                  :key="fg.hostid" 
                  @click="openSidePanel(fg)"
                  class="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer group"
                  :class="fg.status === 'Offline' ? 'bg-red-50/30' : ''"
                >
                  <!-- Servidor / IP / Uptime -->
                  <td class="py-3 px-4">
                    <div class="flex items-center gap-3">
                      <div class="relative flex h-3 w-3">
                        <span v-if="fg.status === 'Online'" class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-emerald-400"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3" :class="fg.status === 'Online' ? 'bg-emerald-500' : 'bg-red-500'"></span>
                      </div>
                      <div class="flex flex-col">
                        <span class="font-bold text-slate-700 text-[13px]">{{ fg.hostname }}</span>
                        <div class="flex items-center gap-2 mt-0.5">
                          <span class="text-xs text-slate-400 font-mono">{{ fg.ip }}</span>
                          <span v-if="fg.metrics.uptime_str" class="text-[10px] text-gray-400">&bull; {{ fg.metrics.uptime_str }}</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <!-- Recursos (CPU y RAM Combinados) -->
                  <td class="py-3 px-4">
                    <div class="flex flex-col gap-2 w-full max-w-[120px]">
                      <!-- CPU Bar -->
                      <div class="flex items-center gap-2">
                        <span class="text-[9px] font-bold text-slate-400 w-6">CPU</span>
                        <div class="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div class="h-full rounded-full transition-all duration-500" :style="`width: ${fg.metrics.cpu}%`" :class="getProgressColor(fg.metrics.cpu)"></div>
                        </div>
                      </div>
                      <!-- RAM Bar -->
                      <div class="flex items-center gap-2">
                        <span class="text-[9px] font-bold text-slate-400 w-6">RAM</span>
                        <div class="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div class="h-full rounded-full transition-all duration-500" :style="`width: ${fg.metrics.ram}%`" :class="getProgressColor(fg.metrics.ram)"></div>
                        </div>
                      </div>
                    </div>
                  </td>

                  <!-- Sesiones Activas -->
                  <td class="py-3 px-4 text-center">
                    <div class="flex flex-col items-center justify-center">
                      <span class="text-[15px] font-bold text-slate-700 font-mono">{{ (fg.metrics.active_sessions || 0).toLocaleString() }}</span>
                    </div>
                  </td>

                  <!-- VPN IPsec -->
                  <td class="py-3 px-4 text-center">
                    <span v-if="fg.metrics.vpn_tunnels_up > 0" class="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-green-100 text-green-700 whitespace-nowrap">
                      {{ fg.metrics.vpn_tunnels_up }} UP
                    </span>
                    <span v-else class="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-400 whitespace-nowrap">
                      0 UP
                    </span>
                  </td>

                  <!-- Seguridad / IPS -->
                  <td class="py-3 px-4 text-center">
                    <div class="flex items-center justify-center gap-1.5">
                      <i class="fas fa-shield-alt" :class="fg.metrics.ips_blocked > 0 ? 'text-orange-500' : 'text-slate-300'"></i>
                      <span class="text-xs font-bold" :class="fg.metrics.ips_blocked > 0 ? 'text-orange-600' : 'text-slate-400'">
                        {{ (fg.metrics.ips_blocked || 0).toLocaleString() }}
                      </span>
                    </div>
                  </td>
                  
                  <!-- Alertas -->
                  <td class="py-2.5 px-4 text-center">
                    <div v-if="fg.metrics.alerts > 0" class="relative inline-flex items-center justify-center">
                      <i class="far fa-bell text-slate-400 text-[15px]"></i>
                      <span class="absolute -top-2 -right-2.5 bg-red-500 text-white text-[9px] font-bold px-1 rounded-full border-2 border-white shadow-sm">
                        {{ fg.metrics.alerts }}
                      </span>
                    </div>
                    <span v-else class="text-slate-300 font-bold">-</span>
                  </td>

                  <!-- Tráfico Total WAN (Main Table) -->
                  <td class="py-2.5 px-4 text-right">
                    <div class="flex flex-col gap-0.5 items-end font-mono text-[10px]">
                      <span class="text-emerald-500 flex items-center">
                        <i class="fas fa-arrow-down mr-1 text-[8px]"></i>{{ formatTraffic(getTotalTraffic(fg.metrics.interfaces).in) }}
                      </span>
                      <span class="text-rose-500 flex items-center">
                        <i class="fas fa-arrow-up mr-1 text-[8px]"></i>{{ formatTraffic(getTotalTraffic(fg.metrics.interfaces).out) }}
                      </span>
                    </div>
                  </td>
                  
                  <!-- Action Arrow (Hover only) -->
                  <td class="py-2.5 px-2 text-center text-slate-300">
                    <i class="fas fa-chevron-right opacity-0 group-hover:opacity-100 group-hover:text-blue-500 transition-all transform group-hover:translate-x-1"></i>
                  </td>
                </tr>
              </template>

              <!-- No Results -->
              <tr v-else>
                <td colspan="10" class="py-12 text-center text-slate-400">
                  <i class="fas fa-search text-3xl mb-3 opacity-20"></i>
                  <p class="text-sm font-medium">No se encontraron firewalls FortiGate con ese criterio.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Backdrop Overlay -->
    <transition name="fade">
      <div 
        v-if="selectedHost" 
        @click="closeSidePanel" 
        class="fixed inset-0 bg-slate-900/40 z-40 backdrop-blur-[2px]"
      ></div>
    </transition>

    <!-- Side Panel (Off-Canvas) -->
    <transition name="slide-right">
      <div 
        v-if="selectedHost" 
        class="fixed inset-y-0 right-0 z-50 w-full max-w-5xl bg-white shadow-2xl flex flex-col border-l border-slate-200"
      >
        <!-- Header -->
        <div class="px-6 py-5 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
              <span class="relative flex h-3 w-3">
                <span v-if="selectedHost.status === 'Online'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-3 w-3" :class="selectedHost.status === 'Online' ? 'bg-emerald-500' : 'bg-red-500'"></span>
              </span>
              {{ selectedHost.hostname }}
            </h2>
            <p class="text-xs text-slate-500 font-mono mt-1">{{ selectedHost.ip }}</p>
          </div>
          <button @click="closeSidePanel" class="text-slate-400 hover:text-slate-700 transition-colors p-2 rounded-full hover:bg-slate-200">
            <i class="fas fa-times text-lg"></i>
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          
          <!-- Grid Cards (Métricas Crudas) -->
          <div class="grid grid-cols-4 gap-4">
            <!-- Sesiones -->
            <div class="bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
              <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Sesiones Activas</h3>
              <p class="text-2xl font-black text-slate-700 font-mono">
                {{ selectedHost.metrics.active_sessions.toLocaleString() }}
              </p>
            </div>
            
            <!-- VPN -->
            <div class="bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
              <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Túneles VPN IPsec</h3>
              <div class="flex gap-2 items-center h-full">
                <div v-if="selectedHost.metrics.vpn.up > 0 || selectedHost.metrics.vpn.down === 0" class="flex flex-col items-center flex-1 bg-emerald-50 rounded-lg py-1 border border-emerald-100">
                  <span class="text-lg font-black text-emerald-600">{{ selectedHost.metrics.vpn.up }}</span>
                  <span class="text-[9px] font-bold text-emerald-500 uppercase">UP</span>
                </div>
                <div v-if="selectedHost.metrics.vpn.down > 0" class="flex flex-col items-center flex-1 bg-red-50 rounded-lg py-1 border border-red-100 animate-pulse">
                  <span class="text-lg font-black text-red-600">{{ selectedHost.metrics.vpn.down }}</span>
                  <span class="text-[9px] font-bold text-red-500 uppercase">DOWN</span>
                </div>
              </div>
            </div>
            
            <!-- Intrusiones -->
            <div class="bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
              <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Intrusiones Bloqueadas</h3>
              <p class="text-2xl font-black text-slate-700 font-mono">
                0 <span class="text-xs text-emerald-500 ml-1 font-normal">(Seguro)</span>
              </p>
            </div>
            
            <!-- Alertas Activas -->
            <div class="bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
              <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Alertas Críticas</h3>
              <p class="text-2xl font-black font-mono" :class="selectedHost.metrics.alerts > 0 ? 'text-red-500' : 'text-slate-700'">
                {{ selectedHost.metrics.alerts }}
              </p>
            </div>
          </div>

          <!-- Rendimiento de Red (ECharts Sparklines) -->
          <div>
            <h3 class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Rendimiento de Red</h3>
            <div v-if="selectedHost.metrics.interfaces && selectedHost.metrics.interfaces.length > 0" class="flex flex-col gap-4">
                <PortTrafficChart 
                  v-for="iface in selectedHost.metrics.interfaces" 
                  :key="iface.name" 
                  :port-name="iface.name"
                  :in-kbps="formatTrafficToNumber(iface.in_bps)"
                  :out-kbps="formatTrafficToNumber(iface.out_bps)"
                  :history-data="iface.history"
                />
            </div>
            <div v-else class="p-4 text-center text-xs text-slate-400 bg-white border border-slate-100 rounded-xl shadow-sm">
              Sin tráfico activo.
            </div>
          </div>
          
        </div>
      </div>
    </transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import zabbixService from '../services/zabbix.service';
import PortTrafficChart from '../components/PortTrafficChart.vue';

// Estado Reactivo Vacío (Hard Rule)
const fortigates = ref([]);
const isLoading = ref(false);
const searchQuery = ref('');
const selectedHost = ref(null);

// Acciones Side Panel
const openSidePanel = (host) => {
  selectedHost.value = host;
};

const closeSidePanel = () => {
  selectedHost.value = null;
};

// Computed: Filtrado reactivo por Nombre o IP
const filteredFortigates = computed(() => {
  if (!searchQuery.value) return fortigates.value;
  const q = searchQuery.value.toLowerCase();
  return fortigates.value.filter(fg => 
    fg.hostname.toLowerCase().includes(q) || 
    fg.ip.toLowerCase().includes(q)
  );
});

// Utilidad: Colores para las barras de progreso
const getProgressColor = (val) => {
  if (val >= 85) return 'bg-red-500';
  if (val >= 70) return 'bg-amber-500';
  return 'bg-emerald-500';
};

// Utilidad: Formatear bps a Number para Kbps
const formatTrafficToNumber = (bps) => {
  if (bps == null || isNaN(bps)) return 0;
  return Math.round(bps / 1000); // Devuelve solo el número en Kbps
};

// Utilidad: Formatear bps a String completo (ej. 10.5 Kbps o 1.2 Mbps)
const formatTraffic = (bps) => {
  if (bps == null || isNaN(bps)) return '0 Kbps';
  const kbps = bps / 1000;
  if (kbps >= 1000) return (kbps / 1000).toFixed(2) + ' Mbps';
  return kbps.toFixed(1) + ' Kbps';
};

// Computed: Total de tráfico para la tabla principal
const getTotalTraffic = (interfaces) => {
  if (!interfaces || interfaces.length === 0) return { in: 0, out: 0 };
  let inTotal = 0;
  let outTotal = 0;
  interfaces.forEach(i => {
    inTotal += i.in_bps || 0;
    outTotal += i.out_bps || 0;
  });
  return { in: inTotal, out: outTotal };
};

// Lógica: Carga asíncrona a la API de backend
const fetchFortigates = async (isSilent = false) => {
  if (!isSilent) isLoading.value = true;
  
  try {
    // LLAMADA REAL A LA API
    const data = await zabbixService.getFortigates();
    fortigates.value = data;

    // Sincronizar el panel lateral (Modal) para que se actualice sin "ruido"
    if (selectedHost.value) {
      const updatedHost = data.find(h => h.hostid === selectedHost.value.hostid);
      if (updatedHost) {
        selectedHost.value = updatedHost;
      }
    }

  } catch (error) {
    console.error("Error cargando datos de Zabbix:", error);
  } finally {
    if (!isSilent) isLoading.value = false;
  }
};

// Inicializar al montar el componente
let refreshInterval;

onMounted(() => {
  fetchFortigates(false);
  refreshInterval = setInterval(() => {
    fetchFortigates(true); // Refresco silencioso cada 30 segundos
  }, 30000); // 30 seconds
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped>
/* Asegurar que la tabla no rompa el contenedor en monitores pequeños */
table {
  border-spacing: 0;
}

/* Transiciones para Backdrop */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Transiciones para Slide Panel */
.slide-right-enter-active, .slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from, .slide-right-leave-to {
  transform: translateX(100%);
}
</style>
