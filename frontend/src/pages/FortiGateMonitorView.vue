<template>
  <div class="w-full flex flex-col gap-4">
    <!-- Widgets de resumen -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div class="bg-white border border-neutral-200 shadow-sm px-4 py-3 flex items-center justify-between">
        <div>
          <div class="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-500">Sesiones globales</div>
          <div class="mt-1 text-3xl font-semibold tracking-tight text-neutral-900 font-mono leading-none">
            {{ totalSessions.toLocaleString() }}
          </div>
          <div class="mt-1.5 text-[11px] text-neutral-400">Sesiones de firewall activas</div>
        </div>
        <div class="w-10 h-10 border border-neutral-200 bg-neutral-50 text-neutral-700 flex items-center justify-center">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z"/>
          </svg>
        </div>
      </div>

      <div class="bg-white border border-neutral-200 shadow-sm px-4 py-3 flex items-center justify-between">
        <div>
          <div class="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-500">Túneles VPN activos</div>
          <div class="mt-1 flex items-baseline gap-2">
            <span class="text-3xl font-semibold tracking-tight text-neutral-900 font-mono leading-none">{{ totalVpn }}</span>
            <span class="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">UP</span>
          </div>
          <div class="mt-1.5 text-[11px] text-neutral-400">IPsec en el parque FortiGate</div>
        </div>
        <div class="flex items-center gap-2">
          <span class="relative flex h-2.5 w-2.5">
            <span v-if="totalVpn > 0" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="totalVpn > 0 ? 'bg-emerald-600' : 'bg-neutral-300'"></span>
          </span>
        </div>
      </div>

      <div class="bg-white border border-neutral-200 shadow-sm px-4 py-3 min-h-[96px] flex flex-col">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-500">Tráfico WAN total</div>
            <div class="mt-1 flex items-baseline gap-3 font-mono text-xs">
              <span class="text-emerald-700">↓ {{ formatTraffic(totalWan.in) }}</span>
              <span class="text-neutral-600">↑ {{ formatTraffic(totalWan.out) }}</span>
            </div>
          </div>
        </div>
        <div class="flex-1 min-h-[52px] mt-1">
          <v-chart class="w-full h-[52px]" :option="wanTrendOption" autoresize />
        </div>
      </div>
    </div>

    <!-- Tabla Principal -->
    <div class="bg-white rounded-md shadow-sm flex-1 relative border border-neutral-200 overflow-hidden">
      
      <!-- Search Toolbar -->
      <div class="px-4 py-3 border-b border-neutral-200 flex justify-between items-center bg-white z-[2]">
        <div class="relative">
          <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-400">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          </span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Buscar por Nombre o IP..." 
            class="pl-9 pr-3 py-1.5 border border-neutral-300 rounded-sm text-[13px] text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-900 focus:border-neutral-900 w-64 bg-white transition-colors" 
          />
        </div>

        <button 
          @click="() => fetchFortigates(false)" 
          :disabled="isLoading"
          class="bg-neutral-900 hover:bg-black disabled:bg-neutral-400 text-white px-4 py-1.5 rounded-sm text-xs font-medium shadow-sm transition-all flex items-center gap-2"
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
          <table class="w-full text-left border-collapse whitespace-nowrap bg-white">
            <thead class="sticky top-0 bg-neutral-100 z-10 border-b border-neutral-300">
              <tr>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-left">Equipo</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">Estado</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">DHCP</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">CPU</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">RAM</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">Sesiones</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-center">VPN IPsec</th>
                <th class="py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider text-right w-1/6">Tráfico Total</th>
                <th class="py-3 px-4 w-8"></th>
              </tr>
            </thead>
            
            <tbody>
              <!-- Skeleton Loader (Skeleton State) -->
              <template v-if="isLoading && fortigates.length === 0">
                <tr v-for="i in 15" :key="'skel'+i" class="border-b border-neutral-100 last:border-0 bg-white">
                  <td class="py-3 px-4"><div class="h-4 w-1/2 bg-neutral-200 rounded-sm animate-pulse mb-2"></div><div class="h-3 w-1/3 bg-neutral-200 rounded-sm animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-4 w-12 bg-neutral-200 rounded-sm mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-4 w-6 bg-neutral-200 rounded-sm mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4"><div class="h-7 w-24 bg-neutral-200 rounded-sm animate-pulse mb-2"></div><div class="h-7 w-24 bg-neutral-200 rounded-sm animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-6 w-10 bg-neutral-200 rounded-sm mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-5 w-12 bg-neutral-200 rounded-sm mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-center"><div class="h-4 w-6 bg-neutral-200 rounded-sm mx-auto animate-pulse"></div></td>
                  <td class="py-3 px-4 text-right"><div class="h-4 w-20 bg-neutral-200 rounded-sm ml-auto animate-pulse"></div></td>
                  <td class="py-3 px-4"></td>
                </tr>
              </template>
              
              <!-- Data Rows -->
              <template v-else-if="paginatedFortigates.length > 0">
                <tr 
                  v-for="fg in paginatedFortigates" 
                  :key="fg.hostid" 
                  @click="openSidePanel(fg)"
                  class="bg-white border-b border-neutral-200 hover:bg-neutral-50 transition-colors cursor-pointer group"
                  :class="fg.status === 'Offline' ? 'bg-red-50/10' : ''"
                >
                  <!-- Equipo / IP / Uptime -->
                  <td class="py-3 px-4">
                    <div class="flex flex-col min-w-0">
                      <span class="font-semibold text-neutral-900 text-sm truncate">{{ fg.hostname }}</span>
                      <div class="flex items-center gap-2 mt-0.5">
                        <span class="text-xs text-neutral-500 font-mono">{{ fg.ip }}</span>
                        <span v-if="fg.metrics.uptime_str" class="text-[10px] text-neutral-400 uppercase tracking-wider">&bull; {{ fg.metrics.uptime_str }}</span>
                      </div>
                    </div>
                  </td>

                  <!-- Estado -->
                  <td class="py-3 px-4 text-center">
                    <span class="inline-flex items-center gap-1.5 text-xs font-semibold"
                      :class="fg.status === 'Online' ? 'text-emerald-700' : 'text-red-700'">
                      <span class="w-1.5 h-1.5 rounded-full" :class="fg.status === 'Online' ? 'bg-emerald-600' : 'bg-red-600'"></span>
                      {{ fg.status === 'Online' ? 'Activo' : 'Abajo' }}
                    </span>
                  </td>

                  <!-- DHCP Activos -->
                  <td class="py-3 px-4 text-center" @click.stop="openDhcpTab(fg)">
                    <div v-if="fg.dhcp_loading" class="animate-pulse flex items-center justify-center">
                      <div class="h-4 w-6 bg-neutral-200 rounded-sm"></div>
                    </div>
                    <button
                      v-else-if="fg.dhcp_count !== null && fg.dhcp_count !== '-'"
                      type="button"
                      class="text-xs tabular-nums"
                      :class="metricTone(fg.dhcp_count)"
                      title="Ver clientes DHCP en Diagnóstico Profundo"
                    >{{ fg.dhcp_count }}</button>
                    <span v-else class="text-neutral-300 text-xs" title="No disponible">-</span>
                  </td>

                  <!-- CPU -->
                  <td class="py-3 px-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                      <span class="w-10 shrink-0 font-mono text-[11px] text-neutral-800 text-right">{{ asPercent(fg.metrics.cpu) }}%</span>
                      <div v-if="fg.cpu_history?.length > 1" class="h-6 w-[80px] shrink-0">
                        <v-chart class="w-full h-full" :option="fg.cpuSparkOption || sparklineOption(fg.cpu_history, '#ea580c', 'rgba(234,88,12,0.35)')" />
                      </div>
                    </div>
                  </td>

                  <!-- RAM -->
                  <td class="py-3 px-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                      <span class="w-10 shrink-0 font-mono text-[11px] text-neutral-800 text-right">{{ asPercent(fg.metrics.ram) }}%</span>
                      <div v-if="fg.ram_history?.length > 1" class="h-6 w-[80px] shrink-0">
                        <v-chart class="w-full h-full" :option="fg.ramSparkOption || sparklineOption(fg.ram_history, '#059669', 'rgba(5,150,105,0.35)')" />
                      </div>
                    </div>
                  </td>

                  <!-- Sesiones Activas -->
                  <td class="py-3 px-4 text-center">
                    <span class="font-mono text-xs" :class="metricTone(fg.metrics?.active_sessions)">
                      {{ (fg.metrics?.active_sessions || 0).toLocaleString() }}
                    </span>
                  </td>

                  <!-- VPN IPsec -->
                  <td class="py-3 px-4 text-center">
                    <span class="inline-flex items-center gap-1.5 text-xs" :class="metricTone(fg.metrics.vpn_tunnels_up)">
                      <span class="w-1.5 h-1.5 rounded-full" :class="(fg.metrics.vpn_tunnels_up || 0) > 0 ? 'bg-emerald-600' : 'bg-neutral-300'"></span>
                      {{ fg.metrics.vpn_tunnels_up || 0 }} UP
                    </span>
                  </td>

                  <!-- Tráfico Total WAN (Main Table) -->
                  <td class="py-2.5 px-4 text-right">
                    <div class="flex flex-col gap-0.5 items-end font-mono text-xs">
                      <span class="text-emerald-700">↓ {{ formatTraffic(getTotalTraffic(fg.metrics.interfaces).in) }}</span>
                      <span class="text-neutral-600">↑ {{ formatTraffic(getTotalTraffic(fg.metrics.interfaces).out) }}</span>
                    </div>
                  </td>
                  
                  <!-- Action Arrow (Hover only) -->
                  <td class="py-2.5 px-2 text-center text-neutral-300">
                    <i class="fas fa-chevron-right opacity-0 group-hover:opacity-100 group-hover:text-neutral-900 transition-all transform group-hover:translate-x-1"></i>
                  </td>
                </tr>
              </template>

              <!-- No Results -->
              <tr v-else>
                <td colspan="9" class="py-12 text-center text-neutral-400">
                  <i class="fas fa-search text-3xl mb-3 opacity-20"></i>
                  <p class="text-sm font-medium">No se encontraron firewalls FortiGate con ese criterio.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Paginación UI -->
        <div class="px-6 py-4 border-t border-neutral-200 bg-neutral-50 flex items-center justify-between" v-if="totalPages > 1">
          <span class="text-sm text-neutral-500">
            Mostrando {{ (currentPage - 1) * itemsPerPage + 1 }} a 
            {{ Math.min(currentPage * itemsPerPage, filteredFortigates.length) }} de {{ filteredFortigates.length }}
          </span>
          
          <div class="flex items-center gap-1">
            <button 
              @click="currentPage > 1 ? currentPage-- : null"
              :disabled="currentPage === 1"
              class="p-1.5 rounded text-neutral-500 hover:bg-neutral-200 hover:text-neutral-700 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
            </button>
            
            <div class="flex items-center gap-1">
              <button 
                v-for="p in totalPages" 
                :key="p"
                @click="currentPage = p"
                class="w-8 h-8 rounded text-sm font-medium transition-colors"
                :class="currentPage === p ? 'bg-blue-50 text-blue-600' : 'text-neutral-600 hover:bg-neutral-200'"
              >
                {{ p }}
              </button>
            </div>

            <button 
              @click="currentPage < totalPages ? currentPage++ : null"
              :disabled="currentPage === totalPages"
              class="p-1.5 rounded text-neutral-500 hover:bg-neutral-200 hover:text-neutral-700 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
            </button>
          </div>
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
        class="fixed inset-y-0 right-0 z-50 w-full max-w-7xl bg-white shadow-2xl flex flex-col border-l border-slate-200"
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

        <!-- Tabs -->
        <div class="px-6 py-0 border-b border-slate-200 bg-slate-50 flex gap-6">
          <button 
            @click="openMonitorTab"
            class="py-3 px-1 border-b-2 text-xs font-bold transition-colors"
            :class="activeTab === 'monitor' ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          >
            <i class="fas fa-chart-line mr-1.5"></i> Rendimiento (Zabbix)
          </button>
          <button 
            @click="openAuditTab"
            class="py-3 px-1 border-b-2 text-xs font-bold transition-colors flex items-center gap-2"
            :class="activeTab === 'audit' ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          >
            <i class="fas fa-list-check"></i> Top Talkers
          </button>
          <button 
            @click="loadDiagnostics"
            class="py-3 px-1 border-b-2 text-xs font-bold transition-colors flex items-center gap-2"
            :class="activeTab === 'diagnostics' ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          >
            <i class="fas fa-microscope"></i> Diagnóstico Profundo (API)
            <i @click.stop="loadDiagnostics" class="fas fa-sync-alt ml-1 cursor-pointer hover:text-blue-500" title="Refrescar diagnósticos manualmente" :class="isLoadingDiagnostics ? 'fa-spin' : ''"></i>
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          
          <!-- TAB: Monitor -->
          <div v-if="activeTab === 'monitor'" class="space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 class="text-xs font-semibold text-slate-800 uppercase tracking-wide">Tráfico y auditoría</h3>
                <p class="text-[11px] text-slate-500 mt-0.5">
                  Zoom con la rueda o el slider. Clic en un pico para ver qué equipo y aplicación lo generó.
                </p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  @click="startLiveAudit"
                  class="px-3 py-1.5 text-[11px] font-semibold border"
                  :class="auditLive ? 'bg-emerald-600 text-white border-emerald-700' : 'bg-white text-slate-700 border-slate-300'"
                >
                  En vivo
                </button>
                <button
                  type="button"
                  @click="loadTrafficAudit(false)"
                  :disabled="isLoadingAudit"
                  class="px-3 py-1.5 text-[11px] font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  <i class="fas fa-sync-alt mr-1" :class="isLoadingAudit ? 'fa-spin' : ''"></i>
                  Auditar ahora
                </button>
              </div>
            </div>

            <div v-if="selectedHost.metrics.interfaces && selectedHost.metrics.interfaces.length > 0" class="grid grid-cols-1 xl:grid-cols-2 gap-3">
              <PortTrafficChart 
                v-for="iface in selectedHost.metrics.interfaces" 
                :key="iface.name" 
                :port-name="iface.name"
                :in-kbps="formatTrafficToNumber(iface.in_bps)"
                :out-kbps="formatTrafficToNumber(iface.out_bps)"
                :history-data="iface.history"
                @audit-at="auditChartWindow"
              />
            </div>
            <div v-else class="p-8 text-center text-xs text-slate-400 bg-white border border-slate-200 shadow-sm">
              <i class="fas fa-ethernet text-2xl text-slate-300 mb-2"></i>
              <p>Sin interfaces de red detectadas</p>
            </div>
          </div>
          
          <!-- TAB: Top Talkers · Auditoría en vivo -->
          <div v-else-if="activeTab === 'audit'" class="space-y-4">
            <div class="bg-white border border-slate-200 shadow-sm overflow-hidden">
              <div class="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-200">
                <div>
                  <div class="text-xs font-semibold text-slate-800 uppercase tracking-wide flex items-center gap-2">
                    <i class="fas fa-list-check text-slate-500"></i>
                    Top Talkers · Auditoría en vivo
                  </div>
                  <p class="text-[11px] text-slate-500 mt-0.5">
                    Clic en una fila para ver el detalle: página, bytes, hora de inicio y consumo.
                    <span> · {{ auditWindowLabel }}</span>
                    <span v-if="trafficAudit?.source"> · fuente {{ trafficAudit.cached ? `${trafficAudit.source} (caché)` : trafficAudit.source }}</span>
                    <span v-if="auditTalkers.length"> · {{ auditTalkers.length }} {{ auditTalkers.length === 1 ? 'fila' : 'filas' }}</span>
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex items-center gap-1.5 border border-slate-300 bg-white px-2 py-1">
                    <i class="fas fa-search text-[10px] text-slate-400"></i>
                    <input v-model="auditSearch" type="text" placeholder="Buscar IP, usuario, host o app…" class="w-52 bg-transparent outline-none text-[11px] text-slate-800 placeholder-slate-400" />
                  </div>
                  <button
                    type="button"
                    @click="loadTrafficAudit(auditLive, auditWindow.start, auditWindow.end)"
                    :disabled="isLoadingAudit"
                    class="px-2.5 py-1 text-[11px] font-semibold border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <i class="fas fa-sync-alt" :class="isLoadingAudit ? 'fa-spin' : ''"></i>
                  </button>
                  <button
                    type="button"
                    @click="auditLive ? stopLiveAudit() : startLiveAudit()"
                    class="px-2.5 py-1 text-[11px] font-semibold border inline-flex items-center gap-1.5"
                    :class="auditLive ? 'bg-emerald-600 text-white border-emerald-700' : 'bg-white text-slate-700 border-slate-300'"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="auditLive ? 'bg-white animate-pulse' : 'bg-slate-400'"></span>
                    {{ auditLive ? 'En vivo' : 'Pausado' }}
                  </button>
                </div>
              </div>
              <TrafficAuditTable
                :rows="filteredAuditTalkers"
                :loading="isLoadingAudit"
                :error="auditError"
                :empty-message="auditSearch ? 'Sin sesiones que coincidan con la búsqueda.' : 'La API no devolvió sesiones ni FortiView para este firewall.'"
                @select="openAuditDetail"
              />
            </div>

            <!-- Centro de Control: Cuarentena -->
            <div class="bg-white border border-slate-200 shadow-sm">
              <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200">
                <div>
                  <div class="text-xs font-semibold text-slate-800 uppercase tracking-wide flex items-center gap-2">
                    <i class="fas fa-ban text-red-600"></i>
                    Centro de Control · Cuarentena
                  </div>
                  <p class="text-[11px] text-slate-500 mt-0.5">Equipos bloqueados en este FortiGate (sin salida a red hasta que expire o los liberes).</p>
                </div>
                <button type="button" @click="loadBannedIps" class="px-2.5 py-1 text-[11px] font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50">
                  <i class="fas fa-sync-alt mr-1" :class="isLoadingBanned ? 'fa-spin' : ''"></i>
                  Refrescar
                </button>
              </div>
              <div v-if="!bannedIps.length" class="px-4 py-6 text-center text-[12px] text-slate-400">
                No hay equipos bloqueados ahora mismo.
              </div>
              <table v-else class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-red-50 border-b border-red-100">
                    <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-red-700">IP Bloqueada</th>
                    <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-red-700">Equipo</th>
                    <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-red-700">Expira</th>
                    <th class="px-3 py-2 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in bannedIps" :key="entry.ip" class="border-b border-slate-100">
                    <td class="px-3 py-2 text-[11px] font-mono font-semibold text-slate-800">{{ entry.ip }}</td>
                    <td class="px-3 py-2 text-[11px] text-slate-600">{{ hostnameForIp(entry.ip) }}</td>
                    <td class="px-3 py-2 text-[11px] text-slate-500">{{ banExpiryLabel(entry) }}</td>
                    <td class="px-3 py-2 text-right">
                      <button type="button" @click="unblockHost(entry.ip)" class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide border border-emerald-300 text-emerald-700 bg-white hover:bg-emerald-50">
                        Liberar
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- TAB: Diagnóstico Profundo -->
          <div v-else-if="activeTab === 'diagnostics'" class="space-y-6">
            <div v-if="isLoadingDiagnostics" class="flex flex-col items-center justify-center py-16 text-slate-400">
              <i class="fas fa-network-wired fa-fade text-4xl mb-4 text-blue-500"></i>
              <p class="text-sm font-bold text-slate-600">Conectando con FortiOS API...</p>
              <p class="text-xs mt-1">Sincronizando interfaces y tabla DHCP en tiempo real</p>
            </div>
            
            <div v-else-if="diagnosticsData" class="space-y-8">
              
              <!-- Segmentación -->
              <div>
                <h3 class="text-xs font-semibold text-slate-800 uppercase tracking-wide mb-3">
                  Topología Local (Subredes)
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  <div v-for="(seg, idx) in diagnosticsData.segments" :key="'seg'+idx" 
                       class="bg-white border border-slate-200 shadow-sm p-4 flex flex-col gap-3 hover:shadow-md transition-all group">
                    
                    <div class="flex justify-between items-start">
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center">
                          <i class="fas fa-ethernet text-base"></i>
                        </div>
                        <div class="flex flex-col gap-1">
                          <h4 class="font-semibold text-slate-900 text-sm">{{ seg.interface_alias || seg.interface.replace('port', 'Port ') }}</h4>
                          <div v-if="seg.type === 'connect'" class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                            <span class="text-[10px] text-slate-500 uppercase tracking-wide">Link Up</span>
                          </div>
                          <div v-else class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-slate-400"></div>
                            <span class="text-[10px] text-slate-500 uppercase tracking-wide">Static</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div class="border-t border-slate-100 pt-3 flex justify-between items-center">
                      <div>
                        <p class="text-[9px] text-slate-400 uppercase tracking-wider mb-0.5">Subred</p>
                        <p class="text-xs font-mono text-slate-800 font-medium">{{ seg.ip_mask }}</p>
                      </div>
                      <div class="text-right">
                        <p class="text-[9px] text-slate-400 uppercase tracking-wider mb-0.5">Gateway</p>
                        <p class="text-xs font-mono text-slate-600">{{ seg.gateway }}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div v-if="!diagnosticsData.segments || diagnosticsData.segments.length === 0" class="col-span-full py-8 text-center bg-slate-50 border border-slate-200">
                    <i class="fas fa-ethernet text-slate-300 text-2xl mb-2"></i>
                    <p class="text-xs text-slate-500">No se encontraron subredes locales.</p>
                  </div>
                </div>
              </div>

              <!-- Monitor DHCP -->
              <div class="flex flex-col">
                <div class="flex items-end justify-between mb-3">
                  <div>
                    <h3 class="text-xs font-semibold text-slate-800 uppercase tracking-wide">Monitor DHCP</h3>
                    <p class="text-[11px] text-slate-500 mt-0.5">
                      {{ dhcpSummary.total }} leases · {{ dhcpSummary.reserved }} reserved · {{ dhcpActionHint }}
                    </p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      @click="handleReservation"
                      :disabled="!canReserveDhcp || isSubmittingReservation"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium border border-slate-300 bg-white text-slate-800 disabled:text-slate-400 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                    >
                      <i class="fas fa-plus text-[9px] text-emerald-600"></i>
                      Reserve
                    </button>
                    <button
                      type="button"
                      @click="handleRevoke"
                      :disabled="!canRevokeDhcp || isRevokingLease"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium border border-slate-300 bg-white text-slate-800 disabled:text-slate-400 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                    >
                      <i v-if="isRevokingLease" class="fas fa-circle-notch fa-spin text-[9px]"></i>
                      <i v-else class="fas fa-undo text-[9px]"></i>
                      Revoke
                    </button>
                    <span v-if="selectedDhcpLeases.length" class="text-[11px] text-slate-600 font-medium px-2">{{ selectedDhcpLeases.length }} selected</span>
                  </div>
                </div>

                <div class="bg-white border border-slate-200 shadow-sm">
                  <div class="flex flex-wrap items-center gap-2 px-3 py-2 border-b border-slate-200 bg-slate-50">
                    <span
                      v-for="filter in dhcpFilters"
                      :key="filter.id"
                      class="inline-flex items-center gap-1.5 pl-2 pr-1 py-0.5 text-[11px] bg-white border border-slate-300 text-slate-700"
                    >
                      <span class="font-medium">{{ filterLabel(filter) }}</span>
                      <button type="button" class="w-4 h-4 text-slate-400 hover:text-slate-800" @click="removeDhcpFilter(filter.id)">×</button>
                    </span>
                    <div class="relative" ref="addFilterRef">
                      <button type="button" class="w-6 h-6 text-emerald-700 border border-slate-300 bg-white hover:bg-slate-50" @click="showAddFilter = !showAddFilter" title="Agregar filtro">+</button>
                      <div v-if="showAddFilter" class="absolute top-full left-0 mt-1 z-30 w-[320px] bg-white border border-slate-300 shadow-lg p-2.5">
                        <div class="grid grid-cols-3 gap-1.5 mb-2">
                          <select v-model="newDhcpFilter.field" class="border border-slate-300 bg-white text-[11px] px-1.5 py-1 text-slate-800">
                            <option v-for="opt in dhcpFilterFields" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
                          </select>
                          <select v-model="newDhcpFilter.op" class="border border-slate-300 bg-white text-[11px] px-1.5 py-1 text-slate-800">
                            <option value="eq">==</option>
                            <option value="neq">!=</option>
                            <option value="contains">contains</option>
                          </select>
                          <select v-if="newDhcpFilter.field === 'interface'" v-model="newDhcpFilter.value" class="border border-slate-300 bg-white text-[11px] px-1.5 py-1 text-slate-800">
                            <option value="">Puerto</option>
                            <option v-for="iface in dhcpInterfaceOptions" :key="iface" :value="iface">{{ iface }}</option>
                          </select>
                          <select v-else-if="newDhcpFilter.field === 'reserved'" v-model="newDhcpFilter.value" class="border border-slate-300 bg-white text-[11px] px-1.5 py-1 text-slate-800">
                            <option value="yes">Reserved</option>
                            <option value="no">Not reserved</option>
                          </select>
                          <input v-else v-model="newDhcpFilter.value" type="text" class="border border-slate-300 bg-white text-[11px] px-1.5 py-1 text-slate-800" placeholder="Valor" />
                        </div>
                        <div class="flex justify-between">
                          <button type="button" class="text-[11px] text-slate-500 hover:text-slate-800" @click="dhcpFilters = []">Quitar todos</button>
                          <button type="button" class="px-2 py-1 text-[11px] bg-emerald-600 text-white disabled:opacity-40" :disabled="!newDhcpFilter.value" @click="addDhcpFilter">Aplicar</button>
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-1.5 ml-auto border border-slate-300 bg-white px-2 py-1">
                      <i class="fas fa-search text-[10px] text-slate-400"></i>
                      <input v-model="dhcpSearchQuery" type="text" placeholder="Buscar host, IP o MAC" class="w-44 bg-transparent outline-none text-[11px] text-slate-800 placeholder-slate-400" />
                    </div>
                    <div class="relative" ref="columnPickerRef">
                      <button type="button" class="w-7 h-7 border border-slate-300 bg-white text-slate-500 hover:text-slate-800" @click="showColumnPicker = !showColumnPicker" title="Columnas">
                        <i class="fas fa-cog text-[11px]"></i>
                      </button>
                      <div v-if="showColumnPicker" class="absolute top-full right-0 mt-1 z-30 w-56 bg-white border border-slate-300 shadow-lg py-1">
                        <div class="px-2.5 py-1 text-[10px] uppercase tracking-wider text-slate-400">Columnas</div>
                        <label v-for="col in dhcpColumnDefs" :key="col.id" class="flex items-center gap-2 px-2.5 py-1 text-[11px] text-slate-700 hover:bg-slate-50">
                          <input type="checkbox" :checked="visibleDhcpColumns.includes(col.id)" @change="toggleDhcpColumn(col.id)" />
                          {{ col.label }}
                        </label>
                      </div>
                    </div>
                  </div>

                  <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                      <thead>
                        <tr class="bg-slate-100 border-b border-slate-300">
                          <th class="w-9 px-2 py-1.5 text-center border-r border-slate-200">
                            <input type="checkbox"
                              :checked="selectedDhcpLeases.length > 0 && selectedDhcpLeases.length === filteredAndSortedDhcpLeases.length"
                              @change="toggleAllDhcp" />
                          </th>
                          <th
                            v-for="col in visibleDhcpColumnDefs"
                            :key="col.id"
                            @click="sortDhcp(col.sort)"
                            class="px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 whitespace-nowrap border-r border-slate-200 last:border-r-0 cursor-pointer select-none"
                          >
                            {{ col.label }}
                            <i class="fas ml-1 text-slate-400" :class="dhcpSortColumn===col.sort ? (dhcpSortOrder==='asc' ? 'fa-sort-up' : 'fa-sort-down') : 'fa-sort'"></i>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="lease in filteredAndSortedDhcpLeases"
                          :key="lease.mac"
                          @click="toggleDhcpSelection(lease)"
                          class="border-b border-slate-100 cursor-pointer group"
                          :class="isDhcpSelected(lease) ? 'bg-emerald-50/70' : 'bg-white hover:bg-slate-50'"
                        >
                          <td class="px-2 py-2 text-center border-r border-slate-100" @click.stop>
                            <input type="checkbox" :checked="isDhcpSelected(lease)" @change="toggleDhcpSelection(lease)" />
                          </td>
                          <td v-if="isDhcpCol('hostname')" class="px-2.5 py-2 border-r border-slate-100">
                            <div class="flex items-center gap-2">
                              <div class="w-7 h-7 bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0">
                                <i class="text-slate-500 text-xs" :class="getDeviceIcon(lease.hostname, lease.vci)"></i>
                              </div>
                              <span class="text-[11px] text-slate-800 font-medium">{{ lease.hostname || 'Unknown Device' }}</span>
                            </div>
                          </td>
                          <td v-if="isDhcpCol('ip')" class="px-2.5 py-2 border-r border-slate-100">
                            <span class="text-[11px] font-mono text-slate-800 font-medium">{{ lease.ip }}</span>
                          </td>
                          <td v-if="isDhcpCol('interface')" class="px-2.5 py-2 border-r border-slate-100">
                            <div class="flex items-center gap-1.5">
                              <i class="fas fa-ethernet text-[9px] text-slate-400"></i>
                              <span class="text-[11px] font-mono text-slate-600">{{ lease.interface_alias || lease.interface }}</span>
                            </div>
                          </td>
                          <td v-if="isDhcpCol('status')" class="px-2.5 py-2 border-r border-slate-100">
                            <span class="inline-flex items-center gap-1.5 text-[10px] text-emerald-700 font-medium">
                              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              Active
                            </span>
                          </td>
                          <td v-if="isDhcpCol('mac')" class="px-2.5 py-2 border-r border-slate-100">
                            <span class="text-[10px] font-mono text-slate-600 tracking-tight">{{ lease.mac?.toUpperCase() }}</span>
                          </td>
                          <td v-if="isDhcpCol('reserved')" class="px-2.5 py-2 border-r border-slate-100">
                            <span v-if="lease.reserved" class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-semibold border border-emerald-300">
                              <i class="fas fa-lock text-[8px]"></i>
                              Reserved
                            </span>
                            <span v-else class="text-[11px] text-slate-400">—</span>
                          </td>
                          <td v-if="isDhcpCol('info')" class="px-2.5 py-2 border-r border-slate-100">
                            <div class="text-[10px] text-slate-500">
                              <span v-if="lease.vci" class="font-medium">{{ lease.vci }}</span>
                              <span v-else>—</span>
                            </div>
                          </td>
                          <td v-if="isDhcpCol('expires')" class="px-2.5 py-2">
                            <span class="text-[10px] font-mono text-slate-500">{{ formatUnixTime(lease.expire_time) }}</span>
                          </td>
                        </tr>
                        <tr v-if="filteredAndSortedDhcpLeases.length === 0">
                          <td :colspan="visibleDhcpColumns.length + 1" class="px-3 py-12 text-center">
                            <i class="fas fa-network-wired text-2xl text-slate-300 mb-2"></i>
                            <p class="text-xs text-slate-500">No se encontraron dispositivos con esos filtros.</p>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div class="px-3 py-1 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 text-right">
                    {{ filteredAndSortedDhcpLeases.length }} / {{ diagnosticsData?.dhcp_leases?.length || 0 }}
                  </div>
                </div>
              </div>


            </div>
          </div>
        </div>
      </div>
    </transition>
          
    <!-- DHCP Reservation Side Panel -->
    <transition name="slide-right">
      <div v-if="showReservationModal" class="fixed inset-y-0 right-0 z-[60] w-full max-w-2xl bg-white shadow-2xl flex flex-col border-l border-slate-200">
        
        <!-- Header -->
        <div class="px-6 py-4 border-b border-emerald-500 bg-white flex justify-between items-center">
          <h3 class="text-base font-semibold text-slate-800 border-b-2 border-emerald-600 pb-1">Create DHCP Reservation</h3>
          <button @click="showReservationModal = false" class="text-slate-400 hover:text-slate-600 transition-colors">
            <i class="fas fa-times text-lg"></i>
          </button>
        </div>
        
        <!-- Body -->
        <div class="p-8 flex-1 flex flex-col gap-6">
          <div class="grid grid-cols-[200px_1fr] items-center gap-4">
            <label class="text-sm text-slate-700">MAC Address</label>
            <input type="text" v-model="reservationForm.mac" disabled
                   class="w-full text-sm border border-slate-300 rounded px-3 py-1.5 bg-slate-50 text-slate-500 outline-none" />
          </div>
          
          <div class="grid grid-cols-[200px_1fr] items-center gap-4">
            <label class="text-sm text-slate-700">IP</label>
            <input type="text" v-model="reservationForm.ip" 
                   class="w-full text-sm border border-slate-300 rounded px-3 py-1.5 text-slate-700 focus:outline-none focus:border-emerald-500 transition-colors" />
          </div>
          
          <div class="grid grid-cols-[200px_1fr] items-center gap-4">
            <label class="text-sm text-slate-700">Create firewall address<br/>matching MAC</label>
            
            <!-- Fortinet style toggle -->
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="reservationForm.createFirewallAddress" class="sr-only peer">
              <div class="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>
        </div>
        
        <!-- Footer -->
        <div class="px-6 py-4 border-t border-slate-200 bg-white flex justify-center gap-3">
          <button @click="submitReservation" :disabled="isSubmittingReservation"
                  class="w-32 py-1.5 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 border border-emerald-700 rounded transition-colors flex items-center justify-center gap-2 disabled:opacity-50">
            <i v-if="isSubmittingReservation" class="fas fa-circle-notch fa-spin"></i>
            OK
          </button>
          <button @click="showReservationModal = false" :disabled="isSubmittingReservation"
                  class="w-32 py-1.5 text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 border border-slate-300 rounded transition-colors disabled:opacity-50">
            Cancel
          </button>
        </div>
        
      </div>
    </transition>

    <SessionDetailDrawer
      read-only
      :session="detailRow"
      :session-data="detail"
      :loading="detailLoading"
      :error="detailError"
      :chart-points="detailChartHistory"
      :duration-seconds="liveDuration"
      @close="closeAuditDetail"
    />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';
import zabbixService from '../services/zabbix.service';
import fortigateService from '../services/fortigate.service';
import PortTrafficChart from '../components/PortTrafficChart.vue';
import TrafficAuditTable from '../components/TrafficAuditTable.vue';
import SessionDetailDrawer from '../components/SessionDetailDrawer.vue';

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

const wave = (len, base, amp, seed) =>
  Array.from({ length: len }, (_, i) =>
    Math.max(0, Number((base + Math.sin((i + seed) * 0.45) * amp + ((i * 3 + seed) % 4) * 0.4).toFixed(1)))
  );

const mockData = {
  wanIn: wave(24, 9.2, 3.4, 1),
  wanOut: wave(24, 3.1, 1.6, 6),
  wanTimes: Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`)
};

const asPercent = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n > 100) return 0;
  return Math.round(n);
};

const toHistoryPoints = (raw) => {
  if (!Array.isArray(raw) || !raw.length) return [];
  return raw
    .map((v) => (typeof v === 'number' ? v : Number(v?.[1] ?? v?.value ?? 0)))
    .filter((n) => Number.isFinite(n) && n >= 0 && n <= 100);
};

const seedHistory = (incoming, previous, currentValue) => {
  let series = toHistoryPoints(incoming);
  if (series.length < 2) series = toHistoryPoints(previous);
  const val = asPercent(currentValue);
  if (series.length === 0 || series[series.length - 1] !== val) {
    if (Number(currentValue) >= 0 && Number(currentValue) <= 100) {
      series = [...series, val];
    }
  }
  return series.slice(-48);
};

// Estado Reactivo Vacío (Hard Rule)
const fortigates = ref([]);
const isLoading = ref(false);
const searchQuery = ref('');
const selectedHost = ref(null);
const activeTab = ref('monitor');
const diagnosticsData = ref(null);
const isLoadingDiagnostics = ref(false);
const trafficAudit = ref(null);
const isLoadingAudit = ref(false);
const auditError = ref('');
const auditLive = ref(false);
const auditSearch = ref('');
const auditWindow = ref({ start: null, end: null, label: '' });
let auditInterval = null;

const bannedIps = ref([]);
const isLoadingBanned = ref(false);
const blockMenuFor = ref(null);
const blockDurations = [
  { label: '5 min', seconds: 300 },
  { label: '30 min', seconds: 1800 },
  { label: '1 hora', seconds: 3600 },
  { label: '24 horas', seconds: 86400 },
  { label: 'Indefinido', seconds: 0 }
];

const DHCP_COLUMN_STORAGE = 'adinfra.dhcp.columns';
const dhcpColumnDefs = [
  { id: 'hostname', label: 'Device', sort: 'hostname' },
  { id: 'ip', label: 'IP', sort: 'ip' },
  { id: 'interface', label: 'Interface', sort: 'interface' },
  { id: 'status', label: 'Status', sort: 'status' },
  { id: 'mac', label: 'MAC', sort: 'mac' },
  { id: 'reserved', label: 'Reserved', sort: 'reserved' },
  { id: 'info', label: 'Host Information', sort: 'vci' },
  { id: 'expires', label: 'Expires', sort: 'expire_time' }
];
const dhcpFilterFields = [
  { id: 'interface', label: 'Interface' },
  { id: 'reserved', label: 'Reserved' },
  { id: 'hostname', label: 'Device' },
  { id: 'ip', label: 'IP' },
  { id: 'mac', label: 'MAC' }
];

const loadDhcpColumns = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(DHCP_COLUMN_STORAGE) || 'null');
    if (Array.isArray(raw) && raw.length) return raw.filter((id) => dhcpColumnDefs.some((c) => c.id === id));
  } catch (_) { /* ignore */ }
  return ['hostname', 'ip', 'interface', 'reserved', 'mac', 'expires'];
};

// Estado de la tabla DHCP
const dhcpSearchQuery = ref('');
const dhcpSortColumn = ref('ip');
const dhcpSortOrder = ref('asc');
const selectedDhcpLeases = ref([]);
const dhcpFilters = ref([]);
const visibleDhcpColumns = ref(loadDhcpColumns());
const showAddFilter = ref(false);
const showColumnPicker = ref(false);
const addFilterRef = ref(null);
const columnPickerRef = ref(null);
const newDhcpFilter = ref({ field: 'interface', op: 'eq', value: '' });

const visibleDhcpColumnDefs = computed(() =>
  dhcpColumnDefs.filter((col) => visibleDhcpColumns.value.includes(col.id))
);
const isDhcpCol = (id) => visibleDhcpColumns.value.includes(id);
const isDhcpSelected = (lease) => selectedDhcpLeases.value.some((l) => l.mac === lease.mac);

const toggleDhcpColumn = (id) => {
  const next = visibleDhcpColumns.value.includes(id)
    ? visibleDhcpColumns.value.filter((c) => c !== id)
    : [...visibleDhcpColumns.value, id];
  if (!next.length) return;
  visibleDhcpColumns.value = dhcpColumnDefs.map((c) => c.id).filter((c) => next.includes(c));
  localStorage.setItem(DHCP_COLUMN_STORAGE, JSON.stringify(visibleDhcpColumns.value));
};

const dhcpInterfaceOptions = computed(() => {
  const leases = diagnosticsData.value?.dhcp_leases || [];
  return [...new Set(leases.map((l) => l.interface_alias || l.interface).filter(Boolean))].sort();
});

const dhcpSummary = computed(() => {
  const leases = diagnosticsData.value?.dhcp_leases || [];
  return {
    total: leases.length,
    reserved: leases.filter((l) => l.reserved).length
  };
});

const canReserveDhcp = computed(() =>
  selectedDhcpLeases.value.length === 1 && !selectedDhcpLeases.value[0].reserved
);
const canRevokeDhcp = computed(() =>
  selectedDhcpLeases.value.some((l) => l.reserved)
);
const dhcpActionHint = computed(() => {
  if (canReserveDhcp.value) return 'Lease dinámico listo para reservar';
  if (canRevokeDhcp.value) return 'Revocar deja la IP otra vez en el pool';
  if (selectedDhcpLeases.value.length > 1) return 'Revoke admite varios. Reserve solo uno.';
  return 'Selecciona un lease para reservar o revocar';
});

const filterLabel = (filter) => {
  const field = dhcpFilterFields.find((f) => f.id === filter.field)?.label || filter.field;
  const op = filter.op === 'neq' ? '!=' : filter.op === 'contains' ? 'contains' : '==';
  const value = filter.field === 'reserved' ? (filter.value === 'yes' ? 'Reserved' : 'Not reserved') : filter.value;
  return `${field} ${op} ${value}`;
};

const addDhcpFilter = () => {
  if (!newDhcpFilter.value.value) return;
  dhcpFilters.value.push({
    id: `${Date.now()}`,
    field: newDhcpFilter.value.field,
    op: newDhcpFilter.value.op,
    value: newDhcpFilter.value.value
  });
  newDhcpFilter.value = { field: newDhcpFilter.value.field, op: 'eq', value: '' };
  showAddFilter.value = false;
};

const removeDhcpFilter = (id) => {
  dhcpFilters.value = dhcpFilters.value.filter((f) => f.id !== id);
};

const leaseFieldValue = (lease, field) => {
  if (field === 'interface') return (lease.interface_alias || lease.interface || '').toLowerCase();
  if (field === 'reserved') return lease.reserved ? 'yes' : 'no';
  if (field === 'mac') return (lease.mac || '').toLowerCase();
  if (field === 'ip') return (lease.ip || '').toLowerCase();
  return (lease.hostname || '').toLowerCase();
};

const matchesDhcpFilter = (lease, filter) => {
  const actual = leaseFieldValue(lease, filter.field);
  const expected = String(filter.value || '').toLowerCase();
  if (filter.op === 'neq') return actual !== expected;
  if (filter.op === 'contains') return actual.includes(expected);
  return actual === expected;
};

const toggleDhcpSelection = (lease) => {
  const idx = selectedDhcpLeases.value.findIndex(l => l.mac === lease.mac);
  if (idx > -1) {
    selectedDhcpLeases.value.splice(idx, 1);
  } else {
    selectedDhcpLeases.value.push(lease);
  }
};

// Modal de Reservación
const showReservationModal = ref(false);
const showReservationDropdown = ref(false);
const reservationDropdownRef = ref(null);
const reservationForm = ref({
  mac: '',
  ip: '',
  createFirewallAddress: false
});
const isSubmittingReservation = ref(false);
const isRevokingLease = ref(false);

const toggleAllDhcp = () => {
  if (selectedDhcpLeases.value.length === filteredAndSortedDhcpLeases.value.length) {
    selectedDhcpLeases.value = [];
  } else {
    selectedDhcpLeases.value = [...filteredAndSortedDhcpLeases.value];
  }
};

const handleClickOutside = (e) => {
  if (reservationDropdownRef.value && !reservationDropdownRef.value.contains(e.target)) {
    showReservationDropdown.value = false;
  }
  if (addFilterRef.value && !addFilterRef.value.contains(e.target)) {
    showAddFilter.value = false;
  }
  if (columnPickerRef.value && !columnPickerRef.value.contains(e.target)) {
    showColumnPicker.value = false;
  }
};

const handleReservation = () => {
  if (!canReserveDhcp.value) return;
  const lease = selectedDhcpLeases.value[0];
  reservationForm.value = {
    mac: lease.mac,
    ip: lease.ip,
    createFirewallAddress: false
  };
  showReservationModal.value = true;
};

const handleRevoke = async () => {
  const reservedLeases = selectedDhcpLeases.value.filter(l => l.reserved);
  if (reservedLeases.length === 0) return;
  
  isRevokingLease.value = true;
  let errored = false;
  
  for (const lease of reservedLeases) {
    try {
      // Enviamos server_mkey para que el backend no tenga que buscar en todos los servidores
      await fortigateService.revokeDhcp(selectedHost.value.ip, lease.mac, lease.server_mkey);
      const found = diagnosticsData.value.dhcp_leases.find(l => l.mac === lease.mac);
      if (found) found.reserved = false;
    } catch (error) {
      console.error('Error revocando reserva:', error);
      errored = true;
    }
  }
  
  isRevokingLease.value = false;
  selectedDhcpLeases.value = [];
  if (errored) alert('Hubo un error al revocar alguna(s) reserva(s). Verifica la consola del backend.');
};

const submitReservation = async () => {
  isSubmittingReservation.value = true;
  try {
    await fortigateService.reserveDhcp(selectedHost.value.ip, reservationForm.value);
    const lease = diagnosticsData.value.dhcp_leases.find(l => l.mac === reservationForm.value.mac);
    if (lease) lease.reserved = true;
  } catch (error) {
    console.error("Error reservando DHCP:", error);
    alert("Hubo un error al crear la reserva DHCP.");
  } finally {
    isSubmittingReservation.value = false;
    showReservationModal.value = false;
    selectedDhcpLeases.value = [];
  }
};

const sortDhcp = (column) => {
  if (dhcpSortColumn.value === column) {
    dhcpSortOrder.value = dhcpSortOrder.value === 'asc' ? 'desc' : 'asc';
  } else {
    dhcpSortColumn.value = column;
    dhcpSortOrder.value = 'asc';
  }
};

const filteredAndSortedDhcpLeases = computed(() => {
  if (!diagnosticsData.value || !diagnosticsData.value.dhcp_leases) return [];
  
  let result = diagnosticsData.value.dhcp_leases;

  if (dhcpFilters.value.length) {
    result = result.filter((lease) => dhcpFilters.value.every((filter) => matchesDhcpFilter(lease, filter)));
  }

  if (dhcpSearchQuery.value) {
    const q = dhcpSearchQuery.value.toLowerCase();
    result = result.filter(lease => 
      (lease.hostname && lease.hostname.toLowerCase().includes(q)) ||
      (lease.ip && lease.ip.toLowerCase().includes(q)) ||
      (lease.mac && lease.mac.toLowerCase().includes(q)) ||
      (lease.interface && lease.interface.toLowerCase().includes(q)) ||
      (lease.interface_alias && lease.interface_alias.toLowerCase().includes(q))
    );
  }

  // Ordenamiento
  result = [...result].sort((a, b) => {
    let valA = a[dhcpSortColumn.value] || '';
    let valB = b[dhcpSortColumn.value] || '';
    
    // Custom sort for IP addresses
    if (dhcpSortColumn.value === 'ip') {
      const numA = Number(valA.split(".").map((ip) => (`000${ip}`).slice(-3)).join(""));
      const numB = Number(valB.split(".").map((ip) => (`000${ip}`).slice(-3)).join(""));
      return dhcpSortOrder.value === 'asc' ? numA - numB : numB - numA;
    }
    
    // Fallback string sort
    valA = valA.toString().toLowerCase();
    valB = valB.toString().toLowerCase();
    
    if (valA < valB) return dhcpSortOrder.value === 'asc' ? -1 : 1;
    if (valA > valB) return dhcpSortOrder.value === 'asc' ? 1 : -1;
    return 0;
  });

  return result;
});

// Acciones Side Panel
const openSidePanel = (host) => {
  selectedHost.value = host;
  activeTab.value = 'monitor';
  diagnosticsData.value = null;
  selectedDhcpLeases.value = [];
  dhcpFilters.value = [];
  dhcpSearchQuery.value = '';
  auditSearch.value = '';
  blockMenuFor.value = null;
  startLiveAudit();
  loadBannedIps();
};

const openDhcpTab = (host) => {
  if (host.dhcp_count === null || host.dhcp_count === '-') return; // Not available
  
  selectedHost.value = host;
  activeTab.value = 'diagnostics';
  
  // If we don't have the data yet, load it
  if (!diagnosticsData.value || selectedHost.value.ip !== host.ip) {
      loadDiagnostics();
  }
};

const closeSidePanel = () => {
  stopLiveAudit();
  closeAuditDetail();
  selectedHost.value = null;
  trafficAudit.value = null;
  auditError.value = '';
  bannedIps.value = [];
  blockMenuFor.value = null;
};

const formatBytes = (bytes) => {
  const n = Number(bytes) || 0;
  if (n >= 1073741824) return (n / 1073741824).toFixed(2) + ' GB';
  if (n >= 1048576) return (n / 1048576).toFixed(1) + ' MB';
  if (n >= 1024) return (n / 1024).toFixed(0) + ' KB';
  return n + ' B';
};

const auditWindowLabel = computed(() => {
  if (auditLive.value) return 'Sesiones en tiempo real del FortiGate';
  if (auditWindow.value.label) return `Ventana: ${auditWindow.value.label}`;
  return 'Última consulta a la API';
});

const matchesAuditQuery = (text) => {
  const q = auditSearch.value.trim().toLowerCase();
  if (!q) return true;
  return String(text || '').toLowerCase().includes(q);
};

const PROTOCOL_APPS = new Set(['DNS', 'NTP', 'SNMP', 'DHCP', 'ICMP', 'HTTP', 'HTTPS', 'SSH', 'FTP']);

function looksLikeIp(value) {
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(String(value || '').split(':')[0]);
}

function mapAuditSession(session) {
  const srcIp = session.srcip || '';
  const domain = session.dst_host && !looksLikeIp(session.dst_host) ? session.dst_host : '';
  const rawApp = session.app || '';
  const app = domain && PROTOCOL_APPS.has(String(rawApp).toUpperCase())
    ? domain
    : (rawApp && !['Tráfico no clasificado', 'Cloudflare', 'Akamai CDN'].includes(rawApp)
      ? rawApp
      : (domain || 'HTTPS'));
  return {
    id: [srcIp, session.dstip, session.dst_host, session.app, session.dport].join('|'),
    srcIp,
    srcUser: session.user || '',
    srcHost: session.hostname || '',
    dstIp: domain || session.dstip || '—',
    dstHost: domain && session.dstip && session.dstip !== domain ? session.dstip : '',
    destIpRaw: session.dstip || '',
    destDomain: domain,
    srcIntf: session.srcintf || '',
    dstIntf: session.dstintf || '',
    app,
    proto: session.proto || 'tcp',
    sport: session.sport || 0,
    dport: session.dport || 0,
    txBytes: Number(session.tx_bytes || 0),
    rxBytes: Number(session.rx_bytes || 0) || (session.tx_bytes ? 0 : Number(session.bytes || 0)),
    sessionSeconds: Number(session.duration || 0),
    status: 'active',
    blocked: bannedIps.value.some((b) => b.ip === srcIp),
    risk: /(bittorrent|torrent|p2p|emule)/i.test(app) ? 'high' : (/(tor\b|onion|proxy|anonym)/i.test(app) ? 'medium' : 'none'),
  };
}

const auditTalkers = computed(() => {
  const firewallIp = selectedHost.value?.ip || '';
  let sessions = [...(trafficAudit.value?.sessions || [])];
  if (!sessions.length && (trafficAudit.value?.sources || []).length) {
    sessions = trafficAudit.value.sources.map((item) => ({
      srcip: item.key,
      hostname: item.hostname,
      dstip: (trafficAudit.value.destinations || [])[0]?.key || '',
      dst_host: item.hostname || '',
      app: (trafficAudit.value.applications || []).find((a) => a.key && !['Tráfico no clasificado', 'Cloudflare'].includes(a.key))?.key || 'HTTPS',
      bytes: item.bytes,
      tx_bytes: 0,
      rx_bytes: item.bytes,
      duration: 0,
    }));
  }
  return sessions
    .filter((s) => s.srcip && s.srcip !== firewallIp && !String(s.srcip).startsWith(firewallIp + ':'))
    .sort((a, b) => Number(b.bytes || 0) - Number(a.bytes || 0))
    .map(mapAuditSession);
});

const filteredAuditTalkers = computed(() =>
  auditTalkers.value.filter((row) =>
    matchesAuditQuery(`${row.srcIp} ${row.srcUser} ${row.srcHost} ${row.dstIp} ${row.dstHost} ${row.app}`)
  )
);

const stopLiveAudit = () => {
  auditLive.value = false;
  if (auditInterval) {
    clearInterval(auditInterval);
    auditInterval = null;
  }
};

const loadTrafficAudit = async (realtime = true, start = null, end = null) => {
  if (!selectedHost.value?.ip) return;
  isLoadingAudit.value = true;
  auditError.value = '';
  try {
    trafficAudit.value = await fortigateService.getTrafficAudit(selectedHost.value.ip, {
      realtime,
      start,
      end
    });
  } catch (error) {
    auditError.value = 'No se pudo leer la API del FortiGate. Revisa token y permisos de FortiView/sesiones.';
    console.error(error);
  } finally {
    isLoadingAudit.value = false;
  }
};

const detailRow = ref(null);
const detail = ref(null);
const detailLoading = ref(false);
const detailError = ref('');
const detailNow = ref(Math.floor(Date.now() / 1000));
const detailChartHistory = ref([]);
let detailClock = null;
let detailPoll = null;

const liveDuration = computed(() => {
  if (detail.value?.started_at && (detail.value.active || detail.value.ended_at)) {
    const end = detail.value.active ? detailNow.value : detail.value.ended_at;
    return Math.max(0, end - detail.value.started_at);
  }
  return detailRow.value?.sessionSeconds || 0;
});

async function refreshAuditDetail() {
  if (!detailRow.value || !selectedHost.value?.ip) return;
  try {
    const data = await fortigateService.getSessionDetail(selectedHost.value.ip, {
      srcip: detailRow.value.srcIp,
      dstip: detailRow.value.destIpRaw || undefined,
      dst_host: detailRow.value.destDomain || undefined,
    });
    const prev = detail.value;
    const incomingBytes = Number(data.tx_bytes || 0) + Number(data.rx_bytes || 0);
    const prevBytes = Number(prev?.tx_bytes || 0) + Number(prev?.rx_bytes || 0);
    if (!data.active && incomingBytes === 0 && prevBytes > 0) {
      detail.value = {
        ...prev,
        active: false,
        ended_at: prev.ended_at || Math.floor(Date.now() / 1000),
        rate_bps: 0,
      };
    } else {
      detail.value = data;
      if (detailChartHistory.value.length === 0 && data.series) {
        detailChartHistory.value = [...data.series];
      } else if (incomingBytes > 0) {
        detailChartHistory.value.push({
          t: Math.floor(Date.now() / 1000),
          tx: data.tx_bytes || 0,
          rx: data.rx_bytes || 0,
        });
        if (detailChartHistory.value.length > 50) detailChartHistory.value.shift();
      }
    }
    detailError.value = '';
  } catch (error) {
    if (!detail.value) detailError.value = error.message || 'No se pudo leer el detalle.';
  } finally {
    detailLoading.value = false;
  }
}

function openAuditDetail(row) {
  if (!row) return;
  detailRow.value = row;
  detail.value = null;
  detailError.value = '';
  detailChartHistory.value = [];
  detailLoading.value = true;
  detailNow.value = Math.floor(Date.now() / 1000);
  refreshAuditDetail();
  stopAuditDetailTimers();
  detailClock = setInterval(() => {
    detailNow.value = Math.floor(Date.now() / 1000);
  }, 1000);
  detailPoll = setInterval(() => refreshAuditDetail(), 8000);
}

function stopAuditDetailTimers() {
  if (detailClock) {
    clearInterval(detailClock);
    detailClock = null;
  }
  if (detailPoll) {
    clearInterval(detailPoll);
    detailPoll = null;
  }
}

function closeAuditDetail() {
  stopAuditDetailTimers();
  detailRow.value = null;
  detail.value = null;
  detailError.value = '';
  detailChartHistory.value = [];
}

const openMonitorTab = () => {
  activeTab.value = 'monitor';
};

const openAuditTab = () => {
  activeTab.value = 'audit';
  if (!auditLive.value && !auditWindow.value.start) startLiveAudit();
  loadBannedIps();
};

const startLiveAudit = () => {
  auditWindow.value = { start: null, end: null, label: '' };
  auditLive.value = true;
  loadTrafficAudit(true);
  if (auditInterval) clearInterval(auditInterval);
  auditInterval = setInterval(() => {
    if (auditLive.value && selectedHost.value && (activeTab.value === 'monitor' || activeTab.value === 'audit')) {
      loadTrafficAudit(true);
      loadBannedIps();
    }
  }, 5000);
};

const loadBannedIps = async () => {
  if (!selectedHost.value?.ip) return;
  isLoadingBanned.value = true;
  try {
    const res = await fortigateService.getBannedIps(selectedHost.value.ip);
    bannedIps.value = res?.banned || [];
  } catch (error) {
    console.error('Error cargando cuarentena:', error);
  } finally {
    isLoadingBanned.value = false;
  }
};

const isBanned = (ip) => bannedIps.value.some((b) => b.ip === ip);

const hostnameForIp = (ip) => {
  const match = trafficAudit.value?.sources?.find((s) => s.key === ip);
  if (match?.hostname) return match.hostname;
  const lease = diagnosticsData.value?.dhcp_leases?.find((l) => l.ip === ip);
  return lease?.hostname || '—';
};

const banExpiryLabel = (entry) => {
  const expires = Number(entry.expires || entry.expiry || 0);
  if (!expires) return 'Indefinido';
  const now = Math.floor(Date.now() / 1000);
  const remaining = expires - now;
  if (remaining <= 0) return 'Expirando...';
  const mins = Math.floor(remaining / 60);
  if (mins < 60) return `en ${mins} min`;
  const hours = Math.floor(mins / 60);
  return `en ${hours}h ${mins % 60}m`;
};

const toggleBlockMenu = (ip) => {
  blockMenuFor.value = blockMenuFor.value === ip ? null : ip;
};

const blockHost = async (ip, expirySeconds) => {
  if (!selectedHost.value?.ip) return;
  blockMenuFor.value = null;
  try {
    await fortigateService.banIp(selectedHost.value.ip, ip, expirySeconds);
    await loadBannedIps();
  } catch (error) {
    console.error('Error bloqueando IP:', error);
    alert('No se pudo bloquear la IP. Verifica que el token tenga permisos de administrador (admingrp).');
  }
};

const unblockHost = async (ip) => {
  if (!selectedHost.value?.ip) return;
  try {
    await fortigateService.unbanIp(selectedHost.value.ip, ip);
    await loadBannedIps();
  } catch (error) {
    console.error('Error desbloqueando IP:', error);
    alert('No se pudo desbloquear la IP.');
  }
};

const auditChartWindow = (payload) => {
  stopLiveAudit();
  const label = payload.timeLabel
    ? `${payload.portName} · ${payload.timeLabel} (±3 min)`
    : payload.portName;
  auditWindow.value = { start: payload.start, end: payload.end, label };
  activeTab.value = 'audit';
  loadTrafficAudit(false, payload.start, payload.end);
};

const loadDiagnostics = async () => {
  stopLiveAudit();
  activeTab.value = 'diagnostics';
  
  isLoadingDiagnostics.value = true;
  try {
    diagnosticsData.value = await fortigateService.getDiagnostics(selectedHost.value.ip);
    
    // Update the dhcp_count in the main table reactive element
    const hostInGrid = fortigates.value.find(h => h.ip === selectedHost.value.ip);
    if (hostInGrid && diagnosticsData.value.dhcp_leases) {
        hostInGrid.dhcp_count = diagnosticsData.value.dhcp_leases.length;
    }
  } catch (error) {
    console.error("Error cargando diagnósticos:", error);
    alert("Error conectando con la API del FortiGate (¿Token configurado?).");
  } finally {
    isLoadingDiagnostics.value = false;
  }
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

// --- Paginación ---
const currentPage = ref(1);
const itemsPerPage = 15;

const totalPages = computed(() => Math.max(1, Math.ceil(filteredFortigates.value.length / itemsPerPage)));

const paginatedFortigates = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return filteredFortigates.value.slice(start, end);
});

watch(searchQuery, () => {
  currentPage.value = 1;
});


const metricTone = (value) => {
  const n = Number(value);
  return n > 0 ? 'font-bold text-neutral-800' : 'font-medium text-neutral-300';
};

const totalSessions = computed(() =>
  fortigates.value.reduce((sum, fg) => sum + Number(fg.metrics?.active_sessions || 0), 0)
);

const totalVpn = computed(() =>
  fortigates.value.reduce((sum, fg) => {
    const up = fg.metrics?.vpn_tunnels_up ?? fg.metrics?.vpn?.up ?? 0;
    return sum + Number(up || 0);
  }, 0)
);

const totalWan = computed(() =>
  fortigates.value.reduce((acc, fg) => {
    const t = getTotalTraffic(fg.metrics?.interfaces);
    acc.in += t.in;
    acc.out += t.out;
    return acc;
  }, { in: 0, out: 0 })
);

const wanTrendSeries = computed(() => {
  const buckets = {};
  fortigates.value.forEach((fg) => {
    (fg.metrics?.interfaces || []).forEach((iface) => {
      (iface.history || []).forEach((pt) => {
        const key = pt.time || '';
        if (!key) return;
        if (!buckets[key]) buckets[key] = { in: 0, out: 0 };
        buckets[key].in += Number(pt.in || 0);
        buckets[key].out += Number(pt.out || 0);
      });
    });
  });
  const times = Object.keys(buckets).sort();
  if (times.length < 3) {
    return { times: mockData.wanTimes, in: mockData.wanIn, out: mockData.wanOut };
  }
  return {
    times,
    in: times.map((t) => Number(buckets[t].in.toFixed(1))),
    out: times.map((t) => Number(buckets[t].out.toFixed(1)))
  };
});

const sparklineOption = (data, color, fill) => {
  const series = Array.isArray(data) && data.length ? data : [];
  return {
    animation: false,
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: 'category', show: false, data: series.map((_, i) => i) },
    yAxis: { type: 'value', show: false, min: 0, max: 100 },
    tooltip: { show: false },
    series: [{
      type: 'line',
      data: series,
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 1.4, color },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: fill },
            { offset: 1, color: 'rgba(255,255,255,0)' }
          ]
        }
      }
    }]
  };
};

const wanTrendOption = computed(() => {
  const { times, in: inbound, out: outbound } = wanTrendSeries.value;
  return {
    animation: false,
    grid: { left: 0, right: 0, top: 4, bottom: 2 },
    xAxis: { type: 'category', show: false, data: times },
    yAxis: { type: 'value', show: false },
    tooltip: { show: false },
    series: [
      {
        name: 'IN',
        type: 'line',
        data: inbound,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: '#059669' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(5,150,105,0.28)' },
              { offset: 1, color: 'rgba(5,150,105,0)' }
            ]
          }
        }
      },
      {
        name: 'OUT',
        type: 'line',
        data: outbound,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.3, color: '#a3a3a3' }
      }
    ]
  };
});

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

// Utilidad: Parsear Unix Time
const formatUnixTime = (unixSeconds) => {
  if (!unixSeconds) return 'N/A';
  const date = new Date(unixSeconds * 1000);
  // Format: YYYY/MM/DD HH:MM:SS
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${yyyy}/${mm}/${dd} ${hh}:${min}:${ss}`;
};

// Utilidad: Agrupar interfaces DHCP únicas para el resumen
const getUniqueDhcpInterfaces = (leases) => {
  if (!leases) return [];
  const counts = {};
  leases.forEach(l => {
    const iface = l.interface || 'unknown';
    counts[iface] = (counts[iface] || 0) + 1;
  });
  return Object.keys(counts).map(key => ({ name: key, count: counts[key] }));
};

// Utilidad: Determinar icono de dispositivo basado en hostname o VCI
const getDeviceIcon = (hostname = '', vci = '') => {
  const name = (hostname || '').toLowerCase();
  const vendor = (vci || '').toLowerCase();
  
  // Impresoras
  if (name.includes('printer') || name.includes('hp') || name.includes('canon') || 
      name.includes('epson') || vendor.includes('printer')) {
    return 'fas fa-print';
  }
  
  // Teléfonos IP / VoIP
  if (name.includes('phone') || name.includes('voip') || name.includes('polycom') ||
      name.includes('cisco') || vendor.includes('phone')) {
    return 'fas fa-phone';
  }
  
  // Access Points / WiFi
  if (name.includes('ap-') || name.includes('wifi') || name.includes('wireless') ||
      name.includes('ubiquiti') || name.includes('unifi')) {
    return 'fas fa-wifi';
  }
  
  // Servidores
  if (name.includes('server') || name.includes('srv') || name.includes('dc-') ||
      name.includes('vm-') || name.includes('host')) {
    return 'fas fa-server';
  }
  
  // Switches / Network equipment
  if (name.includes('switch') || name.includes('sw-') || name.includes('core')) {
    return 'fas fa-network-wired';
  }
  
  // Cámaras IP
  if (name.includes('camera') || name.includes('cam-') || name.includes('ipc') ||
      name.includes('nvr') || vendor.includes('hikvision') || vendor.includes('dahua')) {
    return 'fas fa-video';
  }
  
  // Mobile devices
  if (name.includes('iphone') || name.includes('ipad') || name.includes('android') ||
      name.includes('mobile') || vendor.includes('android') || vendor.includes('apple')) {
    return 'fas fa-mobile-alt';
  }
  
  // Laptops
  if (name.includes('laptop') || name.includes('nb-') || name.includes('macbook')) {
    return 'fas fa-laptop';
  }
  
  // Default: desktop/workstation
  return 'fas fa-desktop';
};

// Lógica: Carga asíncrona a la API de backend
const fetchFortigates = async (isSilent = false) => {
  if (!isSilent) isLoading.value = true;
  
  try {
    // LLAMADA REAL A LA API
    const data = await zabbixService.getFortigates();
    
    // Maintain existing DHCP counts before overwriting
    data.forEach(fg => {
      const existing = fortigates.value.find(f => f.hostid === fg.hostid);
      fg.dhcp_count = existing && existing.dhcp_count !== undefined ? existing.dhcp_count : null;
      fg.dhcp_loading = existing && existing.dhcp_loading !== undefined ? existing.dhcp_loading : false;
      fg.cpu_history = seedHistory(fg.metrics?.cpu_history, existing?.cpu_history, fg.metrics?.cpu);
      fg.ram_history = seedHistory(fg.metrics?.ram_history, existing?.ram_history, fg.metrics?.ram);
      fg.cpuSparkOption = sparklineOption(fg.cpu_history, '#ea580c', 'rgba(234,88,12,0.35)');
      fg.ramSparkOption = sparklineOption(fg.ram_history, '#059669', 'rgba(5,150,105,0.35)');
    });

    fortigates.value = data;

    // Sincronizar el panel lateral (Modal) para que se actualice sin "ruido"
    if (selectedHost.value) {
      const updatedHost = data.find(h => h.hostid === selectedHost.value.hostid);
      if (updatedHost) {
        selectedHost.value = updatedHost;
      }
    }

    // Trigger background fetch for DHCP counts for all hosts (if first load or periodic)
    // COMENTADO PARA EVITAR CONGELAMIENTO AL TENER MÁS DE 300 EQUIPOS
    // Si realmente lo necesitan, debería implementarse una carga progresiva solo para los visibles
    /*
    fortigates.value.forEach(async (fg) => {
      if (fg.dhcp_count === '-' || fg.dhcp_loading) return; // already know it's unconfigured or loading
      try {
        fg.dhcp_loading = true;
        const diag = await fortigateService.getDiagnostics(fg.ip);
        if (diag && diag.dhcp_leases) {
          fg.dhcp_count = diag.dhcp_leases.length;
        } else {
          fg.dhcp_count = '-';
        }
      } catch (err) {
        // 403 = Token no configurado para este FortiGate (comportamiento esperado)
        // Solo loggear errores reales (no 403)
        if (err.message && !err.message.includes('403')) {
          console.warn(`FortiGate ${fg.ip} DHCP fetch error:`, err.message);
        }
        fg.dhcp_count = '-';
      } finally {
        fg.dhcp_loading = false;
      }
    });
    */

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
  document.addEventListener('click', handleClickOutside);
  refreshInterval = setInterval(() => {
    fetchFortigates(true); // Refresco silencioso cada 30 segundos
    
    // Auto refresh de la pestaña de diagnósticos si está activa
    if (activeTab.value === 'diagnostics' && selectedHost.value) {
      // Background silent refresh (sin mostrar loader grandote)
      fortigateService.getDiagnostics(selectedHost.value.ip).then(data => {
        diagnosticsData.value = data;
        // Update main table count as well
        const hostInGrid = fortigates.value.find(h => h.ip === selectedHost.value.ip);
        if (hostInGrid && data.dhcp_leases) {
            hostInGrid.dhcp_count = data.dhcp_leases.length;
        }
      }).catch(() => {});
    }
  }, 30000); // 30 seconds
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
  stopLiveAudit();
  closeAuditDetail();
  document.removeEventListener('click', handleClickOutside);
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
