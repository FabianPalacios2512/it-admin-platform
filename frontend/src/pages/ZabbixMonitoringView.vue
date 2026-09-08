<template>
  <div class="zabbix-monitoring-container flex flex-col gap-4 font-sans pb-10">
    <!-- Header -->
    <header class="flex justify-between items-center shrink-0">
      <div>
        <h1 class="text-xl font-bold text-slate-800 tracking-tight leading-tight">Centro de Telemetría</h1>
        <p class="text-xs text-slate-500 mt-0.5">Estado en tiempo real de todos los servidores monitoreados</p>
      </div>
      <div class="flex items-center gap-4">
        <!-- Templates Selector (iOS Segmented Control Style) -->
        <div class="inline-flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button @click="currentTemplate = 'global'" :class="currentTemplate === 'global' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">Global</button>
          <button @click="currentTemplate = 'issabel'" :class="currentTemplate === 'issabel' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">PBX Issabel</button>
          <button @click="currentTemplate = 'fortigate'" :class="currentTemplate === 'fortigate' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all whitespace-nowrap">Nodos de Red</button>
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
        <!-- Last Updated Badge (like Zabbix) -->
        <div v-if="lastRefreshed" class="text-[10px] text-slate-400 font-mono bg-slate-50 border border-slate-200 px-2 py-1 rounded-lg flex items-center gap-1.5">
          <i class="fas fa-clock text-slate-300"></i>
          <span>{{ lastRefreshed }}</span>
        </div>
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
        <div class="bg-white rounded-md shadow-sm border border-gray-200 px-3 py-2 flex flex-col justify-between relative overflow-hidden transition-all">
          <div class="flex justify-between items-start mb-0.5">
            <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500">Estado del Motor</span>
          </div>
          <div class="flex items-center gap-3 mt-1">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="pbxData.asterisk_down ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'">
              <i class="fas fa-server text-lg drop-shadow-sm"></i>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-lg font-black tracking-tight truncate" :class="pbxData.asterisk_down ? 'text-red-600' : 'text-slate-800'">
                {{ pbxData.asterisk_down ? 'CAÍDO' : 'EN LÍNEA' }}
              </div>
              <div class="text-[9px] font-semibold text-slate-500 flex items-center gap-1.5 truncate">
                <span class="w-1.5 h-1.5 rounded-full inline-block shrink-0" :class="pbxData.asterisk_down ? 'bg-red-500' : 'bg-emerald-500'"></span>
                Asterisk PBX
              </div>
            </div>
          </div>
        </div>

        <!-- Tarjeta 2: Llamadas Activas (clickable) -->
        <div
          @click="!pbxData.asterisk_down && (showActiveCalls = true)"
          class="bg-white rounded-md shadow-sm border border-gray-200 px-3 py-2 flex flex-col justify-between items-center text-center relative overflow-hidden transition-all"
          :class="!pbxData.asterisk_down ? 'cursor-pointer hover:border-blue-300 hover:shadow-blue-100 hover:shadow-md group' : ''"
        >
          <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-0.5">Llamadas Activas</span>
          <div class="flex items-center gap-2 mt-0.5">
            <div class="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center shrink-0 group-hover:bg-blue-100 transition-colors">
              <i class="fas fa-phone-alt text-[11px] text-blue-500 drop-shadow-sm"></i>
            </div>
            <div class="text-2xl font-black font-mono tracking-tighter leading-none" :class="pbxData.asterisk_down ? 'text-red-500' : 'text-slate-800'">
              {{ pbxData.asterisk_down ? '--' : pbxData.llamadas_activas }}
            </div>
          </div>
          <span class="text-[8px] text-slate-400 font-bold uppercase mt-1.5 tracking-[0.1em]">Conexiones Concurrentes</span>
          <!-- Click hint -->
          <div v-if="!pbxData.asterisk_down" class="absolute bottom-1 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <span class="text-[8px] text-blue-500 font-bold flex items-center gap-1"><i class="fas fa-eye"></i> Ver detalle</span>
          </div>
        </div>

        <!-- Tarjeta 3: Troncal SIP IN-HYM -->
        <div class="bg-white rounded-md shadow-sm px-3 py-2 flex flex-col justify-between relative overflow-hidden transition-all"
             :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-50 border-l-4 border-y border-r border-red-500' : 'border border-gray-200'">
          <div class="flex justify-between items-start mb-0.5">
            <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-600' : ''">Troncal SIP (Claro/Tigo)</span>
            <span class="text-[8px] font-bold text-slate-400 mt-0.5 uppercase" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-500' : ''">
              <span class="w-1.5 h-1.5 rounded-full inline-block shrink-0 mr-0.5 align-middle" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-500' : 'bg-slate-300'"></span>
              Enlace [IN-HYM]
            </span>
          </div>
          <div class="flex items-center gap-3 mt-1">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down) ? 'bg-emerald-50 text-emerald-500' : ((pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-slate-50 text-slate-400')">
              <i class="fas fa-exclamation-triangle text-lg drop-shadow-sm" v-if="pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down"></i>
              <i class="fas fa-network-wired text-lg drop-shadow-sm" v-else></i>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-lg font-black tracking-tight truncate" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'text-slate-800' : ((pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-700' : 'text-slate-500')">
                {{ pbxData.server_down ? 'DESCONECT' : (pbxData.asterisk_down ? 'CAÍDO' : (pbxData.troncal_101 === 1 ? 'OK' : (pbxData.troncal_101 === 0 ? 'FALLA' : 'N/A'))) }}
              </div>
              <div class="text-[9px] font-semibold flex items-center gap-1.5 truncate" :class="(pbxData.troncal_101 === 0 || pbxData.server_down || pbxData.asterisk_down) ? 'text-red-500' : 'text-slate-500'">
                <span class="w-1.5 h-1.5 rounded-full inline-block shrink-0" :class="(pbxData.troncal_101 === 1 && !pbxData.server_down && !pbxData.asterisk_down) ? 'bg-emerald-500' : 'bg-red-600'"></span>
                Enlace [IN-HYM]
              </div>
            </div>
          </div>
        </div>

        <!-- Tarjeta 4: Extensiones Registradas -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 px-3 py-2 flex flex-col justify-between items-center text-center relative overflow-hidden transition-all">
          <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-0.5">Ext. Registradas</span>
          <div class="flex items-center gap-2 mt-0.5">
            <div class="w-7 h-7 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
              <i class="fas fa-users text-[11px] text-emerald-500 drop-shadow-sm"></i>
            </div>
            <div class="text-xl font-black font-mono tracking-tighter leading-none" :class="pbxData.asterisk_down ? 'text-red-500' : 'text-slate-800'">
              {{ pbxData.asterisk_down ? '-- / --' : `${pbxData.ext_online} / ${pbxData.ext_total}` }}
            </div>
          </div>
          <span class="text-[8px] text-slate-400 font-bold uppercase mt-1.5 tracking-[0.1em]">Online / Total</span>
        </div>
      </div>

      <!-- Fila 2: Infraestructura y Opciones -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2">

        <!-- Columna Central: Estado de Seguridad (NOC Style) -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 transition-all flex flex-col relative overflow-hidden">
          <!-- Header -->
          <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-3 flex items-center gap-2">
            Estado de Seguridad
          </h3>

          <div v-if="pbxSecurityStatus.loading && !pbxSecurityStatus.fetched" class="flex justify-center items-center flex-1">
            <i class="fas fa-circle-notch fa-spin text-slate-300"></i>
          </div>

          <div v-else class="flex gap-3 items-stretch flex-1">

            <!-- Columna Izquierda: Estado general (estilo imagen referencia) -->
            <div class="flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-lg min-w-[90px] shrink-0 transition-all"
                 :class="pbxSecurityStatus.anomaly
                   ? 'bg-red-50 border border-red-200'
                   : 'bg-emerald-50 border border-emerald-200'">
              <!-- Icono escudo con check o exclamación -->
              <div class="relative mb-1">
                <i class="fas fa-shield-alt text-3xl"
                   :class="pbxSecurityStatus.anomaly ? 'text-red-400' : 'text-emerald-400'"></i>
                <span class="absolute -bottom-0.5 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-white text-[8px] font-bold"
                      :class="pbxSecurityStatus.anomaly ? 'bg-red-500' : 'bg-emerald-500'">
                  <i class="fas" :class="pbxSecurityStatus.anomaly ? 'fa-exclamation' : 'fa-check'"></i>
                </span>
              </div>
              <span class="text-[9px] font-black uppercase tracking-tight text-center leading-tight"
                    :class="pbxSecurityStatus.anomaly ? 'text-red-600' : 'text-emerald-600'">
                {{ pbxSecurityStatus.anomaly ? 'ALERTA' : 'SIN ANOMALÍAS' }}
              </span>
              <span class="text-[8px] text-slate-500 text-center leading-tight">
                {{ pbxSecurityStatus.anomaly ? 'Revisar sistema' : 'Sistema estable' }}
              </span>
            </div>

            <!-- Separador -->
            <div class="w-px bg-slate-100 shrink-0"></div>

            <!-- Columna Derecha: KPIs en grid -->
            <div class="flex flex-1 items-center justify-between gap-4 px-2">

              <!-- KPI 1: Intentos de acceso 24h -->
              <div class="flex items-center gap-2.5">
                <div class="text-3xl font-black font-mono leading-none tracking-tighter"
                     :class="(pbxSecurityStatus.failed_attempts_24h || 0) > 50 ? 'text-red-600' : 'text-slate-800'">
                  {{ pbxSecurityStatus.failed_attempts_24h ?? '--' }}
                </div>
                <div class="flex flex-col text-left">
                  <div class="flex items-center gap-1.5 text-slate-600">
                    <span class="text-[9px] font-bold leading-tight">Intentos de acceso</span>
                  </div>
                  <div class="flex items-center gap-1 mt-0.5">
                    <i class="fas fa-door-open text-slate-400 text-[10px]"></i>
                    <span class="text-[8px] text-slate-400 font-medium">(últimas 24h)</span>
                  </div>
                </div>
              </div>

              <!-- KPI 2: IPs bloqueadas -->
              <div class="flex items-center gap-2.5">
                <div class="text-3xl font-black font-mono leading-none tracking-tighter"
                     :class="(pbxSecurityStatus.blocked_ips || 0) > 0 ? 'text-amber-600' : 'text-slate-800'">
                  {{ pbxSecurityStatus.blocked_ips ?? '--' }}
                </div>
                <div class="flex flex-col text-left">
                  <div class="flex items-center gap-1.5 text-slate-600">
                    <span class="text-[9px] font-bold leading-tight">Bloqueos activos</span>
                  </div>
                  <div class="flex items-center gap-1 mt-0.5">
                    <i class="fas fa-ban text-slate-400 text-[10px]"></i>
                    <span class="text-[8px] text-slate-400 font-medium">(por Fail2Ban)</span>
                  </div>
                </div>
              </div>

              <!-- KPI 3: IPs sospechosas -->
              <div class="flex items-center gap-2.5">
                <div class="text-3xl font-black font-mono leading-none tracking-tighter"
                     :class="(pbxSecurityStatus.suspicious_ips || 0) > 5 ? 'text-red-600' : 'text-slate-800'">
                  {{ pbxSecurityStatus.suspicious_ips ?? '--' }}
                </div>
                <div class="flex flex-col text-left">
                  <div class="flex items-center gap-1.5 text-slate-600">
                    <span class="text-[9px] font-bold leading-tight">IPs sospechosas</span>
                  </div>
                  <div class="flex items-center gap-1 mt-0.5">
                    <i class="fas fa-user-secret text-slate-400 text-[10px]"></i>
                    <span class="text-[8px] text-slate-400 font-medium">(últimas 24h)</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>


        <!-- Columna Derecha: Almacenamiento PBX -->
        <div class="bg-white rounded-md shadow-sm border border-gray-200 p-4 transition-all flex flex-col justify-center relative">
          <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-2 flex items-center gap-2">
            Almacenamiento PBX
          </h3>
          <div class="flex flex-col gap-2 mt-1">
            <div class="flex justify-between items-end">
              <div class="flex flex-col">
                <span class="text-xs font-semibold text-slate-700">Ruta de Grabaciones</span>
                <span class="text-[9px] font-mono text-slate-400">/var/spool/asterisk/monitor</span>
              </div>
              <span class="text-lg font-bold font-mono" :class="pbxData.storage_percent > 80 ? 'text-red-600' : 'text-slate-600'">
                {{ pbxData.storage_percent || '--' }}%
              </span>
            </div>
            <div class="h-2.5 w-full bg-slate-100 rounded-sm overflow-hidden border border-slate-200">
              <div class="h-full transition-all duration-500"
                   :class="pbxData.storage_percent > 80 ? 'bg-red-500' : (pbxData.storage_percent > 60 ? 'bg-amber-400' : 'bg-emerald-500')"
                   :style="`width: ${pbxData.storage_percent || 0}%`">
              </div>
            </div>
            <div class="text-[9px] text-slate-400 font-medium text-right mt-0.5 uppercase tracking-widest flex justify-between items-center">
              <button @click="isRecordingsModalOpen = true" class="px-2 py-0.5 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors flex items-center gap-1">
                <i class="fas fa-play-circle"></i> Ver Grabaciones
              </button>
              <button @click="isSecurityModalOpen = true" class="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded hover:bg-indigo-100 transition-colors flex items-center gap-1 ml-2 mr-auto">
                <i class="fas fa-shield-alt"></i> Seguridad
              </button>
              <span>Uso de Disco Crítico > 80%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Fila 3: Servicios PBX -->
      <div v-if="issabelHostId" class="bg-white rounded-md shadow-sm border border-gray-200 p-4 mt-2 transition-all">
        <h3 class="text-[9px] font-bold uppercase tracking-[0.15em] text-slate-500 mb-4">
          Servicios PBX
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 divide-x divide-slate-100 items-center">
          
          <!-- Asterisk -->
          <div class="flex items-center gap-3 px-2">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="pbxData.asterisk_down ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'">
              <i class="fas fa-asterisk text-[10px]"></i>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-700 uppercase tracking-wide">Asterisk</p>
              <p class="text-[9px] font-bold uppercase mt-0.5 flex items-center gap-1" :class="pbxData.asterisk_down ? 'text-red-500' : 'text-emerald-500'">
                <span class="inline-block w-1.5 h-1.5 rounded-full" :class="pbxData.asterisk_down ? 'bg-red-500' : 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]'"></span>
                {{ pbxData.asterisk_down ? 'Caído' : 'Activo' }}
              </p>
            </div>
          </div>

          <!-- Firewalld -->
          <div class="flex items-center gap-3 px-4">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="pbxSecurityStatus.firewalld ? 'bg-emerald-50 text-emerald-500' : 'bg-slate-100 text-slate-400'">
              <i class="fas fa-shield-alt text-[10px]"></i>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-700 uppercase tracking-wide">Firewalld</p>
              <p class="text-[9px] font-bold uppercase mt-0.5 flex items-center gap-1" :class="pbxSecurityStatus.firewalld ? 'text-emerald-500' : 'text-slate-400'">
                <span class="inline-block w-1.5 h-1.5 rounded-full" :class="pbxSecurityStatus.firewalld ? 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]' : 'bg-slate-300'"></span>
                {{ pbxSecurityStatus.firewalld ? 'Activo' : 'Inactivo' }}
              </p>
            </div>
          </div>

          <!-- Fail2Ban -->
          <div class="flex items-center gap-3 px-4">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="pbxSecurityStatus.fail2ban ? 'bg-emerald-50 text-emerald-500' : 'bg-red-50 text-red-500'">
              <i class="fas fa-ban text-[10px]"></i>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-700 uppercase tracking-wide">Fail2Ban</p>
              <p class="text-[9px] font-bold uppercase mt-0.5 flex items-center gap-1" :class="pbxSecurityStatus.fail2ban ? 'text-emerald-500' : 'text-red-500'">
                <span class="inline-block w-1.5 h-1.5 rounded-full" :class="pbxSecurityStatus.fail2ban ? 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]' : 'bg-red-500'"></span>
                {{ pbxSecurityStatus.fail2ban ? 'Activo' : 'Inactivo' }}
              </p>
            </div>
          </div>

          <!-- Web Panel / HTTPS -->
          <div class="flex items-center gap-3 px-4">
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0" :class="pbxSecurityStatus.httpd ? 'bg-emerald-50 text-emerald-500' : (pbxSecurityStatus.httpd === false ? 'bg-red-50 text-red-500' : 'bg-slate-100 text-slate-400')">
              <i class="fas fa-globe text-[10px]"></i>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-700 uppercase tracking-wide">Panel Web</p>
              <p class="text-[9px] font-bold uppercase mt-0.5 flex items-center gap-1" :class="pbxSecurityStatus.httpd ? 'text-emerald-500' : (pbxSecurityStatus.httpd === false ? 'text-red-500' : 'text-slate-400')">
                <span class="inline-block w-1.5 h-1.5 rounded-full" :class="pbxSecurityStatus.httpd ? 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]' : (pbxSecurityStatus.httpd === false ? 'bg-red-500' : 'bg-slate-300')"></span>
                {{ pbxSecurityStatus.httpd ? 'Activo' : (pbxSecurityStatus.httpd === false ? 'Caído' : 'Cargando...') }}
              </p>
            </div>
          </div>

          <!-- Tiempo de operación -->
          <div class="flex items-center gap-3 px-4">
            <div class="w-8 h-8 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
              <i class="fas fa-clock text-[10px]"></i>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-700 uppercase tracking-wide">Uptime</p>
              <p class="text-[10px] font-bold font-mono mt-0.5 text-slate-600">
                {{ pbxSecurityStatus.uptime || 'Calculando...' }}
              </p>
            </div>
          </div>

        </div>
      </div>

      <!-- Fila 4: Tráfico de Red (Full Width) -->
      <div v-if="issabelHostId && comparisonData[issabelHostId]" class="mt-2 mb-2 w-full h-[350px]">
        <div class="bg-white p-3 rounded-md shadow-sm border border-gray-200 flex flex-col h-full w-full">
          <div class="flex justify-between items-center mb-1 shrink-0">
            <span class="text-[11px] font-bold text-slate-700 tracking-[0.1em] uppercase flex items-center gap-2">
              TRÁFICO DE RED (IN/OUT)
            </span>
            <div class="font-mono text-[10px] text-gray-500 flex gap-4 flex-wrap">
              <span><span class="w-2 h-2 bg-[#22c55e] inline-block mr-1"></span>In: <b class="text-gray-700">{{ networkStats.in.last }}</b> avg {{ networkStats.in.avg }} max {{ networkStats.in.max }}</span>
              <span><span class="w-2 h-2 bg-[#ef4444] inline-block mr-1"></span>Out: <b class="text-gray-700">{{ networkStats.out.last }}</b> avg {{ networkStats.out.avg }} max {{ networkStats.out.max }}</span>
            </div>
          </div>
          <div class="flex-1 w-full relative min-h-0">
            <apexchart
              :key="netChartKey"
              type="line"
              height="100%"
              class="absolute inset-0"
              :options="netTrafficOptions"
              :series="issabelNetSeries"
            />
          </div>
        </div>
      </div>

    </div>


    <!-- Vista Dedicada: Nodos de Red (FortiGate) -->
    <div v-if="renderError" class="bg-red-50 border-l-4 border-red-500 p-4 m-4">
      <h3 class="text-red-800 font-bold">Error fatal al cargar Nodos de Red:</h3>
      <pre class="text-xs text-red-600 mt-2 whitespace-pre-wrap">{{ renderError }}</pre>
    </div>
    <FortiGateMonitorView v-if="currentTemplate === 'fortigate' && !renderError" />

    <!-- Data Table: Solo para Global (servidores Zabbix) -->
    <div v-if="currentTemplate === 'global'" class="bg-white rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] relative">
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
          <!-- Group Filter Dropdown -->
          <select v-model="selectedGroup" @change="refreshAll(true)" class="border border-slate-200 rounded-lg text-[13px] px-2 py-1.5 text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 hover:bg-white transition-colors max-w-[200px] truncate">
            <option value="all">Todos los Grupos</option>
            <option v-for="g in groups" :key="g.groupid" :value="g.groupid">{{ g.name }}</option>
          </select>

        </div>
      </div>

      <div class="w-full overflow-x-auto">
        <table class="w-full text-left border-collapse min-w-[800px]">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest text-center w-16">Estado</th>
              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Servidor</th>
              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">IP</th>

              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">CPU (%)</th>
              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">RAM Usada (%)</th>
              <th class="py-3 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">RED (IN / OUT)</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="host in paginatedHosts" :key="host.hostid" 
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
                    <span class="text-blue-600">↓ {{ formatTrafficVal((host.net_in || 0) / 1000) }}</span>
                    <span class="text-purple-600">↑ {{ formatTrafficVal((host.net_out || 0) / 1000) }}</span>
                  </div>
                </td>
              </template>
            </tr>
            <tr v-if="!loadingHosts && hosts.length === 0">
              <td colspan="5" class="py-16 text-center text-slate-500 font-medium">No se encontraron servidores</td>
            </tr>
          </tbody>
        </table>

        <!-- Paginator -->
        <div v-if="filteredHosts.length > itemsPerPage" class="px-4 py-3 border-t border-slate-100 flex items-center justify-between bg-slate-50 rounded-b-xl">
          <span class="text-[11px] text-slate-500 font-medium">Mostrando {{ (currentPage - 1) * itemsPerPage + 1 }} - {{ Math.min(currentPage * itemsPerPage, filteredHosts.length) }} de {{ filteredHosts.length }} servidores</span>
          <div class="flex gap-1.5 items-center">
            <button @click="currentPage--" :disabled="currentPage === 1" class="px-3 py-1.5 text-[11px] font-bold rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all">Anterior</button>
            <span class="px-3 py-1.5 text-[11px] font-black text-slate-700 bg-white border border-slate-200 rounded-md shadow-sm">{{ currentPage }} / {{ totalPages }}</span>
            <button @click="currentPage++" :disabled="currentPage === totalPages" class="px-3 py-1.5 text-[11px] font-bold rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all">Siguiente</button>
          </div>
        </div>
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
          <apexchart :type="expandedOptions.chart.type || 'line'" width="100%" height="100%" :options="expandedOptions" :series="expandedSeries" />
        </div>
        <div v-if="expandedStats && expandedStats.length > 0" class="px-6 py-4 bg-slate-50 border-t border-slate-200 rounded-b-2xl overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr>
                <th class="pb-2 text-xs font-semibold text-slate-500 border-b border-slate-200">Serie</th>
                <th class="pb-2 text-xs font-semibold text-slate-500 border-b border-slate-200 text-right">Último</th>
                <th class="pb-2 text-xs font-semibold text-slate-500 border-b border-slate-200 text-right">Mínimo</th>
                <th class="pb-2 text-xs font-semibold text-slate-500 border-b border-slate-200 text-right">Promedio</th>
                <th class="pb-2 text-xs font-semibold text-slate-500 border-b border-slate-200 text-right">Máximo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(stat, idx) in expandedStats" :key="idx" class="border-b border-slate-100 last:border-0 hover:bg-slate-100 transition-colors">
                <td class="py-2 text-xs font-medium text-slate-700 flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-sm inline-block shadow-sm" :style="{ backgroundColor: stat.color }"></span>
                  {{ stat.name }}
                </td>
                <td class="py-2 text-xs font-semibold text-blue-600 text-right">{{ stat.last }}</td>
                <td class="py-2 text-xs font-semibold text-emerald-500 text-right">{{ stat.min }}</td>
                <td class="py-2 text-xs font-semibold text-slate-600 text-right">{{ stat.avg }}</td>
                <td class="py-2 text-xs font-semibold text-red-500 text-right">{{ stat.max }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Modals -->
    <RecordingsModal :isOpen="isRecordingsModalOpen" @close="isRecordingsModalOpen = false" />
    <ActiveCallsModal :isOpen="isActiveCallsModalOpen" @close="isActiveCallsModalOpen = false" />
    <SecurityModal :isOpen="isSecurityModalOpen" @close="isSecurityModalOpen = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick, onErrorCaptured } from 'vue';
import RecordingsModal from '@/components/pbx/RecordingsModal.vue';
import ActiveCallsModal from '@/components/pbx/ActiveCallsModal.vue';
import SecurityModal from '@/components/pbx/SecurityModal.vue';
import FortiGateMonitorView from './FortiGateMonitorView.vue';
import zabbixService from '../services/zabbix.service';
import { useChartDownsampling } from '@/composables/useChartDownsampling';

const renderError = ref(null);
const isRecordingsModalOpen = ref(false);
const isActiveCallsModalOpen = ref(false);
const isSecurityModalOpen = ref(false);
onErrorCaptured((err, instance, info) => {
  renderError.value = `${err.toString()} \nInfo: ${info}`;
  console.error("Caught error:", err, info);
  return false; // prevent propagation
});

const { downsampleSeries } = useChartDownsampling();

const pbxData = ref({
  has_fetched: false,
  loading: false,
  asterisk_down: false,
  server_down: false,
  llamadas_activas: 0,
  trunks: [],
  robot_ivr: -1,
  ruta_opcion1: -1,
  ruta_opcion2: -1,
  troncal_101: -1,
  extensiones_registradas: '112 / 120', // Mock data
  almacenamiento_pbx: 45, // Mock data (%)
  ivr_options: {}
});

const pbxSecurityStatus = ref({
  firewalld: false,
  fail2ban: false,
  iptables: false,
  anomaly: false,
  failed_attempts_24h: null,
  blocked_ips: null,
  suspicious_ips: null,
  fetched: false,
  loading: false
});

const fetchPbxSecurityStatus = async () => {
  pbxSecurityStatus.value.loading = true;
  try {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/v1/pbx/recordings/security/status', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'success') {
        pbxSecurityStatus.value = { ...data.data, fetched: true, loading: false };
      }
    }
  } catch (e) {
    console.error("Error fetching PBX security status", e);
  } finally {
    pbxSecurityStatus.value.loading = false;
  }
};

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
      const wasFetched = pbxData.value.has_fetched;
      pbxData.value = {
        has_fetched: true,
        loading: false,
        hostid: res.data.hostid,
        asterisk_down: res.data.asterisk_down,
        server_down: res.data.server_down,
        llamadas_activas: res.data.llamadas_activas,
        robot_ivr: res.data.robot_ivr,
        ruta_opcion1: res.data.ruta_opcion1,
        ruta_opcion2: res.data.ruta_opcion2,
        troncal_101: res.data.troncal_101,
        ext_online: res.data.ext_online,
        ext_total: res.data.ext_total,
        storage_percent: res.data.storage_percent,
        ivr_options: res.data.ivr_options || {},
        trunks: res.data.trunks || []
      };
      
      if (res.data.hostid) {
        issabelHostId.value = res.data.hostid;
      }
      
      if (wasFetched && res.data.asterisk_down && !wasDown) {
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

const groups = ref([]);
const selectedGroup = ref('');

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

  let formatFn = (v) => v.toFixed(2);
  if (expandedChart.value === 'net') formatFn = formatNetAxisLabel;
  else if (expandedChart.value === 'ping') formatFn = (v) => v.toFixed(1) + ' ms';
  else if (expandedChart.value === 'cpu' || expandedChart.value === 'ram') formatFn = (v) => v.toFixed(1) + '%';
  else if (expandedChart.value === 'sessions') formatFn = (v) => Math.round(v).toLocaleString();

  return expandedSeries.value.map((series, i) => {
    let allValues = [];
    if (series.data) {
      allValues = series.data.map(p => p[1]).filter(v => v != null && !isNaN(v));
    }
    
    // El color puede venir de expandedOptions o fallback
    const fallbackColor = SERVER_PALETTE[i % SERVER_PALETTE.length];
    const color = expandedOptions.value.colors?.[i] || fallbackColor;
    
    if (allValues.length === 0) {
      return { name: series.name, last: '--', min: '--', avg: '--', max: '--', color };
    }
    
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const avg = allValues.reduce((a, b) => a + b, 0) / allValues.length;
    const last = allValues[allValues.length - 1];
    
    return {
      name: series.name,
      last: formatFn(last),
      min: formatFn(min),
      avg: formatFn(avg),
      max: formatFn(max),
      color
    };
  });
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
    colors: baseObj.colors ? [...baseObj.colors] : undefined,
    chart: { ...baseObj.chart, toolbar: { show: true }, zoom: { enabled: true } },
    legend: { ...baseObj.legend, fontSize: '13px' },
    xaxis: { ...baseObj.xaxis, labels: { ...baseObj.xaxis?.labels, style: { fontSize: '11px', colors: '#64748b' } } },
    yaxis: { ...baseObj.yaxis, labels: { ...baseObj.yaxis?.labels, style: { fontSize: '11px', colors: '#64748b' }, formatter: baseObj.yaxis?.labels?.formatter } },
    grid: { show: true, borderColor: '#e2e8f0', strokeDashArray: 4, position: 'back', xaxis: { lines: { show: false } }, yaxis: { lines: { show: true } }, padding: { left: 10, right: 10 } },
    tooltip: { 
      theme: 'dark',
      custom: function({series, seriesIndex, dataPointIndex, w}) {
        let hoverTs = w.globals.seriesX?.[seriesIndex]?.[dataPointIndex] ?? w.globals.seriesX?.[0]?.[dataPointIndex];
        let title = '';
        if (hoverTs) {
          let d = new Date(hoverTs);
          title = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
        }
        
        let rows = w.globals.seriesNames.map((name, i) => {
          let val = series[i][dataPointIndex];
          if (val == null) return '';
          let color = w.globals.colors[i];
          let formattedVal = baseObj.yaxis?.labels?.formatter ? baseObj.yaxis.labels.formatter(val) : val;
          return `<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;margin-top:6px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                      <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block;"></span>
                      <span style="color:#cbd5e1;font-size:11px;">${name}</span>
                    </div>
                    <span style="color:#fff;font-weight:bold;font-size:12px;">${formattedVal}</span>
                  </div>`;
        }).filter(r => r !== '').join('');
        
        return `<div style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.3);min-width:140px;font-family:inherit;">
                  <div style="color:#94a3b8;font-size:11px;font-weight:bold;border-bottom:1px solid #334155;padding-bottom:4px;margin-bottom:4px;">${title}</div>
                  ${rows}
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

// IMPORTANTE: getIssabelSeries debe ser un computed por tipo, NO una función normal.
// Las funciones normales no son reactivas en Vue 3 — Vue no re-ejecuta la plantilla
// cuando cambia comparisonData a menos que la dependencia esté dentro de un computed.
const issabelCpuSeries = computed(() => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  return [{ name: 'CPU (%)', data: comp.cpu?.history || [] }];
});

const issabelRamSeries = computed(() => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  return [{ name: 'RAM (%)', data: comp.ram?.history || [] }];
});

const issabelNetSeries = computed(() => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  const ifaceNames = Object.keys(comp.interfaces || {});
  if (ifaceNames.length === 0) return [];

  // Encontrar la interfaz física con más tráfico (ignorar lo, loopback)
  let bestIface = ifaceNames[0];
  let maxTraffic = -1;
  for (const name of ifaceNames) {
    const lower = name.toLowerCase();
    if (lower.includes('lo') || lower.includes('loopback')) continue;
    const inVal = comp.interfaces[name].in?.value || 0;
    const outVal = comp.interfaces[name].out?.value || 0;
    const totalTraffic = inVal + outVal;
    if (totalTraffic > maxTraffic) {
      maxTraffic = totalTraffic;
      bestIface = name;
    }
  }

  const [alignedIn, alignedOut] = alignSeries(
    comp.interfaces[bestIface].in?.history || [],
    comp.interfaces[bestIface].out?.history || []
  );
  return [
    { name: 'Tráfico de Entrada (In)', type: 'area', data: mapTraffic(alignedIn, true) },
    { name: 'Tráfico de Salida (Out)', type: 'line', data: mapTraffic(alignedOut, false) }
  ];
});

// Alias para compatibilidad con el template (CPU y RAM aún pueden usarlo)
const getIssabelSeries = (type) => {
  if (type === 'cpu') return issabelCpuSeries.value;
  if (type === 'ram') return issabelRamSeries.value;
  return [];
};

// Series reactivas para las 2 gráficas extra
const issabelLoadSeries = computed(() => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  return [{ name: 'Carga Sistema', data: comp.load?.history || [] }];
});

const issabelProcsSeries = computed(() => {
  if (!issabelHostId.value || !comparisonData.value[issabelHostId.value]) return [];
  const comp = comparisonData.value[issabelHostId.value];
  return [{ name: 'Procesos', data: comp.procs?.history || [] }];
});

// Alias para el click del KPI de llamadas activas
const showActiveCalls = isActiveCallsModalOpen;

watch(currentTemplate, async (newVal) => {
  if (newVal === 'issabel') {
    // Buscar hostid de Issabel en hosts filtrados
    let h = hosts.value.find(h => h.hostname.toLowerCase().includes('issabel') || h.hostname.toLowerCase().includes('pbx'));
    
    // Si no está en el grupo seleccionado, pero el backend lo encontró globalmente:
    if (!h && pbxData.value.hostid) {
      h = { hostid: pbxData.value.hostid, hostname: 'Issabel_PBX' };
    }

    if (h) {
      issabelHostId.value = h.hostid;
      if (!comparisonData.value[h.hostid]) {
        loadingIssabelDetail.value = true;
        // Solo intentamos cargar el detalle si el host existe (el dummy podría fallar en detalle si no hay IPs, pero fetchDetailForHost lo maneja)
        try {
          await fetchDetailForHost(h);
        } catch (e) {
          console.error("Error fetching detail for Issabel via fallback", e);
        }
        loadingIssabelDetail.value = false;
      }
    }
  }
});


// Key que fuerza un remontaje completo de ApexCharts para la red.
// ApexCharts no detecta cambios en series mixtas (area+line) via prop diff,
// así que lo forzamos montándolo de nuevo cada vez que llega un nuevo punto.
const netChartKey = ref(0);
watch(issabelNetSeries, (newSeries) => {
  const inData = newSeries?.[0]?.data;
  const lastPoint = inData?.[inData.length - 1];
  if (lastPoint) {
    netChartKey.value = lastPoint[0]; // timestamp del último dato = key única
  }
}, { deep: false });

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
  // Al cambiar el rango, limpiar los datos del PBX para forzar un refetch con el rango nuevo
  if (issabelHostId.value && comparisonData.value[issabelHostId.value]) {
    comparisonData.value = {};
  }
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
    
  // Aplicar nuestro downsampling para agrupar y promediar puntos en rangos largos
  return downsampleSeries(cleanData, 250);
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
    const res = await zabbixService.getGlobalTrends(time_from, time_till, selectedGroup.value);
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
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    
    // Crear el contexto solo si ya hubo interacción del usuario (no en auto-play)
    if (!globalAudioCtx) {
      // Si no existe aún, intentar crearlo; si el navegador lo bloquea lo atrapamos silenciosamente
      try {
        globalAudioCtx = new AudioContextClass();
      } catch {
        return; // Browser blocked autoplay - silent fail
      }
    }
    
    // Si fue suspendido por política del navegador, reanudar
    if (globalAudioCtx.state === 'suspended') {
      globalAudioCtx.resume().catch(() => {}); // catch promise silenciosamente
    }
    
    // Solo reproducir si el contexto está activo (no suspended)
    if (globalAudioCtx.state !== 'running') return;
    
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
  } catch {
    // Audio blocked silently - no console noise
  }
};

const fetchHosts = async (time_from, time_till) => {
  try {
    const res = await zabbixService.getAllHosts(time_from, time_till, selectedGroup.value);
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

const fetchGroups = async () => {
  try {
    const res = await zabbixService.getGroups();
    if (res.status === 'success') {
      groups.value = res.data;
      if (groups.value.length > 0 && !selectedGroup.value) {
        const servGroup = groups.value.find(g => g.name.toLowerCase().includes('servidor'));
        selectedGroup.value = servGroup ? servGroup.groupid : groups.value[0].groupid;
      }
    }
  } catch (e) {
    console.error("Error fetching groups:", e);
  }
};

const lastRefreshed = ref('');

const refreshAll = async (showLoading = true) => {
  if (showLoading) {
    loadingTrends.value = loadingHosts.value = true;
  }
  const { time_from, time_till } = getTimeParams();
  
  if (groups.value.length === 0) {
    await fetchGroups();
  }
  
  const promises = [fetchTrends(time_from, time_till), fetchHosts(time_from, time_till), fetchPbxStats(), fetchPbxSecurityStatus()];
  
  // Siempre refrescar el detalle del PBX Issabel cuando estamos en esa pestaña o cuando ya tenemos su hostid
  if (currentTemplate.value === 'issabel' && issabelHostId.value) {
    const pbxHost = hosts.value.find(h => h.hostid === issabelHostId.value)
      || { hostid: issabelHostId.value, hostname: 'Issabel_PBX' };
    // Pasar siempre el rango seleccionado actualmente
    promises.push(fetchDetailForHost(pbxHost, selectedRange.value));
  }
  
  if (showDetail.value) {
    promises.push(fetchAllDetails(true));
  }
  
  await Promise.all(promises);
  
  // Actualizar timestamp de última actualización (estilo Zabbix)
  const now = new Date();
  lastRefreshed.value = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
  // El timer global (refreshAll) ya llama fetchAllDetails cuando showDetail=true.
  // No necesitamos un timer separado aquí.
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
      
      // Eliminamos el early return silencioso que congelaba el historial.
      // Ahora dejamos que el flujo normal procese las gráficas para que se muevan en tiempo real.
      
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
    // Zabbix devuelve bits/sec (ya que aplica el custom multiplier *8 en la BD).
    // Solo dividimos entre 1000 para llevar a Kbps.
    let kbps = v / 1000;
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
  let maxTraffic = -1;
  for (const name of ifaceNames) {
    const lower = name.toLowerCase();
    if (lower.includes('eth') || lower.includes('ens') || lower.includes('eno') || lower.includes('lan')) {
      const inVal = comp.interfaces[name].in?.value || 0;
      const outVal = comp.interfaces[name].out?.value || 0;
      const totalTraffic = inVal + outVal;
      if (totalTraffic > maxTraffic) {
        maxTraffic = totalTraffic;
        bestIface = name;
      }
    }
  }
  
  const calcStats = (history) => {
    if (!history || history.length === 0) return { ...defaultStats };
    // Zabbix API = bits/sec (por el custom multiplier) -> / 1000 para Kbps
    const values = history.map(p => Math.abs(p[1] / 1000));
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



const trendOptions = (forceDir) => {
  const isLongRange = selectedRange.value > 86400; // mayor a 24 horas (86400 segundos)
  
  return {
    chart: {
      type: 'area',
      toolbar: { show: false },
      zoom: { enabled: false },
      animations: { enabled: !isLongRange, dynamicAnimation: { speed: 300 } },
      fontFamily: 'inherit',
      parentHeightOffset: 0
    },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.15,
        opacityTo: 0.0,
        stops: [0, 100]
      }
    },
    stroke: { width: 2, curve: 'smooth' },
    markers: {
      size: 0,
      hover: { size: 4 }
    },
    states: {
      hover: { filter: { type: 'none' } },
      active: { filter: { type: 'none' } }
    },
    xaxis: {
      type: 'datetime',
      labels: {
        datetimeUTC: false, 
        hideOverlappingLabels: true,
        formatter: function(val) {
          const d = new Date(val);
          if (isLongRange) {
             return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
          }
          return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        },
        style: { fontSize: '9px', colors: '#64748b' }
      },
      axisBorder: { show: true, color: '#e2e8f0' },
      axisTicks: { show: true, color: '#e2e8f0' },
      tickAmount: isLongRange ? 6 : undefined,
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
  };
};

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

// Align two time series so they share the exact same X timestamps.
// Zabbix collects net.if.in and net.if.out at slightly different clock ticks,
// which causes one line to start earlier than the other in ApexCharts.
// We build a merged sorted list of all timestamps and fill missing values via
// nearest-neighbour (not linear interpolation) to keep traffic data realistic.
const alignSeries = (histA, histB) => {
  if (!histA.length || !histB.length) return [histA, histB];
  const tsA = new Map(histA.map(([t, v]) => [t, v]));
  const tsB = new Map(histB.map(([t, v]) => [t, v]));
  const allTs = [...new Set([...tsA.keys(), ...tsB.keys()])].sort((a, b) => a - b);

  const fill = (map, ts) => {
    const keys = [...map.keys()].sort((a, b) => a - b);
    return ts.map(t => {
      if (map.has(t)) return [t, map.get(t)];
      // find nearest key
      let best = keys[0], bestDist = Math.abs(keys[0] - t);
      for (const k of keys) {
        const d = Math.abs(k - t);
        if (d < bestDist) { bestDist = d; best = k; }
      }
      return [t, map.get(best)];
    });
  };

  return [fill(tsA, allTs), fill(tsB, allTs)];
};

const netSeries = computed(() => {
  const series = [];
  const iface = selectedInterface.value;
  if (!iface) return series;

  selectedHosts.value.forEach(h => {
    const d = comparisonData.value[h.hostid];
    if (d && d.interfaces && d.interfaces[iface]) {
      const [alignedIn, alignedOut] = alignSeries(
        d.interfaces[iface].in.history || [],
        d.interfaces[iface].out.history || []
      );
      series.push({ name: `${h.hostname} - Recibido (Bajada)`, type: 'area', data: mapTraffic(alignedIn, true) });
      series.push({ name: `${h.hostname} - Enviado (Subida)`, type: 'line', data: mapTraffic(alignedOut, false) });
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
    const isFirewall = nameStr.includes('forti') || nameStr.includes('firewall') || nameStr.includes('fgt');
    
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

const currentPage = ref(1);
const itemsPerPage = ref(15);

const totalPages = computed(() => Math.ceil(filteredHosts.value.length / itemsPerPage.value) || 1);

const paginatedHosts = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return filteredHosts.value.slice(start, end);
});

watch([searchQuery, osFilter, selectedGroup, currentTemplate], () => {
  currentPage.value = 1;
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
  colors: [...serverColors.value],
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
  colors: [...serverColors.value],
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
  colors: [...serverColors.value],
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
  colors: [...serverColors.value],
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
  colors: [...serverColors.value],
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
  const rangeMs = selectedRange.value * 1000;
  // Adaptar el formatter del eje X según el rango seleccionado
  const xFormatter = (val) => {
    const d = new Date(val);
    if (selectedRange.value <= 1800) {
      // <= 30 min: mostrar HH:mm:ss
      return d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    return d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  };
  const now = Date.now();
  return {
  chart: {
    type: 'line',
    stacked: false,
    toolbar: { show: false },
    animations: { enabled: false },
    fontFamily: 'Inter, sans-serif',
    zoom: { enabled: false },
    parentHeightOffset: 0
  },
  stroke: { curve: 'straight', width: [1.5, 1.5] },
  colors: ['#22c55e', '#ef4444'], // Verde para IN, Rojo para OUT
  fill: {
    type: ['gradient', 'solid'],
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.6,
      opacityTo: 0.2,
      stops: [0, 100]
    },
    opacity: [1, 1] // La serie 2 (OUT) es tipo 'line' por lo que no tendrá relleno de todas formas, pero opacity 1 asegura que la línea sea visible
  },
  dataLabels: { enabled: false },
  markers: { size: 0, strokeWidth: 0, hover: { size: 3 } },
  xaxis: {
    type: 'datetime',
    labels: {
      datetimeUTC: false,
      style: { fontSize: '9px', colors: '#64748b' },
      formatter: xFormatter,
      offsetY: 2
    },
    axisBorder: { show: false },
    axisTicks: { show: true, color: '#e2e8f0' },
    tooltip: { enabled: false }
  },
  yaxis: {
    min: 0,
    forceNiceScale: false,
    tickAmount: 5,
    labels: {
      style: { fontSize: '9px', colors: '#64748b' },
      formatter: formatNetAxisLabel,
      offsetX: -10
    }
  },
  legend: { show: false }, // Movido al header del div
  grid: {
    borderColor: '#e2e8f0',
    strokeDashArray: 3,
    xaxis: { lines: { show: true } },
    yaxis: { lines: { show: true } },
    padding: { top: 0, bottom: 0, left: 0, right: 0 }
  },
  tooltip: {
    theme: 'dark',
    shared: true,
    intersect: false,
    y: {
      formatter: (val) => {
        if (val === undefined || val === null || isNaN(val)) return '0.00 Kbps';
        if (val >= 1000) return (val / 1000).toFixed(2) + ' Mbps';
        return val.toFixed(2) + ' Kbps';
      }
    },
    x: { format: 'HH:mm:ss' }
  }
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


// Usa setTimeout recursivo en lugar de setInterval para evitar condiciones de carrera:
// el siguiente ciclo solo arranca cuando el anterior terminó completamente.
const scheduleRefresh = () => {
  globalTimer = setTimeout(async () => {
    await refreshAll(false);
    scheduleRefresh(); // encadenar el siguiente ciclo
  }, 5000);
};

onMounted(() => {
  refreshAll().then(() => scheduleRefresh());
});

onUnmounted(() => {
  if (globalTimer) clearTimeout(globalTimer);
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
