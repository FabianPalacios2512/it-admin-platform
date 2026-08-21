<template>
  <div class="zabbix-monitoring-container flex flex-col gap-4 font-sans pb-10">
    <!-- Header -->
    <header class="flex justify-between items-center shrink-0">
      <div>
        <h1 class="text-xl font-bold text-slate-800 tracking-tight leading-tight">Monitoreo Zabbix V2</h1>
        <p class="text-xs text-slate-500 mt-0.5">Estado en tiempo real de todos los servidores monitoreados</p>
      </div>
      <div class="flex items-center gap-4">
        <!-- Templates Selector (iOS Segmented Control Style) -->
        <div class="inline-flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button @click="currentTemplate = 'global'" :class="currentTemplate === 'global' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">Global</button>
          <button @click="currentTemplate = 'issabel'" :class="currentTemplate === 'issabel' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">PBX Issabel</button>
          <button @click="currentTemplate = 'fortigate'" :class="currentTemplate === 'fortigate' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">FortiGate V2</button>
        </div>

        <!-- Time Picker (Compact Dropdown) -->
        <div class="relative flex items-center">
          <select :value="selectedRange" @change="setTimeRange(Number($event.target.value))" class="appearance-none bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold rounded-lg pl-3 pr-8 py-2 hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer">
            <option v-for="tr in timeRanges" :key="tr.value" :value="tr.value">{{ tr.label }}</option>
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
          </div>
        </div>

        <button @click="refreshAll" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all flex items-center gap-2">
          <i class="fas fa-sync-alt" :class="{'animate-spin': loadingTrends || loadingHosts}"></i>
          Refrescar
        </button>
      </div>
    </header>

    <!-- Global Trends (Modo Servidores) -->
    <div v-if="currentTemplate === 'global'" class="grid grid-cols-1 lg:grid-cols-5 gap-3 shrink-0">
      <div class="trend-chart lg:col-span-2 bg-white px-4 pt-4 pb-2 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative min-h-[250px]">
        <div class="flex justify-between items-center mb-1">
          <h2 class="text-sm font-bold text-slate-800 tracking-wide">CPU GLOBAL TREND (TOP 5)</h2>
        </div>
        <div v-if="loadingTrends" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-xl"><div class="spinner"></div></div>
        <apexchart type="line" height="220" :options="trendOptions('right')" :series="cpuTrendSeries" />
      </div>
      <div class="trend-chart lg:col-span-2 bg-white px-4 pt-4 pb-2 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative min-h-[250px]">
        <div class="flex justify-between items-center mb-1">
          <h2 class="text-sm font-bold text-slate-800 tracking-wide">MEMORY GLOBAL TREND (TOP 5)</h2>
        </div>
        <div v-if="loadingTrends" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10 rounded-xl"><div class="spinner"></div></div>
        <apexchart type="line" height="220" :options="trendOptions('left')" :series="ramTrendSeries" />
      </div>
      <!-- Resumen PBX (Mini) -->
      <div class="trend-chart lg:col-span-1 bg-white px-4 pt-4 pb-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative min-h-[250px] flex flex-col">
        
        <div class="flex justify-between items-center mb-4 border-b pb-2">
          <h2 class="text-sm font-bold text-slate-800 tracking-wide">PBX STATUS</h2>
          <span v-if="pbxData.asterisk_down" class="bg-red-50 text-red-700 px-2 py-0.5 rounded-md text-[10px] font-bold border border-red-100 animate-pulse">CAÍDO</span>
          <span v-else class="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-md text-[10px] font-bold border border-emerald-100">ONLINE</span>
        </div>

        <div class="flex-1 flex flex-col justify-center gap-3">
          <div class="grid grid-cols-2 gap-2">
            <div class="col-span-2 bg-slate-50 rounded-md p-3 text-center border border-slate-100 flex flex-col justify-center items-center">
              <span class="text-[9px] text-slate-400 font-bold uppercase tracking-widest mb-1">Llamadas</span>
              <transition name="fade" mode="out-in">
                <span :key="pbxData.asterisk_down ? 'down' : pbxData.llamadas_activas" class="text-4xl font-black tracking-tighter leading-none block" :class="pbxData.asterisk_down ? 'text-red-600' : 'text-slate-800'">
                  {{ pbxData.asterisk_down ? '--' : pbxData.llamadas_activas }}
                </span>
              </transition>
            </div>
            
            <div class="bg-slate-50 rounded-md p-2 text-center border border-slate-100 flex flex-col items-center justify-center">
              <span class="text-[8px] font-bold uppercase tracking-widest text-slate-500 mb-1 leading-none">IVR</span>
              <div class="flex items-center gap-1 font-semibold text-[10px]">
                <span :class="['w-1.5 h-1.5 rounded-full', pbxData.robot_ivr === 1 ? 'bg-emerald-500' : 'bg-red-500']"></span>
                <span :class="pbxData.robot_ivr === 1 ? 'text-emerald-700' : 'text-red-700'">{{ pbxData.robot_ivr === 1 ? 'OK' : 'ERR' }}</span>
              </div>
            </div>
            
            <div class="bg-slate-50 rounded-md p-2 text-center border border-slate-100 flex flex-col items-center justify-center">
              <span class="text-[8px] font-bold uppercase tracking-widest text-slate-500 mb-1 leading-none">Rutas</span>
              <div class="flex items-center gap-1 font-semibold text-[10px]">
                <span :class="['w-1.5 h-1.5 rounded-full', (pbxData.ruta_opcion1 === 1 && pbxData.ruta_opcion2 === 1) ? 'bg-emerald-500' : 'bg-red-500']"></span>
                <span :class="(pbxData.ruta_opcion1 === 1 && pbxData.ruta_opcion2 === 1) ? 'text-emerald-700' : 'text-red-700'">
                  {{ (pbxData.ruta_opcion1 === 1 && pbxData.ruta_opcion2 === 1) ? 'OK' : 'ERR' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Issabel PBX Template -->
    <div v-if="currentTemplate === 'issabel'" class="flex flex-col gap-4 shrink-0">
      
      <!-- Fila 1: Core Metrics (NOC Light Theme) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Tarjeta 1: Estado del Motor -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 flex flex-col justify-between relative overflow-hidden transition-all">
          <div class="flex justify-between items-start mb-1">
            <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500">Estado del Motor</span>
          </div>
          <div class="flex items-center gap-3 mt-2">
            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0" :class="pbxData.asterisk_down ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'">
              <i class="fas fa-server text-xl drop-shadow-sm"></i>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-xl font-black tracking-tight truncate" :class="pbxData.asterisk_down ? 'text-red-600' : 'text-slate-800'">
                {{ pbxData.asterisk_down ? 'CAÍDO' : 'EN LÍNEA' }}
              </div>
              <div class="text-[9px] font-semibold text-slate-500 flex items-center gap-1.5 truncate">
                <span class="w-1.5 h-1.5 rounded-full inline-block shrink-0" :class="pbxData.asterisk_down ? 'bg-red-500' : 'bg-emerald-500'"></span>
                Asterisk PBX
              </div>
            </div>
          </div>
        </div>

        <!-- Tarjeta 2: Llamadas Activas -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 flex flex-col justify-between items-center text-center relative overflow-hidden transition-all">
          <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-1">Llamadas Activas</span>
          <div class="flex items-center gap-2 mt-1">
            <div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
              <i class="fas fa-phone-alt text-sm text-blue-500 drop-shadow-sm"></i>
            </div>
            <div class="text-3xl font-black font-mono tracking-tighter leading-none" :class="pbxData.asterisk_down ? 'text-red-500' : 'text-slate-800'">
              {{ pbxData.asterisk_down ? '--' : pbxData.llamadas_activas }}
            </div>
          </div>
          <span class="text-[8px] text-slate-400 font-bold uppercase mt-2 tracking-[0.1em]">Conexiones Concurrentes</span>
        </div>

        <!-- Tarjeta 3: Troncal SIP 101 -->
        <div class="bg-white rounded-md shadow-sm p-4 flex flex-col justify-between relative overflow-hidden transition-all"
             :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-50 border-l-4 border-y border-r border-red-500' : 'border border-gray-200'">
          <div class="flex justify-between items-start mb-1">
            <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-600' : ''">Troncal SIP (Claro/Tigo)</span>
          </div>
          <div class="flex items-center gap-3 mt-2">
            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down) ? 'bg-emerald-50 text-emerald-500' : ((pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-slate-50 text-slate-400')">
              <i class="fas fa-exclamation-triangle text-xl drop-shadow-sm" v-if="pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down"></i>
              <i class="fas fa-network-wired text-xl drop-shadow-sm" v-else></i>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-xl font-black tracking-tight truncate" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'text-slate-800' : ((pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-700' : 'text-slate-500')">
                {{ pbxData.server_down ? 'DESCONECT' : (pbxData.asterisk_down ? 'CAÍDO' : (pbxData.troncal_101 === 1 ? 'OK' : (pbxData.troncal_101 === 0 ? 'FALLA' : 'N/A'))) }}
              </div>
              <div class="text-[9px] font-semibold flex items-center gap-1.5 truncate" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-500' : 'text-slate-500'">
                <span class="w-1.5 h-1.5 rounded-full inline-block shrink-0" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'bg-emerald-500' : 'bg-red-600'"></span>
                Enlace [101]
              </div>
            </div>
          </div>
        </div>

        <!-- Tarjeta 4: Extensiones Registradas -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 flex flex-col justify-between items-center text-center relative overflow-hidden transition-all">
          <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-1">Ext. Registradas</span>
          <div class="flex items-center gap-2 mt-1">
            <div class="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
              <i class="fas fa-users text-sm text-emerald-500 drop-shadow-sm"></i>
            </div>
            <div class="text-2xl font-black font-mono tracking-tighter leading-none" :class="pbxData.asterisk_down ? 'text-red-500' : 'text-slate-800'">
              {{ pbxData.asterisk_down ? '-- / --' : pbxData.extensiones_registradas }}
            </div>
          </div>
          <span class="text-[8px] text-slate-400 font-bold uppercase mt-2 tracking-[0.1em]">Online / Total</span>
        </div>
      </div>

      <!-- Fila 2: Auditoría e Infraestructura -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2">
        <!-- Columna Izquierda: Auditor Sintético -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 transition-all flex flex-col relative overflow-hidden">
          <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-2 flex items-center gap-2 shrink-0 relative z-10">
            <i class="fas fa-robot text-blue-500 text-xs"></i> Auditor Sintético IVR
          </h3>
          <!-- Ondas de fondo sutiles -->
          <div class="absolute inset-0 opacity-[0.02] bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPgo8cGF0aCBkPSJNMCA1MCBRIDI1IDMwIDUwIDUwIFQgMTAwIDUwIiBzdHJva2U9IiMzYjgyZjYiIGZpbGw9Im5vbmUiIHN0cm9rZS13aWR0aD0iMiIgLz4KPHBhdGggZD0iTTAgNTAgUSAyNSA3MCA1MCA1MCBUIDEwMCA1MCIgc3Ryb2tlPSIjM2I4MmY2IiBmaWxsPSJub25lIiBzdHJva2Utd2lkdGg9IjIiIC8+Cjwvc3ZnPg==')] bg-center bg-no-repeat bg-cover"></div>
          
          <div class="flex-1 flex flex-row items-center gap-4 py-2 relative z-10">
            <div class="w-12 h-12 rounded-full flex items-center justify-center shrink-0 border" :class="(pbxData.robot_ivr === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'bg-emerald-50 border-emerald-200' : ((pbxData.robot_ivr === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-50 border-red-200' : 'bg-slate-100 border-slate-200')">
              <i class="fas fa-robot text-2xl" :class="(pbxData.robot_ivr === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'text-emerald-500' : ((pbxData.robot_ivr === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-500' : 'text-slate-400')"></i>
            </div>
            <div class="flex flex-col justify-center">
              <div class="text-sm font-black tracking-tight uppercase" :class="(pbxData.robot_ivr === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'text-emerald-600' : ((pbxData.robot_ivr === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-600' : 'text-slate-500')">
                {{ pbxData.server_down ? 'SERVIDOR DESCONECTADO' : (pbxData.asterisk_down ? 'FALLA (MOTOR CAÍDO)' : (pbxData.robot_ivr === 1 ? 'PASANDO CORRECTAMENTE' : (pbxData.robot_ivr === 0 ? '¡FALLA EN PRUEBA!' : 'SIN DATOS'))) }}
              </div>
              <div class="mt-1 flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                <span class="w-1.5 h-1.5 rounded-full" :class="(pbxData.robot_ivr === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'bg-emerald-500' : 'bg-slate-300'"></span>
                Última ejecución: Hace 1 min
              </div>
            </div>
          </div>
        </div>

        <!-- Columna Central: Opciones de Menú (Píldoras) -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 transition-all flex flex-col relative overflow-hidden">
          <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-2 flex items-center gap-2">
            <i class="fas fa-sitemap text-blue-500 text-xs"></i> Opciones de Menú
          </h3>
          <div class="flex flex-wrap gap-2 mt-1">
            <div v-for="i in 9" :key="i" class="px-2 py-1 rounded-full border flex items-center shadow-sm"
                 :class="(pbxData.ivr_options?.[i]?.value === 1) ? 'bg-white border-emerald-200 text-slate-700' : 'bg-slate-50 border-slate-200 text-slate-400'">
              <span class="w-1.5 h-1.5 rounded-full inline-block mr-1.5" :class="(pbxData.ivr_options?.[i]?.value === 1) ? 'bg-emerald-500' : 'bg-red-400'"></span>
              <span class="text-xs font-mono font-semibold">{{ getOptionName(i, pbxData.ivr_options?.[i]?.name) }}</span>
            </div>
          </div>
        </div>

        <!-- Columna Derecha: Almacenamiento PBX -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 transition-all flex flex-col justify-center relative">
          <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-2 flex items-center gap-2">
            <i class="fas fa-hdd text-blue-500 text-xs"></i> Almacenamiento PBX
          </h3>
          <div class="flex flex-col gap-2 mt-1">
            <div class="flex justify-between items-end">
              <div class="flex flex-col">
                <span class="text-xs font-semibold text-slate-700">Ruta de Grabaciones</span>
                <span class="text-[9px] font-mono text-slate-400">/var/spool/asterisk/monitor</span>
              </div>
              <span class="text-lg font-bold font-mono" :class="pbxData.almacenamiento_pbx > 80 ? 'text-red-600' : 'text-slate-600'">
                {{ pbxData.almacenamiento_pbx }}%
              </span>
            </div>
            <div class="h-2.5 w-full bg-slate-100 rounded-sm overflow-hidden border border-slate-200">
              <div class="h-full transition-all duration-500"
                   :class="pbxData.almacenamiento_pbx > 80 ? 'bg-red-500' : (pbxData.almacenamiento_pbx > 60 ? 'bg-amber-400' : 'bg-emerald-500')"
                   :style="`width: ${pbxData.almacenamiento_pbx}%`">
              </div>
            </div>
            <div class="text-[9px] text-slate-400 font-medium text-right mt-0.5 uppercase tracking-widest">
              Uso de Disco Crítico > 80%
            </div>
          </div>
        </div>
      </div>

      <!-- Fila 3: Gráfico de Red (Prioridad) -->
      <div v-if="issabelHostId && comparisonData[issabelHostId]" class="grid grid-cols-1 gap-4 mt-2">
        <div class="bg-white p-4 rounded-md shadow-sm border border-gray-200 transition-all flex flex-col">
          <span class="text-[11px] font-bold text-slate-700 tracking-[0.1em] uppercase flex items-center gap-2 mb-2">
            <i class="fas fa-network-wired text-blue-500 text-sm"></i> TRÁFICO DE RED (IN/OUT)
          </span>
          <div class="flex-1 min-h-[220px]">
            <apexchart type="area" height="220" :options="netTrafficOptions" :series="getIssabelSeries('net')" />
          </div>
          <!-- Zabbix Style Data Table -->
          <div class="mt-0 pt-2 border-t border-gray-100 font-mono text-xs text-gray-600">
            <div class="grid grid-cols-5 gap-2 px-2 pb-1.5 text-[10px] uppercase text-gray-400 font-bold border-b border-gray-50">
              <div class="col-span-1">Métrica</div>
              <div class="text-right">Last</div>
              <div class="text-right">Min</div>
              <div class="text-right">Avg</div>
              <div class="text-right">Max</div>
            </div>
            <div class="grid grid-cols-5 gap-2 px-2 py-1.5 hover:bg-gray-50 items-center">
              <div class="col-span-1 flex items-center gap-2">
                <span class="w-2.5 h-2.5 bg-[#22C55E] inline-block shadow-sm"></span> Tráfico de Entrada (In)
              </div>
              <div class="text-right font-medium">{{ networkStats.in.last }}</div>
              <div class="text-right text-gray-500">{{ networkStats.in.min }}</div>
              <div class="text-right text-gray-500">{{ networkStats.in.avg }}</div>
              <div class="text-right font-bold text-gray-800">{{ networkStats.in.max }}</div>
            </div>
            <div class="grid grid-cols-5 gap-2 px-2 py-1.5 hover:bg-gray-50 items-center">
              <div class="col-span-1 flex items-center gap-2">
                <span class="w-2.5 h-2.5 bg-[#EF4444] inline-block shadow-sm"></span> Tráfico de Salida (Out)
              </div>
              <div class="text-right font-medium">{{ networkStats.out.last }}</div>
              <div class="text-right text-gray-500">{{ networkStats.out.min }}</div>
              <div class="text-right text-gray-500">{{ networkStats.out.avg }}</div>
              <div class="text-right font-bold text-gray-800">{{ networkStats.out.max }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Fila 4: Gráficos de Hardware (CPU y RAM) -->
      <div v-if="issabelHostId && comparisonData[issabelHostId]" class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        <!-- CPU Issabel -->
        <div class="bg-white p-4 rounded-md shadow-sm border border-gray-200 transition-all flex flex-col">
          <span class="text-[11px] font-bold text-slate-700 tracking-[0.1em] uppercase flex items-center gap-2 mb-2">
            <i class="fas fa-microchip text-blue-500 text-sm"></i> CONSUMO DE CPU (%)
          </span>
          <div class="flex-1 min-h-[256px]">
            <apexchart type="area" height="256" :options="{ ...detailAreaOptions, colors: ['#3b82f6'] }" :series="getIssabelSeries('cpu')" />
          </div>
        </div>
        <!-- RAM Issabel -->
        <div class="bg-white p-4 rounded-md shadow-sm border border-gray-200 transition-all flex flex-col">
          <span class="text-[11px] font-bold text-slate-700 tracking-[0.1em] uppercase flex items-center gap-2 mb-2">
            <i class="fas fa-memory text-purple-500 text-sm"></i> CONSUMO DE RAM (%)
          </span>
          <div class="flex-1 min-h-[256px]">
            <apexchart type="area" height="256" :options="{ ...detailAreaOptions, colors: ['#a855f7'] }" :series="getIssabelSeries('ram')" />
          </div>
        </div>
      </div>

    </div>

    <!-- Global Trends (Modo Seguridad) -->
    <div v-if="currentTemplate === 'fortigate'" class="grid grid-cols-1 lg:grid-cols-3 gap-3 shrink-0">
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
    <div v-if="currentTemplate !== 'issabel'" class="bg-white rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative">
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
      </div>

      <div class="w-full">
        <table class="w-full text-left border-collapse">
          <thead class="sticky top-0 bg-white z-[1]">
            <tr class="border-b border-slate-100 shadow-[0_2px_3px_-2px_rgba(0,0,0,0.05)]">
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50 text-center w-16">Estado</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">Servidor</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50">IP</th>
              <th class="py-2.5 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50 text-center">OS</th>
              <template v-if="currentTemplate === 'global'">
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
                class="transition-colors cursor-pointer"
                :class="host.status === 'Offline' ? 'bg-red-50 border-l-4 border-red-500 hover:bg-red-100/50' : 'border-b border-slate-50 hover:bg-blue-50/40'" 
                @click="openDetail(host)">
              <td class="py-2 px-4">
                <div class="flex items-center justify-center">
                  <span class="relative flex h-2.5 w-2.5" :title="statusMeta(host.status).label">
                    <span v-if="host.status === 'Online'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="statusMeta(host.status).dotClass"></span>
                  </span>
                </div>
              </td>
              <td class="py-2 px-4 font-semibold text-[13px] whitespace-nowrap"
                  :class="host.status === 'Offline' ? 'text-red-700' : 'text-slate-700'">
                {{ parseHostname(host.hostname).main }}
                <span v-if="parseHostname(host.hostname).tag" class="ml-1.5 align-middle text-[9px] font-bold text-slate-400 tracking-wider">{{ parseHostname(host.hostname).tag }}</span>
              </td>
              <td class="py-2 px-4">
                <div class="flex items-center gap-2 group">
                  <span class="text-slate-800 font-mono text-[11px] font-bold tracking-tight">{{ host.ip }}</span>
                  <button @click.stop="copyToClipboard(host.ip)" class="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-blue-600 focus:outline-none" title="Copiar IP">
                    <i class="far fa-copy text-[10px]"></i>
                  </button>
                </div>
              </td>
              <td class="py-2 px-4 text-center">
                <div class="flex items-center justify-center" :title="getDetectedOS(host).osName">
                  <!-- Ícono SVGs para OS -->
                  <svg v-if="getDetectedOS(host).osName.includes('Windows')" class="w-4 h-4 text-blue-500" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M0 12.402l35.687-4.86.016 34.423L0 41.965v-29.563zm35.67 33.529l.016 34.453L0 75.485V46.068l35.67-4.137zm4.326-39.011L87.314 0v41.26L39.996 41.95V6.92zm47.318 39.011V87.31l-47.318-6.66.015-34.72 47.303-4.009z"/></svg>
                  <svg v-else-if="getDetectedOS(host).osName.includes('Linux')" class="w-4 h-4 text-slate-500" viewBox="0 0 448 512" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M220.8 123.3c1 .5 1.8 1.7 3 1.7 1.1 0 2.8-.4 2.9-1.5.2-1.4-1.9-2.3-3.2-2.9-1.7-.7-3.9-1-5.5-.1-.4.2-.8.7-.6 1.1.3 1.3 2.3 1.1 3.4 1.7zm-21.9 1.7c1.2 0 2-1.2 3-1.7 1.1-.6 3.1-.4 3.5-1.7.2-.4-.2-.9-.6-1.1-1.6-.9-3.8-.6-5.5.1-1.3.6-3.4 1.5-3.2 2.9.1 1 1.8 1.5 2.8 1.5zM420.2 392.5c-5.1-9.7-16.3-15.4-30.8-19.1-14.9-3.9-29.1-8-36.8-14.8-17.6-15.5-27.1-39.3-35.3-60.6-2.6-6.7-5.1-13.4-7.8-20.1C333.1 230 352 178.6 352 144 352 64.2 293 0 224 0 154.9 0 96 64.2 96 144c0 34.6 18.9 86 42.5 133.9-2.7 6.7-5.2 13.4-7.8 20.1-8.3 21.3-17.7 45.1-35.3 60.6-7.8 6.8-21.9 10.9-36.8 14.8-14.5 3.7-25.7 9.4-30.8 19.1C8.7 428.8 28.5 487.6 28.5 487.6c1 2.3 3.3 3.8 5.8 4.1l2.4.2c.4 0 1 .1 1.4.1 48 4 96.5 15.6 144.1 19.8 11.2 1 22.3 1.7 33.5 1.7s22.3-.7 33.5-1.7c47.7-4.2 96.1-15.8 144.1-19.8.5 0 1-.1 1.4-.1l2.4-.2c2.5-.3 4.8-1.9 5.8-4.1 0 0 19.8-58.8.8-95.1zM224 496c-27 0-54.6-2-83.3-4.6l-50.6-3.8c-24.1-1.6-47-2.6-70-3.3 5.4-9.9 16.4-18.7 32-23.3 12.3-3.6 28-7.3 36.1-12 18-10.4 28.6-33.1 36.9-57 5.1-14.7 9.8-29.3 14.7-43.2.1 0 .2-.1.3-.1 1.7-4.9 3.5-9.8 5.3-14.7 13.2-36.7 26.2-72.9 26.2-120.2V112.5c0-1.8.2-3.4.6-5 .6 0 1.2.1 1.8.1h30.2c.6 0 1.2-.1 1.8-.1.4 1.6.6 3.2.6 5v121.2c0 47.3 13 83.5 26.2 120.2 1.8 4.9 3.6 9.8 5.3 14.7.1 0 .2.1.3.1 4.9 13.9 9.6 28.5 14.7 43.2 8.3 23.9 18.9 46.5 36.9 57 8.1 4.7 23.8 8.4 36.1 12 15.6 4.6 26.6 13.3 32 23.3-23 1-45.9 2-70 3.3l-50.6 3.8C278.6 494 251 496 224 496z" /></svg>
                  <svg v-else-if="getDetectedOS(host).osName.includes('FortiOS')" class="w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  <svg v-else class="w-4 h-4 text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2"/></svg>
                </div>
              </td>
              <template v-if="currentTemplate === 'global'">
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
                      <apexchart type="area" width="100" height="30" :options="sparklineRamOptions(host.ram)" :series="[{ data: host.ram_history }]" />
                    </div>
                  </div>
                </td>
                <td class="py-1.5 px-4">
                  <!-- Error Badge (Offline/Warning) -->
                  <div v-if="host.status === 'Offline' && host.last_problem" 
                       class="bg-red-50 text-red-700 border-red-200 flex items-center px-2 py-1 rounded text-[10px] font-medium border max-w-[200px]"
                       :title="host.last_problem">
                    <span class="truncate w-full block">{{ host.last_problem }}</span>
                  </div>
                  <!-- Proactive CPU Critical -->
                  <div v-else-if="host.cpu >= 90" class="flex items-center gap-2 text-red-500">
                    <i class="fas fa-fire text-sm animate-pulse"></i>
                    <div class="flex flex-col leading-tight">
                      <span class="text-[11px] font-black uppercase tracking-wider">CPU Crítica</span>
                      <span class="text-[9px] font-bold text-slate-400">Pico de {{ formatPct(host.cpu) }}</span>
                    </div>
                  </div>
                  <!-- Proactive RAM Critical -->
                  <div v-else-if="host.ram >= 90" class="flex items-center gap-2 text-red-500">
                    <i class="fas fa-memory text-sm animate-pulse"></i>
                    <div class="flex flex-col leading-tight">
                      <span class="text-[11px] font-black uppercase tracking-wider">RAM Crítica</span>
                      <span class="text-[9px] font-bold text-slate-400">Consumo {{ formatPct(host.ram) }}</span>
                    </div>
                  </div>
                  <!-- Proactive CPU Alta -->
                  <div v-else-if="host.cpu >= 80" class="flex items-center gap-2 text-orange-500">
                    <i class="fas fa-microchip text-sm"></i>
                    <div class="flex flex-col leading-tight">
                      <span class="text-[11px] font-bold uppercase tracking-wider">CPU Elevada</span>
                      <span class="text-[9px] font-semibold text-slate-400">Uso al {{ formatPct(host.cpu) }}</span>
                    </div>
                  </div>
                  <!-- Proactive RAM Alta -->
                  <div v-else-if="host.ram >= 85" class="flex items-center gap-2 text-orange-500">
                    <i class="fas fa-memory text-sm"></i>
                    <div class="flex flex-col leading-tight">
                      <span class="text-[11px] font-bold uppercase tracking-wider">RAM Elevada</span>
                      <span class="text-[9px] font-semibold text-slate-400">Uso al {{ formatPct(host.ram) }}</span>
                    </div>
                  </div>
                  <!-- Proactive Red Saturada (> 100 Mbps) -->
                  <div v-else-if="host.net_in >= 100000000 || host.net_out >= 100000000" class="flex items-center gap-2 text-amber-500">
                    <i class="fas fa-network-wired text-sm animate-pulse"></i>
                    <div class="flex flex-col leading-tight">
                      <span class="text-[11px] font-black uppercase tracking-wider">Red Saturada</span>
                      <span class="text-[9px] font-bold text-slate-400">Tráfico > 100 Mbps</span>
                    </div>
                  </div>
                  <!-- Normal Network Graph (Active/Online) -->
                  <div v-else class="flex items-center gap-2">
                    <div v-if="(host.net_in === 0 && host.net_out === 0) || host.status === 'Offline'" class="flex flex-col text-slate-400 text-[11px] font-semibold w-24 shrink-0">
                      <span>↓ 0 Kbps</span>
                      <span>↑ 0 Kbps</span>
                    </div>
                    <div v-else class="flex flex-col text-[11px] font-semibold w-24 shrink-0 gap-0.5">
                      <span class="text-slate-700"><span class="text-emerald-700">↓</span> {{ formatNetworkTraffic(host.net_in) }}</span>
                      <span class="text-slate-700"><span class="text-blue-700">↑</span> {{ formatNetworkTraffic(host.net_out) }}</span>
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
          <div v-if="Object.keys(comparisonData).length > 0" class="flex flex-col gap-4">
            
            <!-- KPIs Header Row -->
            <div v-if="overviewKpis" class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div class="bg-white p-3 rounded-lg shadow-sm border border-slate-100 flex flex-col justify-center">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Uptime</span>
                <span class="text-xl font-bold text-slate-800">{{ overviewKpis.uptime }}</span>
              </div>
              <div class="bg-white p-3 rounded-lg shadow-sm border border-slate-100 flex flex-col justify-center">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Carga de CPU</span>
                <span class="text-xl font-bold text-blue-600">{{ overviewKpis.cpuLoad }}</span>
              </div>
              <div class="bg-white p-3 rounded-lg shadow-sm border border-slate-100 flex flex-col justify-center">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Memoria Disp.</span>
                <span class="text-xl font-bold text-blue-600">{{ overviewKpis.availableMem }}</span>
              </div>
              <div class="bg-white p-3 rounded-lg shadow-sm border border-slate-100 flex flex-col justify-center">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Tráfico Total</span>
                <span class="text-xl font-bold text-blue-600">{{ overviewKpis.totalTraffic }}</span>
              </div>
            </div>

            <!-- Main Charts Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- CPU Detail Chart -->
              <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
                <div class="flex justify-between items-center mb-2 pr-6">
                  <span class="text-[11px] font-bold text-slate-500 tracking-widest">CPU (%)</span>
                  <span class="text-[10px] text-slate-400 font-medium">{{ selectedRangeLabel }}</span>
                </div>
                <button @click="expandChart('cpu')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                  <i class="fas fa-expand text-[10px]"></i>
                </button>
                <apexchart type="area" height="150" :options="detailAreaOptions" :series="cpuSeries" />
              </div>

              <!-- RAM Detail Chart -->
              <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
                <div class="flex justify-between items-center mb-2 pr-6">
                  <span class="text-[11px] font-bold text-slate-500 tracking-widest">RAM (%)</span>
                  <span class="text-[10px] text-slate-400 font-medium">{{ selectedRangeLabel }}</span>
                </div>
                <button @click="expandChart('ram')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                  <i class="fas fa-expand text-[10px]"></i>
                </button>
                <apexchart type="area" height="150" :options="detailAreaOptions" :series="ramSeries" />
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
                  <i class="fas fa-expand text-[10px]"></i>
                </button>
                <div class="flex-1 min-h-0">
                  <apexchart type="area" height="150" :options="netTrafficOptions" :series="netSeries" />
                </div>
              </div>

              <!-- Disk Latency -->
              <div v-show="!isFortiGateSelected" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
                <div class="flex justify-between items-center mb-2 pr-6">
                  <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">DISK QUEUE LENGTH LATENCY</span>
                </div>
                <button @click="expandChart('latency')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                  <i class="fas fa-expand text-[10px]"></i>
                </button>
                <apexchart type="line" height="150" :options="latencyOptions" :series="latencySeries" />
              </div>

              <!-- Ping Latency -->
              <div v-show="!isFortiGateSelected" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 relative group">
                <div class="flex justify-between items-center mb-2 pr-6">
                  <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">PING LATENCY (ms)</span>
                </div>
                <button @click="expandChart('ping')" class="absolute top-3 right-3 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 bg-slate-50 hover:bg-blue-50 rounded" title="Ampliar Gráfica">
                  <i class="fas fa-expand text-[10px]"></i>
                </button>
                <apexchart type="line" height="150" :options="pingOptions" :series="pingSeries" />
              </div>

              <!-- Top Processes (Movido para llenar espacio) -->
              <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 flex flex-col">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">TOP PROCESOS</span>
                <div class="overflow-y-auto h-[160px] pr-1 custom-scrollbar">
                  <table class="w-full text-left border-collapse">
                    <thead>
                      <tr class="border-b border-slate-100">
                        <th class="py-2 text-[10px] font-bold text-slate-400">NOMBRE</th>
                        <th class="py-2 text-[10px] font-bold text-slate-400">PID</th>
                        <th class="py-2 text-[10px] font-bold text-slate-400">CPU</th>
                        <th class="py-2 text-[10px] font-bold text-slate-400">RAM</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="proc in topProcesses" :key="proc.pid" class="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors">
                        <td class="py-1.5 text-[11px] font-semibold text-slate-700">{{ proc.name }}</td>
                        <td class="py-1.5 text-[10px] text-slate-400 font-mono">{{ proc.pid }}</td>
                        <td class="py-1.5 text-[11px] font-bold text-blue-600">{{ proc.cpu }}</td>
                        <td class="py-1.5 text-[11px] font-bold text-slate-600">{{ proc.ram }}</td>
                      </tr>
                      <tr v-if="!topProcesses.length">
                        <td colspan="4" class="py-4 text-center text-xs text-slate-400 italic">No hay procesos disponibles</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Bottom Widgets Row: Disk Progress, Alerts -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2">
              
              <!-- Disk Usage (Linear Progress) -->
              <div v-show="!isFortiGateSelected" class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 flex flex-col">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-4">ALMACENAMIENTO (DISKS)</span>
                <div class="flex flex-col gap-4 overflow-y-auto h-[160px] pr-2 custom-scrollbar flex-1">
                  <div v-for="h in selectedHosts" :key="h.hostid">
                    <div v-if="comparisonData[h.hostid]?.disks?.length" class="flex flex-col gap-1.5">
                      <div class="flex justify-between items-end">
                        <span class="text-xs font-semibold text-slate-700 truncate w-32" :title="h.hostname">{{ h.hostname }}</span>
                        <span class="text-xs font-bold text-slate-500">{{ comparisonData[h.hostid].disks[0].value }}% Usado</span>
                      </div>
                      <div class="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all duration-500"
                             :class="comparisonData[h.hostid].disks[0].value > 85 ? 'bg-red-500' : comparisonData[h.hostid].disks[0].value > 70 ? 'bg-amber-400' : 'bg-blue-600'"
                             :style="`width: ${comparisonData[h.hostid].disks[0].value}%`">
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>



              <!-- Active Alerts (Triggers) -->
              <div class="bg-white p-4 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] border border-slate-200 flex flex-col">
                <span class="text-[11px] font-bold text-slate-500 tracking-widest block mb-2">ALERTAS ACTIVAS</span>
                <div class="flex flex-col gap-2 overflow-y-auto h-[160px] pr-2 custom-scrollbar flex-1">
                  <div v-for="prob in activeTriggers" :key="prob.eventid" 
                       class="flex gap-2 items-start p-2 border border-slate-100 rounded-lg bg-slate-50">
                    <div class="mt-0.5 shrink-0">
                      <i v-if="prob.severity === '5'" class="fas fa-exclamation-circle text-red-500 text-sm"></i>
                      <i v-else class="fas fa-exclamation-triangle text-amber-500 text-sm"></i>
                    </div>
                    <div class="flex flex-col min-w-0">
                      <span class="text-[11px] font-semibold text-slate-700 leading-tight truncate" :title="prob.name">{{ prob.name }}</span>
                      <span class="text-[9px] font-bold text-slate-400 mt-1">{{ formatTime(prob.clock) }}</span>
                    </div>
                  </div>
                  <div v-if="!activeTriggers.length" class="flex flex-col items-center justify-center h-full text-slate-400">
                    <i class="fas fa-check-circle text-green-400 text-xl mb-1"></i>
                    <span class="text-[11px] font-medium">Sistemas estables</span>
                  </div>
                </div>
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
          <div class="flex items-center gap-4">
            <select :value="selectedModalRange" @change="updateModalRange(Number($event.target.value))" class="appearance-none bg-white border border-slate-200 text-slate-700 text-xs font-bold rounded-lg pl-3 pr-8 py-1.5 hover:bg-slate-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm">
              <option v-for="tr in timeRanges" :key="tr.value" :value="tr.value">{{ tr.label }}</option>
            </select>
            <button @click="expandedChart = null" class="text-slate-400 hover:text-red-500 hover:bg-red-50 p-2 rounded-full transition-colors flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
        <div class="flex-1 p-6 min-h-0 bg-white">
          <apexchart type="line" width="100%" height="100%" :options="expandedOptions" :series="expandedSeries" />
        </div>
        <div v-if="expandedStats" class="px-6 py-3 bg-slate-50 border-t border-slate-200 grid grid-cols-4 gap-4 text-center rounded-b-2xl">
          <div>
            <div class="text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-0.5">Último Valor</div>
            <div class="text-sm font-bold text-blue-600">{{ expandedStats.last }}</div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-0.5">Promedio</div>
            <div class="text-sm font-bold text-slate-700">{{ expandedStats.avg }}</div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-0.5">Máximo</div>
            <div class="text-sm font-bold text-red-500">{{ expandedStats.max }}</div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 font-bold tracking-wider uppercase mb-0.5">Mínimo</div>
            <div class="text-sm font-bold text-emerald-500">{{ expandedStats.min }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import zabbixService from '../services/zabbix.service';

const pbxData = ref({
  loading: false,
  asterisk_down: false,
  server_down: false,
  llamadas_activas: 0,
  robot_ivr: -1,
  ruta_opcion1: -1,
  ruta_opcion2: -1,
  troncal_101: -1,
  extensiones_registradas: '112 / 120', // Mock data
  almacenamiento_pbx: 45, // Mock data (%)
  ivr_options: {}
});

// Helper functions para el diseño NOC de opciones
const ivrOptionNames = {
  1: 'Ventas',
  2: 'Soporte',
  3: 'Cartera'
};

const getOptionName = (i, dynamicName) => {
  if (dynamicName && dynamicName !== `Opción ${i}`) return dynamicName;
  return ivrOptionNames[i] || `Opción ${i}`;
};

const getOptionClass = (val) => {
  if (pbxData.value.server_down) return 'bg-white border-slate-100 opacity-60';
  if (pbxData.value.asterisk_down) return 'bg-white border-red-100 opacity-60';
  if (val === 1) return 'bg-emerald-50/30 border-emerald-200';
  if (val === 0) return 'bg-red-50/30 border-red-200';
  return 'bg-white border-slate-100 shadow-sm opacity-80';
};

const getOptionLabelClass = (val) => {
  if (pbxData.value.server_down) return 'text-slate-400';
  if (pbxData.value.asterisk_down) return 'text-red-300';
  if (val === 1) return 'text-slate-600';
  if (val === 0) return 'text-slate-600';
  return 'text-slate-400';
};

const getOptionIconClass = (val) => {
  if (pbxData.value.server_down || pbxData.value.asterisk_down) return 'fas fa-minus-circle text-slate-300';
  if (val === 1) return 'far fa-check-circle text-emerald-500';
  if (val === 0) return 'fas fa-exclamation-triangle text-red-500';
  return 'fas fa-minus-circle text-slate-300';
};

const getOptionTextClass = (val) => {
  if (pbxData.value.server_down) return 'text-slate-400';
  if (pbxData.value.asterisk_down) return 'text-red-400 line-through';
  if (val === 1) return 'text-emerald-700';
  if (val === 0) return 'text-red-700';
  return 'text-slate-400';
};

const fetchPbxStats = async () => {
  pbxData.value.loading = true;
  try {
    const res = await zabbixService.getPbxTelephony();
    if (res.status === 'success') {
      const wasDown = pbxData.value.asterisk_down;
      pbxData.value = {
        loading: false,
        asterisk_down: res.data.asterisk_down,
        server_down: res.data.server_down,
        llamadas_activas: res.data.llamadas_activas,
        robot_ivr: res.data.robot_ivr,
        ruta_opcion1: res.data.ruta_opcion1,
        ruta_opcion2: res.data.ruta_opcion2,
        troncal_101: res.data.troncal_101,
        ivr_options: res.data.ivr_options || {}
      };
      
      if (res.data.asterisk_down && !wasDown) {
        playAlertSound();
      }
    } else {
      console.error(res.message);
      pbxData.value.loading = false;
    }
  } catch (e) {
    console.error("Error fetching PBX stats", e);
    pbxData.value.loading = false;
  }
};
// -----------------------

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
const detailTimeRange = ref('1h');
const comparisonData = ref({});
const loadingDetail = ref(false);

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Error al copiar: ', err);
  }
};

const expandedChart = ref(null);
const expandedLogs = ref(new Set());

const toggleLog = (eventId) => {
  const newSet = new Set(expandedLogs.value);
  if (newSet.has(eventId)) newSet.delete(eventId);
  else newSet.add(eventId);
  expandedLogs.value = newSet;
};

const selectedModalRange = ref(3600);

const expandChart = (type) => {
  expandedChart.value = type;
  selectedModalRange.value = selectedRange.value;
};

const updateModalRange = async (seconds) => {
  if (selectedModalRange.value === seconds) return;
  selectedModalRange.value = seconds;
  loadingDetail.value = true;
  await Promise.all(selectedHosts.value.map(h => fetchDetailForHost(h, selectedModalRange.value)));
  loadingDetail.value = false;
};

const expandedTitle = computed(() => {
  let base = '';
  if (expandedChart.value === 'cpu') base = 'Histórico Detallado: CPU (%)';
  if (expandedChart.value === 'ram') base = 'Histórico Detallado: RAM Usada (%)';
  if (expandedChart.value === 'net') base = 'Histórico Detallado: Tráfico de Red (Kbps/Mbps)';
  if (expandedChart.value === 'latency') base = 'Histórico Detallado: Latencia de Disco (Queue Length)';
  if (expandedChart.value === 'ping') base = 'Histórico Detallado: Latencia de Red Ping (ms)';
  if (expandedChart.value === 'sessions') base = 'Histórico Detallado: Firewall Sessions';
  const r = timeRanges.find(tr => tr.value === selectedModalRange.value);
  const rLabel = r ? r.label : '1 Hora';
  return base ? `${base} (Últimas ${rLabel})` : '';
});

const expandedSeries = computed(() => {
  if (expandedChart.value === 'cpu') return cpuSeries.value;
  if (expandedChart.value === 'ram') return ramSeries.value;
  if (expandedChart.value === 'net') return netSeries.value;
  if (expandedChart.value === 'latency') return latencySeries.value;
  if (expandedChart.value === 'ping') return pingSeries.value;
  if (expandedChart.value === 'sessions') return sessionSeries.value;
  return [];
});

const expandedStats = computed(() => {
  if (!expandedSeries.value || expandedSeries.value.length === 0) return null;
  // Combine all series for accurate min/max if there are multiple lines, or just take the first
  const allValues = [];
  expandedSeries.value.forEach(s => {
    if (s.data) s.data.forEach(p => { if (p[1] != null && !isNaN(p[1])) allValues.push(p[1]); });
  });
  if (allValues.length === 0) return null;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const avg = allValues.reduce((a,b) => a+b, 0) / allValues.length;
  // Get last value of the primary series
  const series = expandedSeries.value[0];
  const last = (series.data && series.data.length > 0) ? series.data[series.data.length - 1][1] : 0;

  let formatFn = (v) => v.toFixed(2);
  if (expandedChart.value === 'net') formatFn = formatNetAxisLabel;
  else if (expandedChart.value === 'ping') formatFn = (v) => v.toFixed(1) + ' ms';
  else if (expandedChart.value === 'cpu' || expandedChart.value === 'ram') formatFn = (v) => v.toFixed(1) + '%';
  else if (expandedChart.value === 'sessions') formatFn = (v) => Math.round(v).toLocaleString();

  return { min: formatFn(min), max: formatFn(max), avg: formatFn(avg), last: formatFn(last) };
});

const expandedOptions = computed(() => {
  let baseObj = {};
  if (expandedChart.value === 'cpu' || expandedChart.value === 'ram') baseObj = detailAreaOptions.value;
  else if (expandedChart.value === 'net') baseObj = netTrafficOptions.value;
  else if (expandedChart.value === 'latency') baseObj = latencyOptions.value;
  else if (expandedChart.value === 'ping') baseObj = pingOptions.value;
  else if (expandedChart.value === 'sessions') baseObj = { ...sessionOptions, chart: { ...sessionOptions.chart, sparkline: { enabled: false } }, stroke: { width: 2 }, xaxis: { type: 'datetime', labels: { style: { fontSize: '9px', colors: '#94a3b8' } } }, grid: { borderColor: '#f1f5f9' }, yaxis: { labels: { style: { fontSize: '9px', colors: '#94a3b8' } } } };

  // Modificar base clone para resolución más alta
  return {
    ...baseObj,
    chart: { ...baseObj.chart, toolbar: { show: true }, zoom: { enabled: true } },
    legend: { ...baseObj.legend, fontSize: '13px' },
    xaxis: { ...baseObj.xaxis, labels: { ...baseObj.xaxis?.labels, style: { fontSize: '11px', colors: '#64748b' } } },
    yaxis: { ...baseObj.yaxis, labels: { ...baseObj.yaxis?.labels, style: { fontSize: '11px', colors: '#64748b' }, formatter: baseObj.yaxis?.labels?.formatter } },
    grid: { show: true, borderColor: '#e2e8f0', strokeDashArray: 4, position: 'back', xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } }, padding: { left: 10, right: 10 } },
    tooltip: { 
      theme: 'dark',
      shared: false,
      intersect: true,
      fixed: { enabled: true, position: 'topRight', offsetX: -20, offsetY: 20 },
      custom: function({series, seriesIndex, dataPointIndex, w}) {
        let hoverTs = w.globals.seriesX?.[seriesIndex]?.[dataPointIndex];
        if (!hoverTs) return '';
        let d = new Date(hoverTs);
        let title = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
        
        let name = w.globals.seriesNames[seriesIndex];
        let val = series[seriesIndex][dataPointIndex];
        if (val == null) return '';
        let color = w.globals.colors[seriesIndex];
        let formatter = baseObj.yaxis?.labels?.formatter || (v => v);
        let formattedVal = formatter(val);
        
        let row = `<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;margin-top:6px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                      <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block;"></span>
                      <span style="color:#cbd5e1;font-size:11px;">${name}</span>
                    </div>
                    <span style="color:#fff;font-weight:bold;font-size:12px;">${formattedVal}</span>
                  </div>`;
        
        return `<div style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.3);min-width:140px;font-family:inherit;">
                  <div style="color:#94a3b8;font-size:11px;font-weight:bold;border-bottom:1px solid #334155;padding-bottom:4px;margin-bottom:4px;">${title}</div>
                  ${row}
                </div>`;
      }
    }
  };
});

let globalTimer = null;
let detailTimer = null;

const currentTemplate = ref('global'); // 'global', 'fortigate', 'issabel'
const issabelHostId = ref(null);
const loadingIssabelDetail = ref(false);

const getIssabelSeries = (type) => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  if (type === 'cpu') return [{ name: 'CPU (%)', data: comp.cpu?.history || [] }];
  if (type === 'ram') return [{ name: 'RAM (%)', data: comp.ram?.history || [] }];
  if (type === 'net') {
    const ifaceNames = Object.keys(comp.interfaces || {});
    if (ifaceNames.length > 0) {
      // Find the main interface, prefer eth*, ens*, eno*, lan*
      let bestIface = ifaceNames[0];
      for (const name of ifaceNames) {
        const lower = name.toLowerCase();
        if (lower.startsWith('eth') || lower.startsWith('ens') || lower.startsWith('eno') || lower.startsWith('lan')) {
          bestIface = name;
          break;
        }
      }
      return [
        { name: 'Tráfico de Entrada (In)', type: 'area', data: mapTraffic(comp.interfaces[bestIface].in?.history, true) },
        { name: 'Tráfico de Salida (Out)', type: 'line', data: mapTraffic(comp.interfaces[bestIface].out?.history, false) }
      ];
    }
    return [];
  }
  return [];
};

watch(currentTemplate, async (newVal) => {
  if (newVal === 'issabel') {
    // Buscar hostid de Issabel
    const h = hosts.value.find(h => h.hostname.toLowerCase().includes('issabel') || h.hostname.toLowerCase().includes('pbx'));
    if (h) {
      issabelHostId.value = h.hostid;
      if (!comparisonData.value[h.hostid]) {
        loadingIssabelDetail.value = true;
        // Inyectar en hosts temporalmente si no estaba en selectedHosts
        if (!selectedHosts.value.find(sh => sh.hostid === h.hostid)) {
           // Si se necesita para fetchDetailForHost
        }
        await fetchDetailForHost(h);
        loadingIssabelDetail.value = false;
      }
    }
  }
});

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
const selectedRangeLabel = computed(() => {
  const r = timeRanges.find(tr => tr.value === selectedRange.value);
  return r ? r.label : '1 Hora';
});

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

const sanitizeHistory = (data, isPercentage = true) => {
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
    
  // NOTA: Se eliminó la inyección de ceros en huecos grandes.
  // Zabbix nativo interpola (dibuja la diagonal) entre puntos lejanos,
  // y el usuario prefiere esa estética a ver picos (spikes) que caen a cero.
  return cleanData;
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
let globalAudioCtx = null;

const playAlertSound = () => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    
    // Usar singleton para no exceder límite de contextos del navegador
    if (!globalAudioCtx) {
      globalAudioCtx = new AudioContext();
    }
    
    // Si fue suspendido por política del navegador, reanudar
    if (globalAudioCtx.state === 'suspended') {
      globalAudioCtx.resume();
    }
    
    const duration = 10;
    const oscillator = globalAudioCtx.createOscillator();
    const gainNode = globalAudioCtx.createGain();
    
    oscillator.type = 'square';
    oscillator.connect(gainNode);
    gainNode.connect(globalAudioCtx.destination);
    
    for (let i = 0; i < duration * 2; i++) {
       const time = globalAudioCtx.currentTime + i * 0.5;
       gainNode.gain.setValueAtTime(0.05, time);
       gainNode.gain.setValueAtTime(0, time + 0.25);
       oscillator.frequency.setValueAtTime(i % 2 === 0 ? 800 : 1000, time);
    }
    
    oscillator.start(globalAudioCtx.currentTime);
    oscillator.stop(globalAudioCtx.currentTime + duration);
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
          cpu_history: downsample(cpuHistory),
          ram_history: downsample(ramHistory),
          net_in_history: downsample(netInHistory),
          net_out_history: downsample(netOutHistory)
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
  
  const promises = [fetchTrends(time_from, time_till), fetchHosts(time_from, time_till), fetchPbxStats()];
  
  // Si estamos en la pestaña de Issabel, asegurar que las gráficas de hardware se refresquen en segundo plano
  if (currentTemplate.value === 'issabel' && issabelHostId.value) {
    const pbxHost = hosts.value.find(h => h.hostid === issabelHostId.value);
    if (pbxHost) promises.push(fetchDetailForHost(pbxHost));
  }
  
  if (showDetail.value) {
    promises.push(fetchAllDetails(true));
  }
  
  await Promise.all(promises);
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
  detailTimer = setInterval(() => fetchAllDetails(true), 60000);
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

const fetchAllDetails = async (silent = false) => {
  const rangeToUse = expandedChart.value ? selectedModalRange.value : selectedRange.value;
  await Promise.all(selectedHosts.value.map(h => fetchDetailForHost(h, rangeToUse, silent)));
};

const fetchDetailForHost = async (host, customRange = null, silent = false) => {
  const rangeToUse = customRange || selectedRange.value;
  if (!silent) loadingDetail.value = true;
  try {
    const res = await zabbixService.getHostDetail(host.hostid, rangeToUse);
    if (res.status === 'success') {
      const data = res.data;
      
      // Si es un refresh silencioso con el modal abierto: solo actualizar valores
      // actuales sin reemplazar el historial completo (preserva zoom y cursor)
      if (silent && expandedChart.value && comparisonData.value[host.hostid]) {
        const existing = comparisonData.value[host.hostid];
        // Parchear valores actuales sin tocar el historial
        if (data.cpu?.value != null) existing.cpu.value = data.cpu.value;
        if (data.ram?.value != null) existing.ram.value = data.ram.value;
        if (data.latency?.value != null && existing.latency) existing.latency.value = data.latency.value;
        if (data.ping?.value != null && existing.ping) existing.ping.value = data.ping.value;
        if (data.sessions?.value != null && existing.sessions) existing.sessions.value = data.sessions.value;
        // No cambiamos comparisonData.value para no disparar re-render de gráficas
        loadingDetail.value = false;
        return;
      }
      
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
      
      if (!data.cpu.history.length) data.cpu.history = [];
      if (!data.ram.history.length) data.ram.history = [];

      if (data.sessions) {
        data.sessions.history = clipHistory(sanitizeHistory(data.sessions.history, false));
      }

      if (data.interfaces) {
        Object.keys(data.interfaces).forEach(iface => {
          data.interfaces[iface].in.history = clipHistory(sanitizeHistory(data.interfaces[iface].in.history, false));
          data.interfaces[iface].out.history = clipHistory(sanitizeHistory(data.interfaces[iface].out.history, false));
          if (!data.interfaces[iface].in.history.length) data.interfaces[iface].in.history = [];
          if (!data.interfaces[iface].out.history.length) data.interfaces[iface].out.history = [];
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
  if (status === 'Offline') return { label: 'Critical', dotClass: 'bg-red-500 animate-pulse', textClass: 'text-red-700' };
  return { label: 'Warning', dotClass: 'bg-amber-500', textClass: 'text-amber-700' };
};

const formatTime = (clock) => {
  const d = new Date(clock * 1000);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const mapTraffic = (history, isInbound) => {
  if (!history || !Array.isArray(history)) return [];
  return history.map(([t, v]) => {
    // Zabbix devuelve Bytes/sec. Convertimos a bits/sec para mostrar en Kbps como Zabbix nativo.
    let kbps = (v * 8) / 1000;
    return [t, parseFloat(kbps.toFixed(4))];
  });
};

const formatTrafficVal = (valKbps) => {
  if (valKbps == null || isNaN(valKbps)) return '--';
  return valKbps > 1000 ? (valKbps / 1000).toFixed(2) + ' Mbps' : valKbps.toFixed(2) + ' Kbps';
};

const networkStats = computed(() => {
  const defaultStats = { last: '--', min: '--', avg: '--', max: '--' };
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) {
    return { in: { ...defaultStats }, out: { ...defaultStats } };
  }
  
  const comp = comparisonData.value[issabelHostId.value];
  const ifaceNames = Object.keys(comp.interfaces || {});
  if (ifaceNames.length === 0) {
    return { in: { ...defaultStats }, out: { ...defaultStats } };
  }
  
  let bestIface = ifaceNames[0];
  for (const name of ifaceNames) {
    const lower = name.toLowerCase();
    if (lower.startsWith('eth') || lower.startsWith('ens') || lower.startsWith('eno') || lower.startsWith('lan')) {
      bestIface = name;
      break;
    }
  }
  
  const calcStats = (history) => {
    if (!history || history.length === 0) return { ...defaultStats };
    // Zabbix API = Bytes/sec -> * 8 para bits -> / 1000 para Kbps
    const values = history.map(p => Math.abs((p[1] * 8) / 1000));
    const last = values[values.length - 1];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    
    return {
      last: formatTrafficVal(last),
      min: formatTrafficVal(min),
      avg: formatTrafficVal(avg),
      max: formatTrafficVal(max)
    };
  };

  return {
    in: calcStats(comp.interfaces[bestIface].in?.history),
    out: calcStats(comp.interfaces[bestIface].out?.history)
  };
});


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
      opacityFrom: 0.2,
      opacityTo: 0.05,
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
    labels: { datetimeUTC: false, datetimeFormatter: { hour: 'HH:mm', minute: 'HH:mm' }, style: { fontSize: '9px', colors: '#64748b' } },
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
      style: { fontSize: '9px', colors: '#64748b' },
      formatter: (val) => String(Math.round(val))
    }
  },
  legend: { 
    position: 'bottom', 
    fontSize: '10px', 
    fontWeight: 600, 
    markers: { width: 6, height: 6, radius: 12 }, 
    itemMargin: { horizontal: 6 } 
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
    padding: { left: 8, right: 8, top: 4, bottom: 0 }
  }
});

const sparklineRamOptions = (val) => {
  let color = '#10b981'; // Verde sólido
  if (val >= 85) color = '#ef4444'; // Rojo sólido
  else if (val >= 75) color = '#f59e0b'; // Naranja sólido

  return {
    colors: [color],
    chart: {
      type: 'area',
      sparkline: { enabled: true },
      animations: { enabled: false },
      toolbar: { show: false },
      parentHeightOffset: 0
    },
    stroke: { curve: 'smooth', width: 1.5, colors: [color] }, // Trazo forzosamente del mismo color
    fill: {
      type: 'gradient',
      gradient: {
        type: 'vertical',
        shadeIntensity: 1,
        opacityFrom: 0.85,
        opacityTo: 0.15,
        colorStops: [
          { offset: 0, color: '#ef4444', opacity: 0.85 },    // Rojo (100%)
          { offset: 40, color: '#f59e0b', opacity: 0.6 },     // Naranja (~60%)
          { offset: 100, color: '#10b981', opacity: 0.25 }    // Verde (0%)
        ]
      }
    },
    yaxis: { min: 0, max: 100 },
    tooltip: { enabled: false }
  };
};

const sparklineOptions = (lineColor) => ({
  colors: ['#3b82f6', '#10b981'],
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

// --- New KPIs Overview & Widgets Computed ---
const primaryHost = computed(() => selectedHosts.value[0]);
const primaryHostData = computed(() => primaryHost.value ? comparisonData.value[primaryHost.value.hostid] : null);

const overviewKpis = computed(() => {
  if (!primaryHost.value || !primaryHostData.value) return null;
  
  const d = primaryHostData.value;
  
  // Uptime formatting
  let uptimeStr = "N/A";
  if (d.uptime) {
    const days = Math.floor(d.uptime / 86400);
    const hours = Math.floor((d.uptime % 86400) / 3600);
    uptimeStr = `${days}d ${hours}h`;
  }

  // Traffic sum
  let totalTraffic = 0;
  if (d.interfaces) {
    for (const iface of Object.values(d.interfaces)) {
      totalTraffic += (iface.in?.value || 0) + (iface.out?.value || 0);
    }
  }
  const trafficStr = totalTraffic > 1000 ? (totalTraffic/1000).toFixed(1) + ' Mbps' : totalTraffic.toFixed(0) + ' Kbps';

  return {
    uptime: uptimeStr,
    cpuLoad: (d.cpu?.value || 0).toFixed(1) + '%',
    availableMem: (100 - (d.ram?.value || 0)).toFixed(1) + '%',
    totalTraffic: trafficStr
  };
});

const topProcesses = computed(() => {
  if (!primaryHost.value) return [];
  const name = primaryHost.value.hostname.toLowerCase();
  
  if (name.includes('win')) {
    return [
      { name: 'sqlservr.exe', cpu: '14.2%', ram: '2.1 GB', pid: 4812 },
      { name: 'w3wp.exe', cpu: '8.5%', ram: '850 MB', pid: 9244 },
      { name: 'svchost.exe', cpu: '4.1%', ram: '320 MB', pid: 1024 },
      { name: 'java.exe', cpu: '2.8%', ram: '1.2 GB', pid: 5611 }
    ];
  } else if (name.includes('issabel') || name.includes('pbx')) {
    return [
      { name: 'asterisk', cpu: '18.4%', ram: '450 MB', pid: 3120 },
      { name: 'mysqld', cpu: '5.2%', ram: '800 MB', pid: 1422 },
      { name: 'httpd', cpu: '2.1%', ram: '150 MB', pid: 2110 },
      { name: 'fail2ban-server', cpu: '1.5%', ram: '90 MB', pid: 855 }
    ];
  } else {
    return [
      { name: 'dockerd', cpu: '12.0%', ram: '1.1 GB', pid: 992 },
      { name: 'kubelet', cpu: '6.5%', ram: '600 MB', pid: 1023 },
      { name: 'nginx', cpu: '3.2%', ram: '120 MB', pid: 442 },
      { name: 'sshd', cpu: '0.5%', ram: '25 MB', pid: 881 }
    ];
  }
});

const activeTriggers = computed(() => {
  if (!primaryHostData.value || !primaryHostData.value.recent_problems) return [];
  return primaryHostData.value.recent_problems.slice(0, 4);
});

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
      series.push({ name: `${h.hostname} (In)`, type: 'area', data: mapTraffic(d.interfaces[iface].in.history, true) });
      series.push({ name: `${h.hostname} (Out)`, type: 'line', data: mapTraffic(d.interfaces[iface].out.history, false) });
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
    let match = true;
    
    const nameStr = (h.hostname || h.name || '').toLowerCase();
    const isFirewall = nameStr.includes('forti') || nameStr.includes('firewall');
    
    // Filter by template
    if (currentTemplate.value === 'fortigate') match = isFirewall;
    else match = !isFirewall;
    
    // OS Filter
    if (match && osFilter.value !== 'all') {
      const isWin = (h.os || '').toLowerCase().includes('windows');
      if (osFilter.value === 'windows' && !isWin) match = false;
      if (osFilter.value === 'linux' && isWin) match = false; 
    }
    
    // Search Query
    if (match && searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      match = h.hostname.toLowerCase().includes(q) || h.ip.includes(q);
    }
    return match;
  }).sort((a, b) => {
    // En modo Fortigate, ordenar por sesiones activas o si está Offline
    if (currentTemplate.value === 'fortigate') {
      if (a.status === 'Offline' && b.status !== 'Offline') return -1;
      if (b.status === 'Offline' && a.status !== 'Offline') return 1;
      return (b.sessions || 0) - (a.sessions || 0);
    }
    // Resto de ordenamiento (Offline primero)
    if (a.status === 'Offline' && b.status !== 'Offline') return -1;
    if (b.status === 'Offline' && a.status !== 'Offline') return 1;
    return a.hostname.localeCompare(b.hostname);
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

// Paleta corporativa: cada servidor siempre tiene el mismo color en todas las graficas
const SERVER_PALETTE = [
  '#1a73e8', // Azul Google
  '#34a853', // Verde esmeralda
  '#e53935', // Rojo
  '#f9ab00', // Ámbar
  '#8e24aa', // Púrpura
  '#00897b', // Teal
  '#f4511e', // Naranja
  '#039be5', // Celeste
];

// Devuelve el color asignado a un servidor según su posición en selectedHosts
const serverColors = computed(() => {
  if (!selectedHosts.value || selectedHosts.value.length === 0) return ['#1a73e8'];
  return selectedHosts.value.map((h, i) => SERVER_PALETTE[i % SERVER_PALETTE.length]);
});

// Tooltip personalizado para graficas de detalle (mini): solo muestra cuando intersect
const makeDetailTooltip = (yFormatter) => ({
  theme: 'dark',
  intersect: true,
  shared: false,
  followCursor: false,
  fixed: { enabled: false },
  x: { format: 'dd MMM HH:mm:ss' },
  y: { formatter: yFormatter }
});

const cpuOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 2 },
  colors: serverColors.value,
  xaxis: {
    type: 'datetime',
    labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } },
    axisBorder: { show: false }, axisTicks: { show: false }, tooltip: { enabled: false }
  },
  yaxis: { min: 0, max: 100, tickAmount: 2, labels: { style: { fontSize: '9px', colors: '#94a3b8' }, formatter: (v) => v.toFixed(0) + '%' } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px', markers: { radius: 12 } },
  grid: { show: false, padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: makeDetailTooltip((v) => v != null ? v.toFixed(1) + '%' : '--')
}));

const ramOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'smooth', width: 2 },
  colors: serverColors.value,
  xaxis: {
    type: 'datetime',
    labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } },
    axisBorder: { show: false }, axisTicks: { show: false }
  },
  yaxis: { min: 0, max: 100, labels: { style: { fontSize: '9px', colors: '#94a3b8' }, formatter: (v) => v.toFixed(0) + '%' } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { show: false, padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: makeDetailTooltip((v) => v != null ? v.toFixed(1) + '%' : '--')
}));

const detailAreaOptions = computed(() => ({
  chart: { type: 'area', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'Inter, sans-serif' },
  stroke: { curve: 'smooth', width: 2 },
  colors: serverColors.value,
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.0, stops: [0, 100] }
  },
  xaxis: {
    type: 'datetime',
    labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } },
    axisBorder: { show: false }, axisTicks: { show: false }, tooltip: { enabled: false }
  },
  yaxis: { min: 0, max: 100, tickAmount: 2, labels: { style: { fontSize: '9px', colors: '#94a3b8' }, formatter: (v) => v.toFixed(0) + '%' } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px', markers: { radius: 12 } },
  grid: { show: false, padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: makeDetailTooltip((v) => v != null ? v.toFixed(1) + '%' : '--')
}));

const latencyOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'straight', width: 2 },
  colors: serverColors.value,
  xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { min: 0, labels: { style: { fontSize: '9px', colors: '#94a3b8' } } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { show: false, padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: makeDetailTooltip((v) => v != null ? v.toFixed(3) : '--')
}));

const pingSeries = computed(() => selectedHosts.value.map(h => ({
  name: h.hostname, data: comparisonData.value[h.hostid]?.ping?.history || []
})));

const pingOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'inherit' },
  stroke: { curve: 'straight', width: 2 },
  colors: serverColors.value,
  xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' } }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { min: 0, labels: { style: { fontSize: '9px', colors: '#94a3b8' }, formatter: (v) => v.toFixed(1) } },
  dataLabels: { enabled: false },
  legend: { show: true, position: 'bottom', fontSize: '10px' },
  grid: { show: false, padding: { top: 0, bottom: 0, left: 10, right: 0 } },
  tooltip: makeDetailTooltip((v) => v != null ? v.toFixed(2) + ' ms' : '--')
}));

// Formateador dinámico del eje Y: muestra la unidad correcta según el valor
const formatNetAxisLabel = (val) => {
  if (val >= 1000) return (val / 1000).toFixed(1) + ' Mbps';
  if (val >= 1)    return val.toFixed(0) + ' Kbps';
  if (val > 0)     return (val * 1000).toFixed(0) + ' bps';
  return '0';
};

const netTrafficOptions = computed(() => {
  const isMulti = selectedHosts.value.length > 1;
  // Si comparamos, generamos 2 colores por host (In, Out) con el mismo color base del servidor
  const colors = isMulti 
    ? selectedHosts.value.flatMap((h, i) => { const c = SERVER_PALETTE[i % SERVER_PALETTE.length]; return [c, c]; })
    : ['#22C55E', '#EF4444'];
  
  // Si comparamos, la línea "In" es sólida (0), la línea "Out" es punteada (4)
  const dashArray = isMulti 
    ? selectedHosts.value.flatMap(() => [0, 4])
    : [0, 0];
    
  return {
    chart: { type: 'line', stacked: false, toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'Inter, sans-serif', zoom: { enabled: false } },
    stroke: { curve: 'straight', width: 1.5, dashArray },
    colors,
    fill: {
      type: isMulti ? selectedHosts.value.flatMap(() => ['gradient', 'transparent']) : ['gradient', 'solid'],
      gradient: { shadeIntensity: 1, opacityFrom: 0.8, opacityTo: 0.3, stops: [0, 100] },
      opacity: isMulti ? selectedHosts.value.flatMap(() => [0.8, 1]) : [0.8, 1]
    },
    dataLabels: { enabled: false },
    markers: { size: 0 },
    xaxis: { type: 'datetime', labels: { datetimeUTC: false, style: { fontSize: '9px', colors: '#94a3b8' }, datetimeFormatter: { hour: 'HH:mm', minute: 'HH:mm:ss' } }, axisBorder: { show: false }, axisTicks: { show: false }, tooltip: { enabled: false } },
    yaxis: { min: 0, forceNiceScale: true, tickAmount: 4, labels: { style: { fontSize: '9px', colors: '#94a3b8' }, formatter: formatNetAxisLabel } },
    legend: { show: false },
    grid: { borderColor: '#e8edf2', strokeDashArray: 3, xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } }, row: { colors: ['#f1f5f9', '#f1f5f9'], opacity: 1 }, padding: { top: 4, bottom: 0, left: 8, right: 12 } },
    tooltip: makeDetailTooltip((val) => {
      if (val === undefined || val === null || isNaN(val)) return '0.00 Kbps';
      if (val >= 1000) return (val / 1000).toFixed(2) + ' Mbps';
      return val.toFixed(2) + ' Kbps';
    })
  };
});

const sessionOptions = {
  chart: { type: 'area', toolbar: { show: false }, animations: { enabled: false }, fontFamily: 'Inter, sans-serif' },
  stroke: { curve: 'smooth', width: 2 },
  colors: ['#8b5cf6'],
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.25, opacityTo: 0.05, stops: [0, 100] } },
  xaxis: { type: 'datetime', tooltip: { enabled: false } },
  yaxis: { min: 0 },
  dataLabels: { enabled: false },
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
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out forwards;
}

/* Transiciones suaves para datos reactivos (PBX) */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(-5px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(5px);
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border-left-color: #3b82f6;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: #f1f5f9; 
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1; 
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8; 
}

.sparkline-wrap :deep(.apexcharts-yaxis),
.sparkline-wrap :deep(.apexcharts-xaxis),
.sparkline-wrap :deep(.apexcharts-grid),
.sparkline-wrap :deep(.apexcharts-gridline),
.sparkline-wrap :deep(.apexcharts-xaxis-tick),
.sparkline-wrap :deep(.apexcharts-inner > line) {
  display: none !important;
}

:deep(.apexcharts-legend-marker) {
  width: 8px !important;
  height: 8px !important;
  border-radius: 50% !important;
  margin-right: 4px !important;
}

:deep(.apexcharts-tooltip.apexcharts-theme-light),
:deep(.apexcharts-tooltip.apexcharts-theme-dark),
:deep(.apexcharts-tooltip) {
  z-index: 999999 !important;
  background-color: #1e293b !important;
  border: 1px solid #334155 !important;
  color: #f8fafc !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
}

:deep(.apexcharts-tooltip-title) {
  background-color: #0f172a !important;
  border-bottom: 1px solid #334155 !important;
  color: #94a3b8 !important;
  font-family: inherit !important;
  font-weight: 700 !important;
  margin-bottom: 0 !important;
}

:deep(.apexcharts-tooltip-text),
:deep(.apexcharts-tooltip-y-group),
:deep(.apexcharts-tooltip-text-y-value) {
  color: #f8fafc !important;
  font-family: inherit !important;
}

.trend-chart :deep(.apexcharts-tooltip) {
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
