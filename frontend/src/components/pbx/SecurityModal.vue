<template>
  <teleport to="body">
    <transition name="drawer">
      <div v-if="isOpen" class="fixed inset-0 z-[9999] flex justify-end" @keydown.esc="close">
        
        <!-- Backdrop tenue -->
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" @click="close"></div>
        
        <!-- Drawer Panel -->
        <div class="relative bg-white h-full w-[85vw] max-w-7xl shadow-2xl flex flex-col drawer-panel">
          
          <!-- Header -->
          <div class="sticky top-0 bg-white z-10 shrink-0 px-8 pt-6 pb-0 flex flex-col border-b border-slate-200/60">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-md">
                  <i class="fas fa-shield-alt text-lg"></i>
                </div>
                <div>
                  <h2 class="text-lg font-bold text-slate-900 tracking-tight">Centro de Seguridad PBX</h2>
                  <p class="text-xs text-slate-500 font-medium mt-0.5">Gestión de Firewall y Auditoría SIP</p>
                </div>
              </div>

              <div class="flex items-center gap-4">
                <!-- Refresh Button -->
                <button 
                  @click="activeTab === 'live' ? fetchLogs() : fetchBlockedIps()" 
                  :disabled="loading"
                  class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200/60 rounded-lg hover:bg-slate-50 transition-all disabled:opacity-50 flex items-center gap-2 shadow-sm"
                >
                  <i class="fas fa-sync-alt text-slate-400" :class="{'animate-spin': loading}"></i>
                  <span>{{ loading ? 'Actualizando...' : 'Refrescar' }}</span>
                </button>
                
                <!-- Close Button -->
                <button 
                  @click="close"
                  class="w-9 h-9 flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
                >
                  <i class="fas fa-times text-lg"></i>
                </button>
              </div>
            </div>

            <!-- Health Bar Removed -->

            <!-- Tabs -->
            <div class="flex gap-6 mt-2">
              <button 
                @click="activeTab = 'live'"
                class="pb-3 text-sm font-bold border-b-2 transition-colors flex items-center gap-2"
                :class="activeTab === 'live' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'"
              >
                <i class="fas fa-satellite-dish"></i> Tráfico en Vivo
              </button>
              <button 
                @click="activeTab = 'blocked'; fetchBlockedIps()"
                class="pb-3 text-sm font-bold border-b-2 transition-colors flex items-center gap-2"
                :class="activeTab === 'blocked' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'"
              >
                <i class="fas fa-ban"></i> Reglas de Firewall (Bloqueados)
              </button>
              <button 
                @click="activeTab = 'scan'; fetchScanData()"
                class="pb-3 text-sm font-bold border-b-2 transition-colors flex items-center gap-2"
                :class="activeTab === 'scan' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'"
              >
                <i class="fas fa-radar"></i> Escáner de Vulnerabilidades
              </button>
              <button 
                @click="activeTab = 'whitelist'; fetchWhitelist()"
                class="pb-3 text-sm font-bold border-b-2 transition-colors flex items-center gap-2"
                :class="activeTab === 'whitelist' ? 'border-teal-600 text-teal-600' : 'border-transparent text-slate-400 hover:text-slate-600'"
              >
                <i class="fas fa-list-check"></i> Lista Blanca
              </button>
            </div>
          </div>

          <!-- TAB 1: LIVE TRAFFIC -->
          <div v-if="activeTab === 'live'" class="flex-1 flex flex-col bg-white overflow-hidden">
            
            <!-- Filters -->
            <div class="px-8 pt-4 pb-3 border-b border-slate-100 flex items-center justify-between shrink-0 bg-slate-50/50">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mr-2">Filtro:</span>
                <button @click="protocolFilter = 'ALL'" :class="protocolFilter === 'ALL' ? 'bg-slate-700 text-white border-transparent' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'" class="px-3 py-1 text-[10px] font-bold rounded transition-colors border shadow-sm">Todos</button>
                <button @click="protocolFilter = 'SIP'" :class="protocolFilter === 'SIP' ? 'bg-slate-700 text-white border-transparent' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'" class="px-3 py-1 text-[10px] font-bold rounded transition-colors border shadow-sm">SIP (Asterisk)</button>
                <button @click="protocolFilter = 'SSH'" :class="protocolFilter === 'SSH' ? 'bg-slate-700 text-white border-transparent' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'" class="px-3 py-1 text-[10px] font-bold rounded transition-colors border shadow-sm">SSH (Servidor)</button>
              </div>
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                Mostrando {{ filteredLogs.length }} eventos
              </div>
            </div>

            <div class="flex-1 overflow-auto px-8 pb-8 relative">
            <div v-if="loading && logs.length === 0" class="flex flex-col items-center justify-center py-20">
              <i class="fas fa-circle-notch fa-spin text-4xl text-slate-300 mb-4"></i>
              <p class="text-sm text-slate-500">Analizando registros en tiempo real...</p>
            </div>
            
            <div v-else-if="!loading && logs.length === 0" class="flex flex-col items-center justify-center py-20">
              <div class="w-16 h-16 rounded-full flex items-center justify-center mb-4 text-slate-300 border-2 border-slate-100">
                <i class="fas fa-check text-2xl"></i>
              </div>
              <h3 class="text-slate-800 font-bold text-sm mb-1">Red Limpia</h3>
            </div>

            <div v-else class="w-full mt-4">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Timestamp</th>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Protocolo</th>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Estado</th>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Objetivo</th>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">IPv4 Origen</th>
                    <th class="py-3 px-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Log Raw</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50/50">
                  <tr 
                    v-for="(log, index) in filteredLogs" 
                    :key="index"
                    @dblclick="promptBlockIp(log)"
                    class="transition-colors group cursor-pointer"
                    :class="log.is_breach ? 'bg-rose-50/30 hover:bg-rose-50/50' : 'hover:bg-slate-50/50'"
                    title="Doble clic para bloquear IP"
                  >
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span class="text-xs font-mono" :class="log.is_breach ? 'text-rose-600 font-semibold' : 'text-slate-500'">{{ log.timestamp }}</span>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span class="text-[9px] font-black px-2 py-0.5 rounded-sm uppercase tracking-widest" :class="log.protocol === 'SSH' ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-orange-50 text-orange-600 border border-orange-100'">
                        {{ log.protocol }}
                      </span>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span v-if="log.is_breach" class="inline-flex items-center text-[10px] font-bold tracking-wide uppercase text-rose-600 animate-pulse">
                        <i class="fas fa-engine-warning mr-1.5"></i> BRECHA CONFIRMADA
                      </span>
                      <span v-else class="inline-flex items-center text-[10px] font-bold tracking-wide uppercase" :class="log.status === 'FALLA' ? 'text-slate-400' : 'text-emerald-500'">
                        <i class="fas mr-1.5 text-[9px]" :class="log.status === 'FALLA' ? 'fa-shield-alt' : 'fa-check'"></i>
                        {{ log.status === 'FALLA' ? 'Bloqueado' : 'Autenticado' }}
                      </span>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <span class="text-xs font-semibold" :class="log.is_breach ? 'text-rose-700' : 'text-slate-700'">{{ log.extension || 'N/A' }}</span>
                    </td>
                    <td class="py-3 px-2 whitespace-nowrap">
                      <div class="flex items-center gap-2">
                        <div class="w-1.5 h-1.5 rounded-full" :class="log.is_breach ? 'bg-rose-500' : (log.status === 'FALLA' ? 'bg-slate-300' : 'bg-emerald-400')"></div>
                        <span class="text-xs font-mono font-medium" :class="log.is_breach ? 'text-rose-700' : 'text-slate-600'">{{ log.ip || 'Desconocida' }}</span>
                      </div>
                    </td>
                    <td class="py-3 px-2">
                      <div class="text-[11px] font-mono truncate max-w-2xl transition-colors" :class="log.is_breach ? 'text-rose-600/80' : 'text-slate-400 group-hover:text-slate-500'">
                        {{ log.raw }}
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

          <!-- TAB 2: BLOCKED IPS -->
          <div v-if="activeTab === 'blocked'" class="flex-1 overflow-auto bg-slate-50/50 px-8 pb-8">
            <div v-if="loading && blockedIps.length === 0" class="flex flex-col items-center justify-center py-20">
              <i class="fas fa-circle-notch fa-spin text-4xl text-slate-300 mb-4"></i>
            </div>
            
            <div v-else-if="!loading && blockedIps.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
              <div class="w-16 h-16 rounded-full flex items-center justify-center mb-4 text-emerald-400 bg-emerald-50 border-2 border-emerald-100">
                <i class="fas fa-shield-check text-2xl"></i>
              </div>
              <h3 class="text-slate-800 font-bold text-sm mb-1">Sin Bloqueos Activos</h3>
              <p class="text-xs text-slate-500">No hay ninguna IP bloqueada en Firewalld ni en Fail2Ban.</p>
            </div>

            <div v-else class="w-full mt-4 bg-white rounded-xl border border-slate-100 overflow-hidden shadow-sm">
              <table class="w-full text-left border-collapse">
                <thead class="bg-slate-50/50">
                  <tr>
                    <th class="py-3 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">IPv4 Bloqueada</th>
                    <th class="py-3 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Origen</th>
                    <th class="py-3 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Motivo del Bloqueo</th>
                    <th class="py-3 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100">Fecha/Hora</th>
                    <th class="py-3 px-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest border-b border-slate-100 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50">
                  <tr 
                    v-for="(item, index) in blockedIps" 
                    :key="index"
                    class="transition-colors hover:bg-slate-50/50 group"
                  >
                    <td class="py-3 px-4 whitespace-nowrap">
                      <div class="flex items-center gap-3">
                        <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 shadow-inner"
                             :class="item.source === 'FIREWALLD' ? 'bg-slate-700 text-white' : 'bg-rose-500 text-white'">
                          <i class="fas fa-ban text-[10px]"></i>
                        </div>
                        <span class="text-sm font-mono font-bold text-slate-800">{{ item.ip }}</span>
                      </div>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap">
                      <span class="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded"
                         :class="item.source === 'FIREWALLD' ? 'bg-slate-100 text-slate-600 border border-slate-200' : 'bg-rose-50 text-rose-600 border border-rose-100'">
                        <i class="fas mr-1" :class="item.source === 'FIREWALLD' ? 'fa-shield-alt' : 'fa-robot'"></i> {{ item.source }}
                      </span>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap">
                      <span class="text-xs text-slate-600 font-medium">{{ item.reason }}</span>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap">
                      <span class="text-xs font-mono text-slate-500">{{ item.timestamp }}</span>
                    </td>
                    <td class="py-3 px-4 whitespace-nowrap text-right">
                      <button 
                        @click="unblockIp(item.ip)"
                        class="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-400 hover:text-emerald-600 rounded-md text-xs font-bold transition-colors border border-slate-200 shadow-sm opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="Restaurar acceso"
                      >
                        <i class="fas fa-unlock mr-1"></i> Desbloquear
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- TAB 3: SCANNER -->
          <div v-if="activeTab === 'scan'" class="flex-1 overflow-auto bg-slate-50/30 px-8 pb-8">
            <div v-if="loading && !scanData" class="flex flex-col items-center justify-center py-20">
              <i class="fas fa-radar fa-spin text-4xl text-indigo-400 mb-4"></i>
              <p class="text-sm font-bold text-slate-500">Ejecutando auditoría profunda en el PBX...</p>
            </div>
            
            <div v-else-if="scanError" class="flex flex-col items-center justify-center py-20">
              <i class="fas fa-exclamation-triangle text-4xl text-rose-400 mb-4"></i>
              <h3 class="text-slate-800 font-bold text-sm mb-1">Error ejecutando escáner</h3>
              <p class="text-xs text-slate-500">{{ scanError }}</p>
              <button @click="fetchScanData()" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded font-bold text-xs hover:bg-indigo-700">Reintentar</button>
            </div>

            <div v-else-if="scanData" class="mt-6 space-y-8">
              
              <!-- Compromised Extensions (CRITICAL) -->
              <section v-if="scanData.compromised && scanData.compromised.length > 0">
                <h3 class="text-xs font-black text-rose-600 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <i class="fas fa-radiation"></i> Extensiones Comprometidas (Brecha Confirmada)
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div v-for="comp in scanData.compromised" :key="comp.extension" class="bg-rose-50 border-2 border-rose-200 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <p class="text-2xl font-black text-rose-700 font-mono">{{ comp.extension }}</p>
                      <p class="text-xs font-bold text-rose-500 mt-1">Hackeada tras {{ comp.failed_attempts_before_success }} intentos fallidos</p>
                    </div>
                    <div class="text-right">
                      <p class="text-[10px] font-bold text-rose-400 uppercase tracking-widest">IP Atacante</p>
                      <p class="text-sm font-bold text-rose-900 font-mono">{{ comp.attacker_ip }}</p>
                    </div>
                  </div>
                </div>
              </section>

              <!-- Under Attack (WARNING) -->
              <section v-if="scanData.under_attack && scanData.under_attack.length > 0">
                <h3 class="text-xs font-black text-orange-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <i class="fas fa-crosshairs"></i> Bajo Ataque Constante (Fuerza Bruta)
                </h3>
                <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <table class="w-full text-left">
                    <thead class="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th class="py-2 px-4 text-[10px] font-bold text-slate-500 uppercase">Extensión Objetivo</th>
                        <th class="py-2 px-4 text-[10px] font-bold text-slate-500 uppercase">Intentos Fallidos Acumulados</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr v-for="atk in scanData.under_attack" :key="atk.extension" class="hover:bg-orange-50/30 transition-colors">
                        <td class="py-3 px-4 font-mono font-bold text-slate-700">{{ atk.extension }}</td>
                        <td class="py-3 px-4">
                          <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-bold bg-orange-100 text-orange-700">
                            <i class="fas fa-fire"></i> {{ atk.failed_attempts }} bloqueados
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <!-- Weak Passwords (INFO) -->
              <section v-if="scanData.weak_passwords && scanData.weak_passwords.length > 0">
                <h3 class="text-xs font-black text-amber-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <i class="fas fa-key"></i> Vulnerabilidades de Contraseña
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div v-for="(wp, idx) in scanData.weak_passwords" :key="idx" class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-amber-300 transition-colors">
                    <div class="flex justify-between items-start mb-3">
                      <span class="text-xs font-bold px-2 py-1 bg-slate-100 text-slate-600 rounded-md uppercase tracking-wider font-mono">
                        PWD: {{ wp.password_mask }}
                      </span>
                      <span class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded-full flex items-center gap-1">
                        <i class="fas fa-exclamation-triangle"></i> {{ wp.reason }}
                      </span>
                    </div>
                    <div>
                      <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Extensiones Afectadas</p>
                      <div class="flex flex-wrap gap-1.5">
                        <span v-for="ext in wp.extensions" :key="ext" class="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-mono font-semibold">
                          {{ ext }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
              
              <div v-if="scanData && (!scanData.compromised?.length && !scanData.under_attack?.length && !scanData.weak_passwords?.length)" class="flex flex-col items-center justify-center py-10">
                <div class="w-16 h-16 rounded-full flex items-center justify-center mb-4 text-emerald-400 bg-emerald-50 border-2 border-emerald-100">
                  <i class="fas fa-shield-check text-2xl"></i>
                </div>
                <h3 class="text-slate-800 font-bold text-sm mb-1">Auditoría 100% Segura</h3>
                <p class="text-xs text-slate-500">No se detectaron vulnerabilidades críticas ni claves repetidas.</p>
              </div>

            </div>
          </div>

          <!-- TAB 4: WHITELIST -->
          <div v-if="activeTab === 'whitelist'" class="flex-1 overflow-auto bg-slate-50/50 px-8 pb-8 pt-6">
            <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200/60 overflow-hidden">
              <div class="p-6 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                <div>
                  <h3 class="text-slate-800 font-bold">IPs en Lista Blanca (IgnoreIP)</h3>
                  <p class="text-xs text-slate-500 mt-1">Estas direcciones están protegidas y NUNCA serán bloqueadas por Fail2Ban.</p>
                </div>
                <div class="w-12 h-12 rounded-full bg-teal-50 text-teal-500 flex items-center justify-center shrink-0">
                  <i class="fas fa-shield-check text-xl"></i>
                </div>
              </div>
              
              <div class="p-6">
                <!-- Add new IP form -->
                <div class="flex gap-3 mb-6 bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div class="relative flex-1">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <i class="fas fa-network-wired text-slate-400 text-xs"></i>
                    </div>
                    <input 
                      type="text" 
                      v-model="newWhitelistIp" 
                      placeholder="Ej. 200.1.2.3 o 192.168.10.0/24"
                      class="pl-9 w-full text-sm rounded-md border-slate-200 focus:border-teal-500 focus:ring-teal-500 font-mono shadow-sm"
                      @keyup.enter="addToWhitelist"
                    >
                  </div>
                  <button 
                    @click="addToWhitelist"
                    :disabled="addingToWhitelist || !newWhitelistIp.trim()"
                    class="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-md text-sm font-semibold transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <i class="fas" :class="addingToWhitelist ? 'fa-circle-notch fa-spin' : 'fa-plus'"></i>
                    {{ addingToWhitelist ? 'Añadiendo...' : 'Añadir IP' }}
                  </button>
                </div>

                <!-- IP List -->
                <div v-if="loading && whitelist.length === 0" class="flex justify-center py-10">
                  <i class="fas fa-circle-notch fa-spin text-3xl text-slate-300"></i>
                </div>
                <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  <div v-for="(ip, idx) in whitelist" :key="idx" class="flex items-center gap-2 p-2.5 rounded border border-slate-200 bg-white shadow-sm hover:shadow-md transition-all">
                    <i class="fas fa-check-circle text-teal-500 text-xs shrink-0"></i>
                    <span class="text-sm font-mono font-medium text-slate-700 truncate" :title="ip">{{ ip }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Custom Confirm Modal (Overlay sobre el Drawer) -->
        <div v-if="showConfirmModal" class="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-md">
          <div class="bg-white rounded-md shadow-2xl w-[450px] overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-slate-700">
            <div class="p-6">
              <div class="flex items-center gap-4 mb-4">
                <div class="w-12 h-12 rounded-sm bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
                  <i class="fas fa-radiation text-xl"></i>
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-900">Aniquilar Atacante</h3>
                  <p class="text-xs text-rose-600 font-bold uppercase tracking-wider">Acción Irreversible</p>
                </div>
              </div>
              
              <div class="mb-4 bg-rose-50 border border-rose-100 rounded-sm p-3 flex items-center justify-between">
                <span class="text-xs font-semibold text-rose-800 uppercase tracking-widest">Intentos Fallidos Detectados:</span>
                <span class="font-mono text-base font-black text-rose-600">{{ attemptsToBlock }}</span>
              </div>

              <p class="text-sm text-slate-600 leading-relaxed">
                ¿Estás seguro que deseas inyectar una regla <span class="font-mono bg-slate-100 px-1 rounded-sm text-slate-700 font-bold">DROP</span> en el firewall del PBX para destruir cualquier tráfico futuro de:
              </p>
              <div class="mt-4 p-4 bg-slate-900 rounded-sm flex items-center justify-center">
                <span class="font-mono text-xl font-bold text-emerald-400">{{ ipToBlock }}</span>
              </div>
            </div>
            <div class="bg-slate-50 px-6 py-4 border-t border-slate-200 flex justify-end gap-3">
              <button 
                @click="showConfirmModal = false"
                class="px-5 py-2.5 rounded-sm text-sm font-bold text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-colors border border-slate-300"
                :disabled="blockingIp"
              >
                Cancelar
              </button>
              <button 
                @click="executeBlockIp"
                class="px-5 py-2.5 rounded-sm text-sm font-bold bg-rose-600 text-white hover:bg-rose-700 transition-colors flex items-center gap-2 shadow-sm"
                :disabled="blockingIp"
              >
                <i v-if="blockingIp" class="fas fa-circle-notch fa-spin"></i>
                <i v-else class="fas fa-skull"></i>
                {{ blockingIp ? 'Ejecutando...' : 'Bloquear IP Permanente' }}
              </button>
            </div>
          </div>
        </div>

      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close']);

const activeTab = ref('live');
const logs = ref([]);
const blockedIps = ref([]);
const scanData = ref(null);
const scanError = ref(null);
const loading = ref(false);
const whitelist = ref([]);
const newWhitelistIp = ref('');
const addingToWhitelist = ref(false);

const protocolFilter = ref('ALL');

const filteredLogs = computed(() => {
  if (protocolFilter.value === 'ALL') return logs.value;
  return logs.value.filter(log => log.protocol === protocolFilter.value);
});

const fetchWhitelist = async () => {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/whitelist');
    if (!response.ok) throw new Error('Error de red');
    const data = await response.json();
    if (data.status === 'success') {
      whitelist.value = data.data || [];
    }
  } catch (error) {
    console.error('Error fetching whitelist:', error);
  } finally {
    loading.value = false;
  }
};

const addToWhitelist = async () => {
  if (!newWhitelistIp.value.trim()) return;
  addingToWhitelist.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/whitelist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: newWhitelistIp.value.trim() })
    });
    const data = await response.json();
    if (data.status === 'success') {
      newWhitelistIp.value = '';
      fetchWhitelist();
    } else {
      alert(data.message || 'Error al añadir IP');
    }
  } catch (error) {
    alert('Fallo de red al añadir IP');
  } finally {
    addingToWhitelist.value = false;
  }
};

const serviceStatus = ref({ firewalld: false, iptables: false, fail2ban: false });
const fetchingStatus = ref(false);

// Custom Confirm Modal State
const showConfirmModal = ref(false);
const ipToBlock = ref('');
const attemptsToBlock = ref(0);
const blockingIp = ref(false);

const close = () => {
  emit('close');
};

const fetchServiceStatus = async () => {
  fetchingStatus.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/status');
    if (!response.ok) throw new Error('Error');
    const data = await response.json();
    if (data.status === 'success') {
      serviceStatus.value = data.data;
    }
  } catch (e) {
    console.error('Error fetching security status:', e);
  } finally {
    fetchingStatus.value = false;
  }
};

const fetchLogs = async () => {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/auth-logs?limit=200');
    if (!response.ok) throw new Error('Error de red');
    const data = await response.json();
    if (data.status === 'success') {
      logs.value = data.data || [];
    }
  } catch (error) {
    console.error('Error fetching PBX security logs:', error);
  } finally {
    loading.value = false;
  }
};

const fetchBlockedIps = async () => {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/blocked-ips');
    if (!response.ok) throw new Error('Error de red');
    const data = await response.json();
    if (data.status === 'success') {
      blockedIps.value = data.data || [];
    }
  } catch (error) {
    console.error('Error fetching blocked IPs:', error);
  } finally {
    loading.value = false;
  }
};

const fetchScanData = async () => {
  loading.value = true;
  scanData.value = null;
  scanError.value = null;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/scan');
    if (!response.ok) throw new Error('Error de red');
    const data = await response.json();
    if (data.status === 'success') {
      scanData.value = data.data;
    } else {
      scanError.value = data.message || "Error desconocido en el servidor";
    }
  } catch (error) {
    console.error('Error fetching vulnerability scan:', error);
    scanError.value = error.message;
  } finally {
    loading.value = false;
  }
};

const promptBlockIp = (log) => {
  // Lógica de validación
  if (log.status === 'FALLA' || log.is_breach) {
    if (!log.ip || log.ip === 'Unknown') return;
    ipToBlock.value = log.ip;
    attemptsToBlock.value = log.attempts_count || 1;
    showConfirmModal.value = true;
  }
};

const executeBlockIp = async () => {
  if (!ipToBlock.value) return;
  blockingIp.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/block-ip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: ipToBlock.value })
    });
    
    if (response.ok) {
      showConfirmModal.value = false;
      // Refrescar ambas pestañas por si acaso
      fetchLogs();
      fetchBlockedIps();
    } else {
      alert('Error inyectando la regla de iptables.');
    }
  } catch (e) {
    alert('Fallo de red al intentar bloquear la IP.');
  } finally {
    blockingIp.value = false;
  }
};

const unblockIp = async (ip) => {
  try {
    const response = await fetch('http://localhost:8000/api/v1/pbx/recordings/security/unblock-ip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip: ip })
    });
    if (response.ok) {
      fetchBlockedIps();
    }
  } catch (error) {
    console.error('Error unblocking IP:', error);
  }
};

// Fetch data when modal opens
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    activeTab.value = 'live';
    fetchServiceStatus();
    fetchLogs();
  } else {
    showConfirmModal.value = false;
  }
});
</script>

<style scoped>
/* Transición del Drawer */
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}

.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}

/* Modal Animations */
.animate-in {
  animation: animate-in 0.2s ease-out;
}
@keyframes animate-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
