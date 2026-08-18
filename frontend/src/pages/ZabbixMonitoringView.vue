<template>
  <div class="zabbix-monitoring-container h-full min-h-0 flex flex-col gap-3 font-sans overflow-hidden">
    <!-- Header -->
    <header class="flex justify-between items-center shrink-0">
      <div>
        <h1 class="text-xl font-bold text-slate-800 tracking-tight leading-tight">Monitoreo Zabbix V2</h1>
        <p class="text-xs text-slate-500 mt-0.5">Estado en tiempo real de todos los servidores monitoreados</p>
      </div>
      <!-- Time Picker -->
      <div class="flex items-center gap-1 bg-slate-100/80 p-1 rounded-lg border border-slate-200">
        <button v-for="tr in timeRanges" :key="tr.value" 
                @click="setTimeRange(tr.value)"
                class="px-3 py-1 text-xs font-semibold rounded-md transition-all"
                :class="selectedRange === tr.value ? 'bg-white text-slate-800 shadow-sm ring-1 ring-slate-200/50' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'">
          {{ tr.label }}
        </button>
      </div>

      <button @click="refreshAll" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all flex items-center gap-2">
        <i class="fas fa-sync-alt" :class="{'animate-spin': loadingTrends || loadingHosts}"></i>
        Refrescar Todo
      </button>
    </header>

    <!-- Global Trends (Modo Servidores) -->
    <div v-if="!isSecurityMode" class="grid grid-cols-1 lg:grid-cols-2 gap-3 shrink-0">
      <div class="trend-chart bg-white px-4 pt-3 pb-2 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative min-h-[320px]">
        <div class="flex justify-between items-center mb-1">
          <h2 class="text-xs font-bold text-slate-700 tracking-wider">CPU GLOBAL TREND (TOP 5)</h2>
        </div>
        <div v-if="loadingTrends" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-xl"><div class="spinner"></div></div>
        <apexchart type="line" height="300" :options="trendOptions('right')" :series="cpuTrendSeries" />
      </div>
      <div class="trend-chart bg-white px-4 pt-3 pb-2 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative min-h-[320px]">
        <div class="flex justify-between items-center mb-1">
          <h2 class="text-xs font-bold text-slate-700 tracking-wider">MEMORY GLOBAL TREND (TOP 5)</h2>
        </div>
        <div v-if="loadingTrends" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-xl"><div class="spinner"></div></div>
        <apexchart type="line" height="300" :options="trendOptions('left')" :series="ramTrendSeries" />
      </div>
    </div>

    <!-- Global Trends (Modo Seguridad) -->
    <div v-if="isSecurityMode" class="grid grid-cols-1 lg:grid-cols-3 gap-3 shrink-0">
      <div class="bg-slate-800 text-white px-5 py-4 rounded-xl shadow-lg relative flex flex-col justify-between">
        <h2 class="text-xs font-bold text-slate-300 tracking-wider">TOTAL SESSIONS (ACTIVES)</h2>
        <div class="text-4xl font-black tracking-tight mt-2 text-purple-400">{{ globalFirewallSessions.toLocaleString() }}</div>
        <div class="text-[10px] text-slate-400 mt-1">Conexiones concurrentes en tiempo real</div>
      </div>
      <div class="bg-slate-800 text-white px-5 py-4 rounded-xl shadow-lg relative flex flex-col justify-between">
        <h2 class="text-xs font-bold text-slate-300 tracking-wider">VPN TUNNELS (IPSEC/SSL)</h2>
        <div class="text-4xl font-black tracking-tight mt-2" :class="globalVpnTunnels > 0 ? 'text-emerald-400' : 'text-slate-500'">{{ globalVpnTunnels }}</div>
        <div class="text-[10px] text-slate-400 mt-1">Túneles VPN Activos</div>
      </div>
      <div class="bg-slate-800 text-white px-5 py-4 rounded-xl shadow-lg relative flex flex-col justify-between">
        <h2 class="text-xs font-bold text-slate-300 tracking-wider">NETWORK TRAFFIC (TOTAL IN)</h2>
        <div class="text-4xl font-black tracking-tight mt-2 text-blue-400">{{ (globalNetIn / 1000).toFixed(1) }} <span class="text-lg">Mbps</span></div>
        <div class="text-[10px] text-slate-400 mt-1">Tráfico de descarga consolidado</div>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-white rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] flex-1 min-h-0 flex flex-col overflow-hidden relative">
      <div v-if="loadingHosts" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-xl"><div class="spinner"></div></div>
      
      <!-- Toolbar -->
      <div class="px-4 py-3 border-b border-slate-100 flex flex-wrap justify-between items-center bg-white z-[2]">
        <div class="flex items-center gap-3">
          <!-- Search Input -->
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </span>
            <input v-model="searchQuery" type="text" placeholder="Buscar por servidor o IP..." class="pl-9 pr-3 py-1.5 border border-slate-200 rounded-lg text-[13px] text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64 bg-slate-50 hover:bg-white transition-colors" />
          </div>
          <!-- OS Filter Dropdown -->
          <select v-model="osFilter" class="border border-slate-200 rounded-lg text-[13px] px-2 py-1.5 text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 hover:bg-white transition-colors">
            <option value="all">Todos los Sistemas</option>
            <option value="windows">Windows</option>
            <option value="linux">Linux</option>
          </select>
        </div>
        <!-- Right Section: Toggle -->
        <div class="flex items-center gap-4">
          <label class="flex items-center cursor-pointer group">
            <div class="relative">
              <input type="checkbox" v-model="isSecurityMode" class="sr-only">
              <div class="block w-10 h-6 rounded-full transition-colors" :class="isSecurityMode ? 'bg-red-500' : 'bg-slate-300'"></div>
              <div class="dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform" :class="isSecurityMode ? 'transform translate-x-4' : ''"></div>
            </div>
            <span class="ml-3 text-[12px] font-bold" :class="isSecurityMode ? 'text-red-600' : 'text-slate-500 group-hover:text-slate-700'">FortiGate V2</span>
          </label>
        </div>
      </div>

      <div class="overflow-auto flex-1 min-h-0">
        <table class="w-full text-left border-collapse">
          <thead class="sticky top-0 bg-white z-[1]">
            <tr class="border-b border-slate-100 shadow-[0_2px_3px_-2px_rgba(0,0,0,0.05)]">
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Servidor</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">IP</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">OS / INFO</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Estado</th>
              <template v-if="!isSecurityMode">
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">CPU (%)</th>
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">RAM Usada (%)</th>
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">RED (IN / OUT)</th>
              </template>
              <template v-else>
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Túneles VPN</th>
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Sesiones Activas</th>
                <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Tráfico Global (In/Out)</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="host in filteredHosts" :key="host.hostid" 
                class="border-b transition-colors cursor-pointer"
                :class="host.status === 'Offline' ? 'bg-red-50/40 hover:bg-red-100/50 animate-[pulse_3s_ease-in-out_infinite]' : 'border-slate-50 hover:bg-blue-50/40'" 
                @click="openDetail(host)">
              <td class="py-2 px-4 font-semibold text-[13px] whitespace-nowrap"
                  :class="host.status === 'Offline' ? 'text-red-700' : 'text-slate-700'">
                {{ parseHostname(host.hostname).main }}
                <span v-if="parseHostname(host.hostname).tag" class="ml-1.5 align-middle text-[9px] font-bold text-slate-400 tracking-wider">{{ parseHostname(host.hostname).tag }}</span>
              </td>
              <td class="py-2 px-4 text-slate-500 font-mono text-[11px] font-medium tracking-tight">{{ host.ip }}</td>
              <td class="py-2 px-4 whitespace-nowrap">
                <div class="flex items-center gap-2">
                  <!-- Ícono SVGs para OS -->
                  <svg v-if="getDetectedOS(host).osName.includes('Windows')" class="w-3.5 h-3.5 text-blue-500" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M0 12.402l35.687-4.86.016 34.423L0 41.965v-29.563zm35.67 33.529l.016 34.453L0 75.485V46.068l35.67-4.137zm4.326-39.011L87.314 0v41.26L39.996 41.95V6.92zm47.318 39.011V87.31l-47.318-6.66.015-34.72 47.303-4.009z"/></svg>
                  <svg v-else-if="getDetectedOS(host).osName.includes('Linux')" class="w-3.5 h-3.5 text-slate-600" viewBox="0 0 448 512" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M220.8 123.3c1 .5 1.8 1.7 3 1.7 1.1 0 2.8-.4 2.9-1.5.2-1.4-1.9-2.3-3.2-2.9-1.7-.7-3.9-1-5.5-.1-.4.2-.8.7-.6 1.1.3 1.3 2.3 1.1 3.4 1.7zm-21.9 1.7c1.2 0 2-1.2 3-1.7 1.1-.6 3.1-.4 3.5-1.7.2-.4-.2-.9-.6-1.1-1.6-.9-3.8-.6-5.5.1-1.3.6-3.4 1.5-3.2 2.9.1 1 1.8 1.5 2.8 1.5zM420.2 392.5c-5.1-9.7-16.3-15.4-30.8-19.1-14.9-3.9-29.1-8-36.8-14.8-17.6-15.5-27.1-39.3-35.3-60.6-2.6-6.7-5.1-13.4-7.8-20.1C333.1 230 352 178.6 352 144 352 64.2 293 0 224 0 154.9 0 96 64.2 96 144c0 34.6 18.9 86 42.5 133.9-2.7 6.7-5.2 13.4-7.8 20.1-8.3 21.3-17.7 45.1-35.3 60.6-7.8 6.8-21.9 10.9-36.8 14.8-14.5 3.7-25.7 9.4-30.8 19.1C8.7 428.8 28.5 487.6 28.5 487.6c1 2.3 3.3 3.8 5.8 4.1l2.4.2c.4 0 1 .1 1.4.1 48 4 96.5 15.6 144.1 19.8 11.2 1 22.3 1.7 33.5 1.7s22.3-.7 33.5-1.7c47.7-4.2 96.1-15.8 144.1-19.8.5 0 1-.1 1.4-.1l2.4-.2c2.5-.3 4.8-1.9 5.8-4.1 0 0 19.8-58.8.8-95.1zM224 496c-27 0-54.6-2-83.3-4.6l-50.6-3.8c-24.1-1.6-47-2.6-70-3.3 5.4-9.9 16.4-18.7 32-23.3 12.3-3.6 28-7.3 36.1-12 18-10.4 28.6-33.1 36.9-57 5.1-14.7 9.8-29.3 14.7-43.2.1 0 .2-.1.3-.1 1.7-4.9 3.5-9.8 5.3-14.7 13.2-36.7 26.2-72.9 26.2-120.2V112.5c0-1.8.2-3.4.6-5 .6 0 1.2.1 1.8.1h30.2c.6 0 1.2-.1 1.8-.1.4 1.6.6 3.2.6 5v121.2c0 47.3 13 83.5 26.2 120.2 1.8 4.9 3.6 9.8 5.3 14.7.1 0 .2.1.3.1 4.9 13.9 9.6 28.5 14.7 43.2 8.3 23.9 18.9 46.5 36.9 57 8.1 4.7 23.8 8.4 36.1 12 15.6 4.6 26.6 13.3 32 23.3-23 1-45.9 2-70 3.3l-50.6 3.8C278.6 494 251 496 224 496z" /></svg>
                  <svg v-else-if="getDetectedOS(host).osName.includes('FortiOS')" class="w-3.5 h-3.5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  <svg v-else class="w-3.5 h-3.5 text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2"/></svg>
                  <span class="text-[11px] font-medium text-slate-600 truncate max-w-[140px]" :title="getDetectedOS(host).osName">{{ getDetectedOS(host).osName }}</span>
                </div>
              </td>
              <td class="py-2 px-4">
                <div class="flex items-center gap-2">
                  <span class="relative flex h-2.5 w-2.5">
                    <span v-if="host.status === 'Online'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="statusMeta(host.status).dotClass"></span>
                  </span>
                  <span class="text-[11px] font-semibold tracking-tight" :class="statusMeta(host.status).textClass">
                    {{ statusMeta(host.status).label }}
                  </span>
                </div>
              </td>
              <template v-if="!isSecurityMode">
                <td class="py-1.5 px-4">
                  <div class="flex items-center gap-2">
                    <span class="w-12 shrink-0 text-xs font-semibold text-slate-700 tabular-nums">{{ formatPct(host.cpu) }}</span>
                    <div class="sparkline-wrap w-[100px] h-[30px] overflow-hidden shrink-0">
                      <apexchart type="area" width="100" height="30" :options="sparklineOptions(getStatusColor(host.cpu))" :series="[{ data: host.cpu_history }]" />
                    </div>
                  </div>
                </td>
                <td class="py-1.5 px-4">
                  <div class="flex items-center gap-2">
                    <span class="w-12 shrink-0 text-xs font-semibold text-slate-700 tabular-nums">{{ formatPct(host.ram) }}</span>
                    <div class="sparkline-wrap w-[100px] h-[30px] overflow-hidden shrink-0">
                      <apexchart type="area" width="100" height="30" :options="sparklineOptions(getStatusColor(host.ram))" :series="[{ data: host.ram_history }]" />
                    </div>
                  </div>
                </td>
                <td class="py-1.5 px-4">
                  <div class="flex items-center gap-2">
                    <div v-if="(host.net_in === 0 && host.net_out === 0) || host.status === 'Offline'" class="flex flex-col text-red-400 text-[11px] font-semibold w-20 shrink-0">
                      <span>↓ 0 Kbps</span>
                      <span>↑ 0 Kbps</span>
                    </div>
                    <div v-else class="flex flex-col text-[11px] font-semibold w-20 shrink-0">
                      <span class="text-emerald-500">↓ {{ formatNetworkTraffic(host.net_in) }}</span>
                      <span class="text-blue-500">↑ {{ formatNetworkTraffic(host.net_out) }}</span>
                    </div>
                    <div class="sparkline-wrap w-[100px] h-[30px] overflow-hidden shrink-0">
                      <apexchart type="area" width="100" height="30" :options="sparklineOptions('#3b82f6')" :series="[{ data: host.net_in_history }]" />
                    </div>
                  </div>
                </td>
              </template>
              <template v-else>
                <td class="py-1.5 px-4 text-xs font-semibold">
                  <span v-if="host.vpn_tunnels > 0" class="flex items-center gap-1 text-emerald-600"><span class="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span> {{ host.vpn_tunnels }} Activos</span>
                  <span v-else class="flex items-center gap-1 text-red-500"><span class="w-2 h-2 rounded-full bg-red-500 inline-block"></span> 0 Activos</span>
                </td>
                <td class="py-1.5 px-4 text-xs font-black text-slate-700 tabular-nums">{{ (host.sessions || 0).toLocaleString() }}</td>
                <td class="py-1.5 px-4 text-[11px] font-semibold text-slate-500">
                  <div class="flex flex-col">
                    <span class="text-blue-600">↓ {{ ((host.net_in || 0) / 1000).toFixed(1) }} Mbps</span>
                    <span class="text-purple-600">↑ {{ ((host.net_out || 0) / 1000).toFixed(1) }} Mbps</span>
                  </div>
                </td>
              </template>
            </tr>
            <tr v-if="!loadingHosts && hosts.length === 0">
              <td colspan="5" class="py-16 text-center text-slate-500 font-medium">No se encontraron servidores</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Offcanvas Detail Modal -->
    <div v-if="showDetail" class="fixed inset-0 z-50 flex justify-end">
      <!-- Backdrop invisible pero funcional para clics -->
      <div class="absolute inset-0 bg-transparent transition-opacity" @click="closeDetail"></div>
      
      <!-- Panel -->
      <div class="relative w-full max-w-[950px] bg-slate-50 shadow-2xl h-full flex flex-col transform transition-transform translate-x-0 overflow-hidden rounded-none">
        <div class="px-5 py-3 border-b border-slate-200 flex flex-wrap justify-between items-center bg-white z-10 gap-4">
          <div class="flex flex-col gap-2">
            <div class="flex items-center gap-3">
              <h2 class="text-lg font-semibold text-slate-800">Comparativa:</h2>
              <div class="flex flex-wrap gap-2">
                <span v-for="h in selectedHosts" :key="h.hostid" class="px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded text-xs font-bold flex items-center gap-1">
                  {{ h.hostname }}
                  <button v-if="selectedHosts.length > 1" @click="removeHost(h.hostid)" class="hover:text-red-600">&times;</button>
                </span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <select class="text-sm border border-slate-200 rounded px-2 py-1" @change="addHost($event.target.value); $event.target.value=''">
              <option value="">+ Agregar Servidor...</option>
              <option v-for="h in availableHostsToAdd" :key="h.hostid" :value="h.hostid">{{ h.hostname }}</option>
            </select>
            <button @click="closeDetail" class="text-slate-400 hover:text-slate-700 hover:bg-slate-100 h-8 w-8 rounded-full flex items-center justify-center transition-colors">&times;</button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 relative">
          <div v-if="loadingDetail" class="absolute inset-0 bg-slate-50/80 flex flex-col items-center justify-center z-10">
            <div class="spinner"></div>
            <p class="mt-4 text-sm font-medium text-slate-500">Cargando métricas...</p>
          </div>
          <div v-if="Object.keys(comparisonData).length > 0" class="grid grid-cols-2 gap-3">
            <!-- CPU Detail Chart -->
            <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
              <div class="flex justify-between items-center mb-2 pr-6">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest">CPU (%)</span>
                <span class="text-[10px] text-slate-400 font-medium">Última 1 hora</span>
              </div>
              <button @click="expandChart('cpu')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
              </button>
              <apexchart type="line" height="180" :options="detailAreaOptions" :series="cpuSeries" />
            </div>

            <!-- RAM Detail Chart -->
            <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
              <div class="flex justify-between items-center mb-2 pr-6">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest">RAM (%)</span>
                <span class="text-[10px] text-slate-400 font-medium">Última 1 hora</span>
              </div>
              <button @click="expandChart('ram')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
              </button>
              <apexchart type="line" height="180" :options="detailAreaOptions" :series="ramSeries" />
            </div>

            <!-- Disks Usage (Pie Chart) -->
            <div v-show="!isFortiGateSelected" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 flex flex-col relative">
              <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-1">DISK USAGE</span>
              <div class="flex-1 flex flex-wrap items-center justify-center gap-4 -my-4 overflow-y-auto">
                <div v-for="h in selectedHosts" :key="h.hostid" class="flex flex-col items-center">
                  <span class="text-[10px] font-bold text-slate-500 mb-1 truncate w-24 text-center" :title="h.hostname">{{ h.hostname }}</span>
                  <apexchart v-if="comparisonData[h.hostid]?.disks?.length" type="donut" width="130" :options="diskPieOptions" :series="[comparisonData[h.hostid].disks[0].value, 100 - comparisonData[h.hostid].disks[0].value]" />
                  <div v-else class="text-[10px] text-slate-400 italic">No data</div>
                  <span class="text-[9px] font-medium text-slate-400 mt-1">Espacio Usado</span>
                </div>
              </div>
            </div>

            <!-- Network Traffic -->
            <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group flex flex-col">
              <div class="flex justify-between items-center mb-2 pr-6">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">NET TRAFFIC</span>
                <select v-if="availableInterfaces.length > 0" v-model="selectedInterface" class="text-[10px] border border-slate-200 rounded px-1.5 py-0.5 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500">
                  <option v-for="iface in availableInterfaces" :key="iface" :value="iface">{{ iface }}</option>
                </select>
              </div>
              <button @click="expandChart('net')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
              </button>
              <div class="flex-1 min-h-0">
                <apexchart type="line" height="170" :options="netTrafficOptions" :series="netSeries" />
              </div>
            </div>

            <!-- Disk Latency -->
            <div v-show="!isFortiGateSelected" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
              <div class="flex justify-between items-center mb-2 pr-6">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">DISK QUEUE LENGTH LATENCY</span>
              </div>
              <button @click="expandChart('latency')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
              </button>
              <apexchart type="line" height="160" :options="latencyOptions" :series="latencySeries" />
            </div>

            <!-- Firewall Sessions (Dinámico) -->
            <div v-if="hasFirewallSessions" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
              <div class="flex justify-between items-center mb-2 pr-6">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">FIREWALL SESSIONS & SECURITY</span>
              </div>
              <button @click="expandChart('sessions')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
              </button>
              <div class="flex flex-col h-full">
                <div class="text-3xl font-black text-slate-800 tracking-tight mt-2 text-center" v-if="selectedHosts.length === 1">
                  {{ comparisonData[selectedHosts[0].hostid]?.sessions?.value?.toLocaleString() || 0 }}
                </div>
                <apexchart class="mt-auto" type="area" height="120" :options="sessionOptions" :series="sessionSeries" />
              </div>
            </div>

            <!-- Critical Log -->
            <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 flex flex-col">
              <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-3">CRÍTICO LOG</span>
              <div class="flex flex-col gap-2 overflow-y-auto h-[160px] pr-2 custom-scrollbar flex-1">
                <div v-for="prob in combinedLogs" :key="prob.eventid" 
                     class="border border-slate-100 rounded-lg p-2.5 bg-slate-50 hover:bg-white transition-colors group cursor-pointer shadow-sm"
                     @click="toggleLog(prob.eventid)">
                  <div class="flex items-start gap-2">
                    <span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 text-slate-600 mt-0.5 shrink-0">{{ formatTime(prob.clock) }}</span>
                    <span :class="prob.severity === '5' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'" class="px-1.5 py-0.5 rounded text-[9px] font-bold mt-0.5 shrink-0 whitespace-nowrap">{{ prob.severity === '5' ? '🔴 Critical' : '🟡 Warning' }}</span>
                    <div class="flex-1 min-w-0">
                      <p class="text-xs font-semibold text-slate-700 truncate group-hover:text-blue-600 transition-colors">[{{ prob._hostname }}] {{ prob.name }}</p>
                      
                      <!-- Expanded Details -->
                      <div v-if="expandedLogs.has(prob.eventid)" class="mt-2 text-[10px] text-slate-500 whitespace-pre-wrap font-mono bg-white p-2 border border-slate-100 rounded">
                        <strong>Evento Completo:</strong><br/>
                        {{ prob.name }}<br/>
                        <strong>ID Evento:</strong> {{ prob.eventid }}
                      </div>
                    </div>
                    <button class="text-slate-400 shrink-0 hover:text-blue-500">
                      <svg class="w-4 h-4 transform transition-transform" :class="{'rotate-180': expandedLogs.has(prob.eventid)}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                    </button>
                  </div>
                </div>
                <div v-if="!combinedLogs.length" class="text-slate-400 italic text-center py-6 text-sm">No critical events</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Expanded Chart Modal -->
    <div v-if="expandedChart" class="fixed inset-0 z-[60] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 lg:p-8">
      <div class="bg-white w-full max-w-6xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden relative animate-fade-in-up">
        <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <h3 class="font-bold text-lg text-slate-800 tracking-tight">{{ expandedTitle }}</h3>
          <button @click="expandedChart = null" class="text-slate-400 hover:text-red-500 hover:bg-red-50 p-2 rounded-full transition-colors flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div class="flex-1 p-6 min-h-0 bg-white">
          <apexchart type="line" width="100%" height="100%" :options="expandedOptions" :series="expandedSeries" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import zabbixService from '../services/zabbix.service';

const hosts = ref([]);
const cpuTrendSeries = ref([]);
const ramTrendSeries = ref([]);

const searchQuery = ref('');
const osFilter = ref('all');

const loadingHosts = ref(true);
const loadingTrends = ref(true);

const showDetail = ref(false);
const selectedHost = ref(null);
const selectedHosts = ref([]);
const comparisonData = ref({});
const loadingDetail = ref(false);

const expandedChart = ref(null);
const expandedLogs = ref(new Set());

const toggleLog = (eventId) => {
  const newSet = new Set(expandedLogs.value);
  if (newSet.has(eventId)) newSet.delete(eventId);
  else newSet.add(eventId);
  expandedLogs.value = newSet;
};

const expandChart = (type) => {
  expandedChart.value = type;
};

const expandedTitle = computed(() => {
  if (expandedChart.value === 'cpu') return 'Histórico Detallado: CPU (%)';
  if (expandedChart.value === 'ram') return 'Histórico Detallado: RAM Usada (%)';
  if (expandedChart.value === 'net') return 'Histórico Detallado: Tráfico de Red (Kbps/Mbps)';
  if (expandedChart.value === 'latency') return 'Histórico Detallado: Latencia de Disco (Queue Length)';
  if (expandedChart.value === 'sessions') return 'Histórico Detallado: Firewall Sessions';
  return '';
});

const expandedSeries = computed(() => {
  if (expandedChart.value === 'cpu') return cpuSeries.value;
  if (expandedChart.value === 'ram') return ramSeries.value;
  if (expandedChart.value === 'net') return netSeries.value;
  if (expandedChart.value === 'latency') return latencySeries.value;
  if (expandedChart.value === 'sessions') return sessionSeries.value;
  return [];
});

const expandedOptions = computed(() => {
  let base = {};
  if (expandedChart.value === 'cpu' || expandedChart.value === 'ram') base = detailAreaOptions;
  else if (expandedChart.value === 'net') base = netTrafficOptions;
  else if (expandedChart.value === 'latency') base = latencyOptions;
  else if (expandedChart.value === 'sessions') base = { ...sessionOptions, chart: { ...sessionOptions.chart, sparkline: { enabled: false } }, stroke: { width: 2 }, xaxis: { type: 'datetime', labels: { style: { fontSize: '9px', colors: '#94a3b8' } } }, grid: { borderColor: '#f1f5f9' }, yaxis: { labels: { style: { fontSize: '9px', colors: '#94a3b8' } } } };

  // Modificar base clone para resolución más alta
  return {
    ...base,
    chart: { ...base.chart, toolbar: { show: true }, zoom: { enabled: true } },
    legend: { ...base.legend, fontSize: '13px' },
    xaxis: { ...base.xaxis, labels: { ...base.xaxis?.labels, style: { fontSize: '11px', colors: '#64748b' } } },
    yaxis: { ...base.yaxis, labels: { ...base.yaxis?.labels, style: { fontSize: '11px', colors: '#64748b' }, formatter: base.yaxis?.labels?.formatter } }
  };
});

let globalTimer = null;
let detailTimer = null;

const isSecurityMode = ref(false);

const timeRanges = [
  { label: '10 Min', value: 600 },
  { label: '30 Min', value: 1800 },
  { label: '1 Hora', value: 3600 },
  { label: '3 Horas', value: 10800 },
  { label: '6 Horas', value: 21600 },
  { label: '12 Horas', value: 43200 },
  { label: '24h', value: 86400 },
  { label: '3d', value: 259200 },
  { label: '7d', value: 604800 }
];
const selectedRange = ref(3600);

const setTimeRange = (seconds) => {
  if (selectedRange.value === seconds) return;
  selectedRange.value = seconds;
  refreshAll();
};

const getTimeParams = () => {
  const time_till = Math.floor(Date.now() / 1000);
  const time_from = time_till - selectedRange.value;
  return { time_from, time_till };
};

// Mock suave SOLO cuando no hay historial (sparklines vacías). Nunca pisa
// datos reales ni rellena huecos con 0.
const generateMockData = (baseVal, volatility) => {
  const data = [];
  let time = Date.now() - 3600000;
  let current = Number.isFinite(baseVal) ? Math.min(100, Math.max(0, baseVal)) : 5;
  for (let i = 0; i < 30; i++) {
    current = Math.max(0, Math.min(100, current + (Math.random() - 0.5) * volatility));
    data.push([time, parseFloat(current.toFixed(2))]);
    time += 120000;
  }
  return data;
};

const sanitizeHistory = (data, isPercentage = true, gapThresholdMs = 240000) => {
  if (!Array.isArray(data)) return [];
  
  // Filtrar, parsear y ordenar los puntos base
  const cleanData = data
    .filter((p) => Array.isArray(p) && p.length >= 2)
    .map(([t, v]) => {
      if (v === null || v === undefined || v === '') return null;
      const n = Number(v);
      const ts = Number(t);
      if (!Number.isFinite(n) || !Number.isFinite(ts)) return null;
      if (isPercentage && (n < 0 || n > 100)) return null;
      return [ts, n];
    })
    .filter(Boolean)
    .sort((a, b) => a[0] - b[0]);
    
  if (cleanData.length <= 1) return cleanData;
  
  // Inyectar ceros en huecos grandes para evitar interpolación (trazado de líneas en diagonal largas)
  const gapFilledData = [];
  gapFilledData.push(cleanData[0]);
  
  for (let i = 1; i < cleanData.length; i++) {
    const prev = cleanData[i - 1];
    const curr = cleanData[i];
    
    // Si la diferencia de tiempo entre dos puntos excede el umbral (ej. 4 minutos)
    if (curr[0] - prev[0] > gapThresholdMs) {
      // Inyectamos un 0 un milisegundo después del último dato conocido
      gapFilledData.push([prev[0] + 1000, 0]);
      // Y otro 0 un milisegundo antes del nuevo dato que acaba de llegar
      gapFilledData.push([curr[0] - 1000, 0]);
    }
    
    gapFilledData.push(curr);
  }
  
  return gapFilledData;
};

const downsample = (data, maxPoints = 24) => {
  if (!data.length || data.length <= maxPoints) return data;
  const step = (data.length - 1) / (maxPoints - 1);
  const out = [];
  for (let i = 0; i < maxPoints; i++) {
    out.push(data[Math.round(i * step)]);
  }
  return out;
};

const formatPct = (val) => {
  const n = Number(val);
  if (!Number.isFinite(n)) return '—';
  return `${n.toFixed(2)}%`;
};

const formatNetworkTraffic = (bps) => {
  if (!bps || bps === 0) return '0 Kbps';
  if (bps < 1000) return `${Math.round(bps)} bps`;
  if (bps < 1000000) return `${(bps / 1000).toFixed(1)} Kbps`;
  if (bps < 1000000000) return `${(bps / 1000000).toFixed(1)} Mbps`;
  return `${(bps / 1000000000).toFixed(2)} Gbps`;
};

const getColorForServer = (name) => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const chartPalette = ['#1a73e8', '#34a853', '#fbbc04', '#ea4335', '#a142f4', '#46bdc6', '#ff6d00', '#c51162', '#00bfa5'];
  return chartPalette[Math.abs(hash) % chartPalette.length];
};

const mapSeries = (series = []) =>
  series.map((s) => ({
    name: s.name,
    data: sanitizeHistory(s.data),
    color: getColorForServer(s.name)
  })).filter((s) => s.data.length > 1).sort((a, b) => a.name.localeCompare(b.name));

// --- Data Fetching ---

const fetchTrends = async (time_from, time_till) => {
  try {
    const res = await zabbixService.getGlobalTrends(time_from, time_till);
    if (res.status === 'success') {
      cpuTrendSeries.value = mapSeries(res.data.cpu_trends);
      ramTrendSeries.value = mapSeries(res.data.ram_trends);
    }
  } catch (e) { console.error(e); }
  loadingTrends.value = false;
};

const previousStatusMap = ref({});

const playAlertSound = () => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const duration = 10;
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();
    
    oscillator.type = 'square';
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    
    for (let i = 0; i < duration * 2; i++) {
       const time = ctx.currentTime + i * 0.5;
       gainNode.gain.setValueAtTime(0.05, time);
       gainNode.gain.setValueAtTime(0, time + 0.25);
       oscillator.frequency.setValueAtTime(i % 2 === 0 ? 800 : 1000, time);
    }
    
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + duration);
  } catch (err) {
    console.warn("Audio autoplay blocked", err);
  }
};

const fetchHosts = async (time_from, time_till) => {
  try {
    const res = await zabbixService.getAllHosts(time_from, time_till);
    if (res.status === 'success') {
      hosts.value = res.data.map(h => {
        const cpuHistory = sanitizeHistory(h.cpu_history);
        const maxCpuClock = cpuHistory.length > 0 ? cpuHistory[cpuHistory.length - 1][0] : Infinity;
        const clipHistory = (hist) => {
          if (h.status !== 'Offline') return hist;
          const clipped = hist.filter(p => p[0] <= maxCpuClock + 60000);
          clipped.push([Date.now(), null]);
          return clipped;
        };
        
        if (h.status === 'Offline') cpuHistory.push([Date.now(), null]);
        const ramHistory = clipHistory(sanitizeHistory(h.ram_history));
        const netInHistory = clipHistory(sanitizeHistory(h.net_in_history, false));
        const netOutHistory = clipHistory(sanitizeHistory(h.net_out_history, false));
        
        return {
          ...h,
          cpu_history: downsample(cpuHistory.length ? cpuHistory : generateMockData(h.cpu, 2)),
          ram_history: downsample(ramHistory.length ? ramHistory : generateMockData(h.ram, 1)),
          net_in_history: downsample(netInHistory.length ? netInHistory : generateMockData(h.net_in, 10000)),
          net_out_history: downsample(netOutHistory.length ? netOutHistory : generateMockData(h.net_out, 10000))
        };
      });

      let playedSoundThisTick = false;
      hosts.value.forEach(h => {
        const prevStatus = previousStatusMap.value[h.hostid];
        if (h.status === 'Offline' && prevStatus !== 'Offline' && prevStatus !== undefined) {
          if (!playedSoundThisTick) {
            playAlertSound();
            playedSoundThisTick = true;
          }
        }
        previousStatusMap.value[h.hostid] = h.status;
      });
    }
  } catch (e) { console.error(e); }
  loadingHosts.value = false;
};

const refreshAll = async (showLoading = true) => {
  if (showLoading) {
    loadingTrends.value = loadingHosts.value = true;
  }
  const { time_from, time_till } = getTimeParams();
  await Promise.all([fetchTrends(time_from, time_till), fetchHosts(time_from, time_till)]);
};

// --- Detail View (Multi-Server) ---

const availableHostsToAdd = computed(() => {
  return hosts.value.filter(h => !selectedHosts.value.some(sh => sh.hostid === h.hostid));
});

const openDetail = async (host) => {
  selectedHost.value = host;
  selectedHosts.value = [host];
  comparisonData.value = {};
  showDetail.value = true;
  await fetchDetailForHost(host);
  if (detailTimer) clearInterval(detailTimer);
  detailTimer = setInterval(fetchAllDetails, 30000);
};

const addHost = async (hostid) => {
  if (!hostid) return;
  const host = hosts.value.find(h => h.hostid === hostid);
  if (host && !selectedHosts.value.some(h => h.hostid === hostid)) {
    selectedHosts.value.push(host);
    await fetchDetailForHost(host);
  }
};

const removeHost = (hostid) => {
  selectedHosts.value = selectedHosts.value.filter(h => h.hostid !== hostid);
  const newData = { ...comparisonData.value };
  delete newData[hostid];
  comparisonData.value = newData;
  if (selectedHosts.value.length === 0) closeDetail();
};

const closeDetail = () => {
  showDetail.value = false;
  selectedHost.value = null;
  selectedHosts.value = [];
  comparisonData.value = {};
  if (detailTimer) clearInterval(detailTimer);
};

const fetchAllDetails = async () => {
  await Promise.all(selectedHosts.value.map(h => fetchDetailForHost(h)));
};

const fetchDetailForHost = async (host) => {
  loadingDetail.value = true;
  try {
    const res = await zabbixService.getHostDetail(host.hostid);
    if (res.status === 'success') {
      const data = res.data;
      data.cpu.history = sanitizeHistory(data.cpu.history, true);
      let maxCpuClock = data.cpu.history.length > 0 ? data.cpu.history[data.cpu.history.length - 1][0] : Infinity;
      
      const clipHistory = (hist) => {
        if (host.status !== 'Offline') return hist;
        const clipped = hist.filter(p => p[0] <= maxCpuClock + 60000);
        clipped.push([Date.now(), null]);
        return clipped;
      };
      
      if (host.status === 'Offline') data.cpu.history.push([Date.now(), null]);
      
      data.ram.history = clipHistory(sanitizeHistory(data.ram.history, true));
      if (data.latency) {
        data.latency.history = clipHistory(sanitizeHistory(data.latency.history, false));
      }
      
      if (!data.cpu.history.length) data.cpu.history = generateMockData(data.cpu.value, 2);
      if (!data.ram.history.length) data.ram.history = generateMockData(data.ram.value, 1);

      if (data.sessions) {
        data.sessions.history = clipHistory(sanitizeHistory(data.sessions.history, false));
      }

      if (data.interfaces) {
        Object.keys(data.interfaces).forEach(iface => {
          data.interfaces[iface].in.history = clipHistory(sanitizeHistory(data.interfaces[iface].in.history, false));
          data.interfaces[iface].out.history = clipHistory(sanitizeHistory(data.interfaces[iface].out.history, false));
          if (!data.interfaces[iface].in.history.length) data.interfaces[iface].in.history = generateMockData(4000, 2000);
          if (!data.interfaces[iface].out.history.length) data.interfaces[iface].out.history = generateMockData(4000, 2000);
        });
      }
      
      comparisonData.value = { ...comparisonData.value, [host.hostid]: data };
    }
  } catch (e) { console.error(e); }
  loadingDetail.value = false;
};

// --- Helpers & Chart Options ---

const getStatusColor = (val) => {
  if (val < 60) return '#10b981'; // Green
  if (val < 85) return '#f59e0b'; // Yellow
  return '#ef4444'; // Red
};

// El nombre visible de algunos hosts en Zabbix trae el SO como sufijo
// (ej. "Sanson LNX", "Ser Conteo WIN"). Lo separamos para pintarlo como
// una etiqueta pequeña junto al nombre, tal como se ve en el mockup.
const parseHostname = (hostname) => {
  if (!hostname) return { main: '', tag: null };
  const match = hostname.match(/^(.*\S)\s+(LNX|WIN|UNIX|MAC)$/i);
  if (match) return { main: match[1], tag: match[2].toUpperCase() };
  return { main: hostname, tag: null };
};

// OS Fallback
const getDetectedOS = (host) => {
  const osStr = (host.os || '').toLowerCase();
  const nameStr = (host.hostname || host.name || '').toLowerCase();

  if (osStr.includes('windows') || nameStr.includes('win') || nameStr.includes('servidor')) {
    return { osName: 'Windows Server' };
  } else if (osStr.includes('linux') || osStr.includes('ubuntu') || nameStr.includes('lnx')) {
    return { osName: 'Linux' };
  } else if (osStr.includes('forti') || nameStr.includes('forti') || nameStr.includes('firewall')) {
    return { osName: 'FortiOS' };
  }
  
  return { osName: host.os || 'Desconocido' };
};

// Estados del agente Zabbix: 1=Available, 2=Unavailable, 0=Unknown
const statusMeta = (status) => {
  if (status === 'Online') return { label: 'Active', dotClass: 'bg-emerald-500', textClass: 'text-emerald-700' };
  if (status === 'Offline') return { label: 'Critical', dotClass: 'bg-red-500', textClass: 'text-red-700' };
  return { label: 'Warning', dotClass: 'bg-amber-500', textClass: 'text-amber-700' };
};

const formatTime = (clock) => {
  const d = new Date(clock * 1000);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const mapTraffic = (history, isInbound) => {
  if (!history || !Array.isArray(history)) return [];
  return history.map(([t, v]) => {
    // Convertir de Bytes/sec a Kilobits/sec (Kbps)
    let kbps = (v * 8) / 1000;
    // Hacemos el tráfico de salida negativo para graficarlo invertido
    return [t, parseFloat(kbps.toFixed(2)) * (isInbound ? 1 : -1)];
  });
};

// ApexCharts Configurations
const MONTHS_ES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];

const formatTooltipHeader = (ts) => {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${d.getDate()} ${MONTHS_ES[d.getMonth()]}, ${hh}:${mm}:${ss}`;
};

const nearestSeriesValue = (seriesIndex, hoverTs, w) => {
  const xs = w.globals.seriesX[seriesIndex] || [];
  const ys = w.globals.series[seriesIndex] || [];
  if (!xs.length) return null;
  let bestIdx = 0;
  let bestDiff = Infinity;
  for (let i = 0; i < xs.length; i++) {
    const diff = Math.abs(xs[i] - hoverTs);
    if (diff < bestDiff) {
      bestDiff = diff;
      bestIdx = i;
    }
  }
  if (bestDiff > 180000) return null;
  const val = ys[bestIdx];
  return Number.isFinite(val) ? val : null;
};

const renderTrendTooltip = ({ seriesIndex, dataPointIndex, w }) => {
  const hoverTs = w.globals.seriesX?.[seriesIndex]?.[dataPointIndex] ?? w.globals.seriesX?.[0]?.[dataPointIndex];
  if (!hoverTs) return '';

  const rows = (w.globals.seriesNames || [])
    .map((name, i) => ({
      name,
      color: w.globals.colors[i],
      val: nearestSeriesValue(i, hoverTs, w)
    }))
    .filter((r) => r.val !== null)
    .sort((a, b) => b.val - a.val);

  const body = rows.map((r) => `
    <div style="display:flex;align-items:center;gap:8px;padding:4px 0;line-height:1.2;opacity:1;">
      <span style="width:10px;height:10px;border-radius:2px;background:${r.color};flex-shrink:0;"></span>
      <span style="flex:1;font-size:11px;color:#000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${r.name}</span>
      <span style="font-size:11px;font-weight:600;color:#000;font-variant-numeric:tabular-nums;padding-left:12px;">${r.val.toFixed(2)}%</span>
    </div>
  `).join('');

  const d = new Date(hoverTs);
  const dateStr = `${d.getDate()} ${MONTHS_ES[d.getMonth()].toLowerCase()} ${d.getFullYear()}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;

  return `
    <div class="custom-tooltip-box" style="background:#fff;border:1px solid #e2e8f0;border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.1);min-width:180px;max-width:240px;padding:10px;">
      <div style="font-size:11px;color:#64748b;margin-bottom:6px;">
        ${dateStr}
      </div>
      ${body || '<div style="font-size:11px;color:#94a3b8;">Sin datos</div>'}
    </div>
  `;
};

const trendOptions = (forceDir) => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, dynamicAnimation: { speed: 300 } },
    fontFamily: 'inherit',
    parentHeightOffset: 0
  },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.20,
      opacityTo: 0.0,
      stops: [0, 100]
    }
  },
  stroke: { width: 1.5, curve: 'smooth' },
  markers: {
    size: 0,
    hover: { sizeOffset: 4 }
  },
  states: {
    hover: { filter: { type: 'none' } },
    active: { filter: { type: 'none' } }
  },
  xaxis: {
    type: 'datetime',
    labels: { datetimeUTC: false, datetimeFormatter: { hour: 'HH:mm', minute: 'HH:mm' }, style: { fontSize: '10px', colors: '#64748b' } },
    axisBorder: { show: true, color: '#e2e8f0' },
    axisTicks: { show: true, color: '#e2e8f0' },
    tooltip: { enabled: false },
    crosshairs: {
      show: true,
      width: 1,
      position: 'back',
      opacity: 1,
      stroke: { color: '#94a3b8', width: 1, dashArray: 4 }
    }
  },
  yaxis: {
    min: 0,
    max: (max) => max < 5 ? 5 : Math.ceil(max * 1.2),
    tickAmount: 5,
    forceNiceScale: true,
    decimalsInFloat: 0,
    labels: {
      style: { fontSize: '10px', colors: '#64748b' },
      formatter: (val) => String(Math.round(val))
    }
  },
  legend: { 
    position: 'bottom', 
    fontSize: '11px', 
    fontWeight: 600, 
    markers: { width: 10, height: 10, radius: 0 }, 
    itemMargin: { horizontal: 8 } 
  },
  tooltip: {
    enabled: true,
    shared: true,
    intersect: false,
    followCursor: true,
    cssClass: `force-tooltip-${forceDir}`,
    custom: renderTrendTooltip
  },
  grid: {
    show: true,
    borderColor: '#e2e8f0',
    strokeDashArray: 0,
    position: 'back',
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: false } }, // Grid minimalista: quitamos líneas Y también
    padding: { left: 8, right: 8, top: 8, bottom: 0 }
  }
});

const sparklineOptions = (lineColor) => ({
  chart: {
    type: 'area',
    sparkline: { enabled: true },
    animations: { enabled: false },
    toolbar: { show: false },
    parentHeightOffset: 0,
    offsetX: 0,
    offsetY: 0
  },
  stroke: { curve: 'smooth', width: 1.5 },
  fill: {
    type: 'gradient',
    gradient: {
      type: 'vertical',
      shadeIntensity: 1,
      opacityFrom: 0.85,
      opacityTo: 0.15,
      colorStops: [
        { offset: 0, color: '#ef4444', opacity: 0.85 },
        { offset: 50, color: '#f59e0b', opacity: 0.6 },
        { offset: 100, color: '#10b981', opacity: 0.25 }
      ]
    }
  },
  dataLabels: { enabled: false },
  legend: { show: false },
  tooltip: { enabled: false },
  xaxis: {
    labels: { show: false },
    axisBorder: { show: false },
    axisTicks: { show: false },
    tooltip: { enabled: false }
  },
  yaxis: {
    show: false,
    min: 0,
    max: 100,
    labels: { show: false }
  },
  grid: {
    show: false,
    padding: { left: 0, right: 0, top: 0, bottom: 0 },
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: false } }
  },
  colors: [lineColor]
});

// --- Computed Series for Comparison ---
const cpuSeries = computed(() => selectedHosts.value.map(h => ({
  name: h.hostname, data: comparisonData.value[h.hostid]?.cpu?.history || []
})));

const ramSeries = computed(() => selectedHosts.value.map(h => ({
  name: h.hostname, data: comparisonData.value[h.hostid]?.ram?.history || []
})));


const availableInterfaces = computed(() => {
  const set = new Set();
  selectedHosts.value.forEach(h => {
    const d = comparisonData.value[h.hostid];
    if (d && d.interfaces) {
      Object.keys(d.interfaces).forEach(i => set.add(i));
    }
  });
  return Array.from(set).sort();
});

const selectedInterface = ref('');

watch(availableInterfaces, (newVal) => {
  if (newVal.length > 0 && !newVal.includes(selectedInterface.value)) {
    selectedInterface.value = newVal[0];
  } else if (newVal.length === 0) {
    selectedInterface.value = '';
  }
});

const netSeries = computed(() => {
  const series = [];
  const iface = selectedInterface.value;
  if (!iface) return series;

  selectedHosts.value.forEach(h => {
    const d = comparisonData.value[h.hostid];
    if(d && d.interfaces && d.interfaces[iface]) {
      series.push({ name: `${h.hostname} (In)`, data: mapTraffic(d.interfaces[iface].in.history, true) });
      series.push({ name: `${h.hostname} (Out)`, data: mapTraffic(d.interfaces[iface].out.history, false) });
    }
  });
  return series;
});

const hasFirewallSessions = computed(() => {
  return selectedHosts.value.some(h => {
    const d = comparisonData.value[h.hostid];
    return d && d.sessions && d.sessions.value !== null;
  });
});

const isFortiGateSelected = computed(() => {
  return selectedHosts.value.some(h => {
    const nameStr = (h.hostname || h.name || '').toLowerCase();
    return nameStr.includes('forti') || nameStr.includes('firewall');
  });
});

const sessionSeries = computed(() => selectedHosts.value.map(h => ({
  name: h.hostname, data: comparisonData.value[h.hostid]?.sessions?.history || []
})));

const filteredHosts = computed(() => {
  return hosts.value.filter(h => {
    // Modo Seguridad (FortiGate V2)
    const nameStr = (h.hostname || h.name || '').toLowerCase();
    const isFirewall = nameStr.includes('forti') || nameStr.includes('firewall');
    
    if (isSecurityMode.value && !isFirewall) return false; // Solo firewalls en modo seguridad
    if (!isSecurityMode.value && isFirewall) return false; // Solo servidores en modo normal

    // Search Query
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      if (!h.hostname.toLowerCase().includes(q) && !h.ip.includes(q)) return false;
    }
    // OS Filter
    if (osFilter.value !== 'all') {
      const isWin = (h.os || '').toLowerCase().includes('windows');
      if (osFilter.value === 'windows' && !isWin) return false;
      if (osFilter.value === 'linux' && isWin) return false; 
    }
    return true;
  }).sort((a, b) => {
    // Ordenar para que los Offline queden de primeros
    if (a.status === 'Offline' && b.status !== 'Offline') return -1;
    if (b.status === 'Offline' && a.status !== 'Offline') return 1;
    // Segundo criterio: Warnings
    if (a.status === 'Warning' && b.status !== 'Warning') return -1;
    if (b.status === 'Warning' && a.status !== 'Warning') return 1;
    return 0;
  });
});

const globalFirewallSessions = computed(() => {
  return hosts.value.reduce((acc, h) => acc + (h.sessions || 0), 0);
});

const globalVpnTunnels = computed(() => {
  return hosts.value.reduce((acc, h) => acc + (h.vpn_tunnels || 0), 0);
});

const globalNetIn = computed(() => {
  return hosts.value.reduce((acc, h) => acc + (h.net_in || 0), 0);
});

const latencySeries = computed(() => selectedHosts.value.map(h => ({
  name: h.hostname, data: comparisonData.value[h.hostid]?.latency?.history || []
})));

const combinedLogs = computed(() => {
  let all = [];
  selectedHosts.value.forEach(h => {
    const probs = comparisonData.value[h.hostid]?.recent_problems || [];
    probs.forEach(p => all.push({ ...p, _hostname: h.hostname }));
  });
  return all.sort((a,b) => b.clock - a.clock);
});

// ApexCharts Configurations
const dynamicColors = ['#1a73e8', '#34a853', '#fbbc04', '#ea4335', '#a142f4', '#46bdc6'];

const detailAreaOptions = {
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 2 },
  colors: dynamicColors,
  fill: { type: 'solid', opacity: 1 },
  xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } }, axisBorder: { show: true, color: '#e2e8f0' }, axisTicks: { show: true, color: '#e2e8f0' }, tooltip: { enabled: false } },
  yaxis: { min: 0, max: 100, tickAmount: 2, labels: { style: { fontSize: '9px', colors: '#94a3b8' } } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { borderColor: '#f1f5f9', padding: { top: 0, bottom: 0, left: 10, right: 0 } }
};

const latencyOptions = {
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'straight', width: 2 },
  colors: dynamicColors,
  xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } }, axisBorder: { show: true, color: '#e2e8f0' }, axisTicks: { show: true, color: '#e2e8f0' } },
  yaxis: { min: 0, labels: { style: { fontSize: '9px', colors: '#94a3b8' } } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { borderColor: '#f1f5f9', padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: {
    y: { formatter: (val) => val.toFixed(2) }
  }
};

const netTrafficOptions = {
  chart: { type: 'line', stacked: false, toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 1.5 },
  colors: dynamicColors,
  dataLabels: { enabled: false },
  xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } }, axisBorder: { show: true, color: '#e2e8f0' }, axisTicks: { show: true, color: '#e2e8f0' } },
  yaxis: {
    tickAmount: 4,
    labels: {
      style: { fontSize: '9px', colors: '#94a3b8' },
      formatter: (val) => Math.abs(val) > 1000 ? (Math.abs(val)/1000).toFixed(1) + ' Mbps' : Math.abs(val).toFixed(0) + ' Kbps'
    }
  },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { borderColor: '#f1f5f9', padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: {
    y: { formatter: (val) => Math.abs(val).toFixed(2) + ' Kbps' }
  }
};

const sessionOptions = {
  chart: { type: 'area', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit', sparkline: { enabled: true } },
  stroke: { curve: 'smooth', width: 2 },
  colors: ['#8b5cf6'], // Purple tone for sessions
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100] } },
  xaxis: { type: 'datetime', tooltip: { enabled: false } },
  yaxis: { min: 0 },
  tooltip: {
    y: { formatter: (val) => Math.round(val).toLocaleString() }
  }
};

const diskPieOptions = {
  chart: { type: 'donut', fontFamily: 'inherit', animations: { enabled: false } },
  labels: ['Usado', 'Libre'],
  colors: ['#ef4444', '#10b981'],
  plotOptions: {
    pie: {
      donut: { 
        size: '75%', 
        labels: { 
          show: true, 
          name: { show: false }, 
          value: { show: true, fontSize: '18px', fontWeight: 'bold', color: '#1e293b', formatter: (v) => v + '%' }, 
          total: { show: true, showAlways: true, label: '', formatter: function(w) { return w.globals.seriesTotals[0] + '%' } } 
        } 
      }
    }
  },
  dataLabels: { enabled: false },
  legend: { 
    show: true, 
    position: 'bottom',
    fontSize: '11px',
    markers: { width: 10, height: 10, radius: 2 }
  },
  stroke: { show: false },
  tooltip: {
    y: { formatter: (val) => val.toFixed(1) + '%' }
  }
};


onMounted(() => {
  refreshAll();
  globalTimer = setInterval(() => refreshAll(false), 10000); // 10 seconds refresh, invisible
});

onUnmounted(() => {
  if (globalTimer) clearInterval(globalTimer);
  if (detailTimer) clearInterval(detailTimer);
});
</script>

<style scoped>
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sparkline-wrap :deep(.apexcharts-yaxis),
.sparkline-wrap :deep(.apexcharts-xaxis),
.sparkline-wrap :deep(.apexcharts-grid),
.sparkline-wrap :deep(.apexcharts-gridline),
.sparkline-wrap :deep(.apexcharts-xaxis-tick),
.sparkline-wrap :deep(.apexcharts-inner > line) {
  display: none !important;
}

:deep(.apexcharts-tooltip) {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}

:deep(.apexcharts-xcrosshairs),
:deep(.apexcharts-xcrosshairs.apexcharts-active) {
  opacity: 1 !important;
}

/* Tooltip Positioning Hacks */
:deep(.apexcharts-tooltip.force-tooltip-right),
:deep(.apexcharts-tooltip.force-tooltip-left) {
  width: 0 !important;
  height: 0 !important;
  overflow: visible !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  transition: none !important;
}

:deep(.custom-tooltip-box) {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

:deep(.force-tooltip-right .custom-tooltip-box) {
  left: 15px;
}

:deep(.force-tooltip-left .custom-tooltip-box) {
  right: 15px;
}

.trend-chart :deep(.apexcharts-svg:has(.apexcharts-series.apexcharts-active) .apexcharts-series[rel]) {
  opacity: 0.18;
  transition: opacity 0.12s ease;
}

.trend-chart :deep(.apexcharts-svg:has(.apexcharts-series.apexcharts-active) .apexcharts-series[rel].apexcharts-active) {
  opacity: 1;
}
</style>
