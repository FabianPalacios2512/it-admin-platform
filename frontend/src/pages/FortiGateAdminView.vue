<template>
  <div class="w-full flex flex-col gap-6">

    <!-- ============================================================ -->
    <!-- Header -->
    <!-- ============================================================ -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-semibold text-neutral-900">Centro de Administración y Respuesta Activa</h1>
          <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-slate-900 text-white rounded-lg">God Mode</span>
        </div>
        <p class="text-xs text-neutral-500 mt-0.5">NOC/SOC · Auditoría de tráfico en vivo y acciones correctivas directas sobre la API de FortiOS</p>
      </div>

      <div class="flex items-center gap-2">
        <div class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl shadow-[0_2px_8px_-3px_rgba(0,0,0,0.05)]">
          <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Firewall</span>
          <select
            v-if="fortigates.length && !manualIpMode"
            v-model="selectedFirewallIp"
            class="text-xs font-mono font-semibold text-neutral-800 bg-transparent outline-none max-w-[220px]"
          >
            <option v-for="fg in fortigates" :key="fg.hostid" :value="fg.ip">{{ fg.hostname }} · {{ fg.ip }}</option>
          </select>
          <input
            v-else
            v-model="selectedFirewallIp"
            type="text"
            placeholder="192.168.x.x"
            class="text-xs font-mono font-semibold text-neutral-800 bg-transparent outline-none w-28"
          />
          <button type="button" @click="manualIpMode = !manualIpMode" class="text-neutral-400 hover:text-neutral-700 transition-colors" title="Cambiar a IP manual">
            <i class="fas fa-pen text-[10px]"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- ============================================================ -->
    <!-- KPI strip -->
    <!-- ============================================================ -->
    <div class="bg-white rounded-xl shadow-[0_2px_8px_-3px_rgba(0,0,0,0.05)] grid grid-cols-1 md:grid-cols-5 divide-y md:divide-y-0 md:divide-x divide-slate-100 overflow-hidden">
      <button type="button" class="px-4 py-3.5 text-left hover:bg-slate-50/80 transition-colors" @click="setOpsTab('live')">
        <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Sesiones auditadas</div>
        <div class="mt-1.5 text-2xl font-semibold font-mono text-slate-900 leading-none">{{ activeSessionsCount }}</div>
        <div class="mt-1.5 text-[11px] text-slate-400">Top Talkers en la ventana actual</div>
      </button>
      <button type="button" class="px-4 py-3.5 text-left hover:bg-slate-50/80 transition-colors" @click="setOpsTab('live')">
        <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Ancho de banda total</div>
        <div class="mt-1.5 text-2xl font-semibold font-mono text-slate-900 leading-none">{{ formatBytes(totalBandwidth) }}</div>
        <div class="mt-1.5 text-[11px] text-slate-400">Acumulado TX + RX de la sesión</div>
      </button>
      <button type="button" class="px-4 py-3.5 text-left hover:bg-slate-50/80 transition-colors" @click="setOpsTab('controls')">
        <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Páginas bloqueadas</div>
        <div class="mt-1.5 text-2xl font-semibold font-mono leading-none" :class="destinationBlocks.length ? 'text-amber-700' : 'text-slate-900'">{{ destinationBlocks.length }}</div>
        <div class="mt-1.5 text-[11px] text-slate-400">{{ destinationBlocks.length ? 'Clic para ver y revertir' : 'Ningún destino cortado a mano' }}</div>
      </button>
      <button type="button" class="px-4 py-3.5 text-left hover:bg-slate-50/80 transition-colors" @click="setOpsTab('quarantine')">
        <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">En cuarentena</div>
        <div class="mt-1.5 text-2xl font-semibold font-mono leading-none" :class="quarantinedCount > 0 ? 'text-red-600' : 'text-slate-900'">{{ quarantinedCount }}</div>
        <div class="mt-1.5 text-[11px] text-slate-400">{{ quarantinedCount ? 'Clic para habilitar de nuevo' : 'Hosts aislados en este firewall' }}</div>
      </button>
      <button type="button" class="px-4 py-3.5 text-left hover:bg-slate-50/80 transition-colors" @click="setOpsTab('shaping')">
        <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Con Traffic Shaping</div>
        <div class="mt-1.5 text-2xl font-semibold font-mono leading-none" :class="shapedCount > 0 ? 'text-orange-600' : 'text-slate-900'">{{ shapedCount }}</div>
        <div class="mt-1.5 text-[11px] text-slate-400">Perfiles de ancho de banda activos</div>
      </button>
    </div>

    <div class="flex flex-wrap gap-1 border-b border-slate-200/70">
      <button
        v-for="tab in opsTabs"
        :key="tab.id"
        type="button"
        class="px-3 py-2.5 text-[11px] uppercase tracking-wide inline-flex items-center gap-2 border-b-2 transition-colors"
        :class="opsTab === tab.id ? 'border-blue-600 text-slate-900 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-800'"
        @click="setOpsTab(tab.id)"
      >
        <i :class="tab.icon" class="text-[10px]"></i>
        {{ tab.label }}
        <span
          v-if="tab.count() > 0"
          class="min-w-[16px] h-4 px-1 rounded text-[10px] font-mono leading-4 text-center"
          :class="opsTab === tab.id ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'"
        >{{ tab.count() }}</span>
      </button>
    </div>

    <!-- ============================================================ -->
    <!-- Top Talkers -->
    <!-- ============================================================ -->
    <div v-show="opsTab === 'live'" class="bg-white rounded-xl shadow-[0_2px_8px_-3px_rgba(0,0,0,0.05)] overflow-hidden">
      <div class="px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-xs font-semibold text-neutral-800 uppercase tracking-wide flex items-center gap-2">
            <i class="fas fa-list-check text-neutral-500"></i> Top Talkers · Auditoría en vivo
          </h2>
          <p class="text-[11px] text-neutral-500 mt-0.5">
            Clic en una fila para ver el detalle: página, bytes, hora de inicio y consumo.
            <span v-if="auditSource"> · fuente {{ auditSource }}</span>
            <span v-if="auditSessionCount != null"> · {{ auditSessionCount }} filas</span>
          </p>
        </div>

        <div class="flex items-center gap-2">
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-2.5 text-neutral-400">
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar IP, usuario, host o app…"
              class="pl-8 pr-3 py-1.5 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600 w-56 bg-slate-50 transition-colors"
            />
          </div>
          <button
            type="button"
            @click="loadLiveData(false)"
            :disabled="isLoadingAudit"
            class="px-3 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50 rounded-lg inline-flex items-center gap-1.5"
          >
            <i class="fas fa-sync-alt text-[10px]" :class="isLoadingAudit ? 'fa-spin' : ''"></i>
            Actualizar
          </button>
          <button
            type="button"
            @click="toggleLive"
            class="px-3 py-1.5 text-[11px] font-semibold rounded-lg inline-flex items-center gap-1.5 transition-colors"
            :class="isLive ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-100'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="isLive ? 'bg-white animate-pulse' : 'bg-neutral-400'"></span>
            {{ isLive ? 'En vivo' : 'Pausado' }}
          </button>
        </div>
      </div>

      <div class="overflow-x-auto w-full">
        <table class="w-full text-left border-collapse whitespace-nowrap">
          <thead class="border-b border-slate-100">
            <tr>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Origen</th>
              <th class="py-2.5 px-1 w-6"></th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Destino</th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Aplicación</th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">TX ↑</th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">RX ↓</th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-right">Sesión</th>
              <th class="py-2.5 px-3 text-[10px] font-semibold text-neutral-500 uppercase tracking-wider text-center">Estado</th>
              <th class="py-2.5 px-3 w-10"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoadingAudit && !talkers.length">
              <td colspan="9" class="py-12 text-center text-neutral-400">
                <i class="fas fa-circle-notch fa-spin mb-2 text-lg"></i>
                <p class="text-xs">Consultando sesiones reales del FortiGate…</p>
                <p class="text-[11px] mt-1">La primera lectura tarda unos segundos; luego se sirve desde caché.</p>
              </td>
            </tr>
            <tr v-else-if="auditError && !talkers.length">
              <td colspan="9" class="py-10 text-center">
                <p class="text-xs text-red-600 font-medium">{{ auditError }}</p>
              </td>
            </tr>
            <tr
              v-for="row in filteredTalkers"
              :key="row.id"
              class="border-b border-slate-100 last:border-0 hover:bg-slate-50/80 transition-colors cursor-pointer"
              :class="row.status === 'closed' ? 'opacity-40' : ''"
              @click="openDetail(row)"
            >
              <!-- Origen -->
              <td class="py-2 px-3 align-top">
                <div class="font-mono text-sm font-semibold text-neutral-900">{{ row.srcIp }}</div>
                <div class="text-[11px] text-neutral-500 truncate max-w-[170px]">{{ row.srcUser || row.srcHost }}</div>
              </td>
              <td class="py-2 px-1 text-center text-neutral-300 align-top pt-3">
                <i class="fas fa-arrow-right text-[10px]"></i>
              </td>
              <!-- Destino -->
              <td class="py-2 px-3 align-top">
                <div class="font-mono text-sm text-neutral-800">{{ row.dstIp }}</div>
                <div class="text-[11px] text-neutral-500 truncate max-w-[190px]">{{ row.dstHost }}</div>
              </td>
              <!-- Aplicación -->
              <td class="py-2 px-3 align-top">
                <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-[11px] font-semibold" :class="appMeta(row.app).badge">
                  <i :class="appMeta(row.app).icon" class="text-[11px]"></i>
                  {{ row.app }}
                </span>
                <div v-if="row.risk !== 'none'" class="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold" :class="row.risk === 'high' ? 'text-red-600' : 'text-amber-600'">
                  <span class="w-1.5 h-1.5 rounded-full animate-pulse" :class="row.risk === 'high' ? 'bg-red-500' : 'bg-amber-500'"></span>
                  {{ row.risk === 'high' ? 'Riesgo alto' : 'Riesgo medio' }}
                </div>
              </td>
              <!-- TX / RX -->
              <td class="py-2 px-3 text-right font-mono text-sm text-neutral-600 align-top">{{ formatBytes(row.txBytes) }}</td>
              <td class="py-2 px-3 text-right font-mono text-sm font-semibold text-neutral-900 align-top">{{ formatBytes(row.rxBytes) }}</td>
              <!-- Duración -->
              <td class="py-2 px-3 text-right font-mono text-xs text-neutral-500 align-top">{{ formatDuration(row.sessionSeconds) }}</td>
              <!-- Estado -->
              <td class="py-2 px-3 text-center align-top">
                <span v-if="row.status === 'closed'" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-slate-100 text-slate-500 rounded-lg">Cerrada</span>
                <span v-else-if="row.blocked" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-red-50 text-red-600 rounded-lg">Cuarentena</span>
                <span v-else-if="row.destBlocked" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-amber-50 text-amber-700 rounded-lg">{{ row.destBlockedLabel || 'Página bloqueada' }}</span>
                <span v-else-if="row.appBlocked" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-amber-50 text-amber-600 rounded-lg">App bloqueada</span>
                <span v-else-if="row.shaped" class="px-2 py-0.5 text-[10px] font-semibold uppercase bg-orange-50 text-orange-600 rounded-lg">{{ row.shaperLabel }}</span>
                <span v-else class="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase text-emerald-700">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Activa
                </span>
              </td>
              <!-- Acciones -->
              <td class="py-2 px-3 text-right align-top">
                <button
                  type="button"
                  :disabled="row.status === 'closed'"
                  @click.stop="openMenu($event, row)"
                  class="actions-trigger px-2.5 py-1.5 text-[11px] font-medium text-slate-600 bg-transparent hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg inline-flex items-center gap-1.5 transition-colors"
                >
                  Acciones <i class="fas fa-chevron-down text-[9px]"></i>
                </button>
              </td>
            </tr>
            <tr v-if="!isLoadingAudit && !auditError && !filteredTalkers.length">
              <td colspan="9" class="py-10 text-center text-sm text-neutral-400">
                <i class="fas fa-search text-2xl mb-2 opacity-20 block"></i>
                {{ searchQuery
                  ? 'Sin sesiones que coincidan con la búsqueda.'
                  : 'La API no devolvió sesiones ni FortiView para este firewall. Si hay PCs generando tráfico, el token suele no tener permiso de lectura de sesiones (fwgrp).' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <SessionDetailDrawer
      :session="detailRow"
      :session-data="detail"
      :loading="detailLoading"
      :error="detailError"
      :chart-points="localChartHistory"
      :successor="successorRow"
      :processing="isProcessingAction"
      :action-note="detailActionNote"
      :confirm="detailConfirm"
      :shape-index="detailShapeIndex"
      :shaper-profiles="limitSelectOptions"
      :duration-seconds="liveDuration"
      :block-preview="blockPreview"
      @close="closeDetail"
      @update:confirm="detailConfirm = $event"
      @update:shape-index="detailShapeIndex = $event"
      @confirm-action="confirmDetailAction"
      @request-block="requestDestinationBlock"
      @open-successor="openDetail"
    />

    <!-- ============================================================ -->
    <!-- Hosts · inventario pasivo -->
    <!-- ============================================================ -->
    <div v-show="opsTab === 'hosts'">
      <HostsInventoryPanel
        ref="hostsPanelRef"
        :firewall-ip="selectedFirewallIp"
        @view-traffic="viewHostTraffic"
        @isolate="isolateFromInventory"
      />
    </div>

    <!-- ============================================================ -->
    <!-- Controles humanos: páginas bloqueadas + bitácora -->
    <!-- ============================================================ -->
    <div v-show="opsTab === 'controls'" ref="controlsPanelRef" class="bg-white rounded-xl shadow-[0_2px_8px_-3px_rgba(0,0,0,0.05)] overflow-hidden">
      <div class="px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="text-xs font-semibold text-neutral-800 uppercase tracking-wide flex items-center gap-2">
            <i class="fas fa-user-shield" :class="destinationBlocks.length ? 'text-amber-700' : 'text-neutral-500'"></i>
            Controles activos · decisión humana
          </h2>
          <p class="text-[11px] text-neutral-500 mt-0.5">
            Nada se bloquea solo. Si el gerente no entra a YouTube y su compañero sí, la causa está aquí: quién, a qué IP y a qué página.
          </p>
        </div>
        <button
          type="button"
          @click="loadControls"
          class="px-3 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 rounded-lg inline-flex items-center gap-1.5"
        >
          <i class="fas fa-sync-alt text-[10px]"></i>
          Actualizar
        </button>
      </div>

      <div class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Páginas / destinos bloqueados ahora en este FortiGate</div>
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Equipo</th>
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Página / servicio</th>
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Dominios cubiertos</th>
            <th class="px-3 py-2 w-28"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in destinationBlocks" :key="`${row.srcip}-${row.dest_name}`" class="border-b border-slate-100 last:border-0">
            <td class="px-3 py-2">
              <div class="font-mono text-xs font-semibold text-neutral-900">{{ row.srcip }}</div>
              <div class="text-[11px] text-neutral-500">{{ destBlockHostLabel(row.srcip) }}</div>
            </td>
            <td class="px-3 py-2 text-xs font-semibold text-neutral-800">{{ row.dest_label }}</td>
            <td class="px-3 py-2 text-[11px] font-mono text-neutral-500">{{ row.domains_label }}</td>
            <td class="px-3 py-2 text-right">
              <button
                type="button"
                :disabled="revertingKey === `${row.srcip}|${row.dest_name}`"
                @click="revertDestinationBlock(row)"
                class="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 bg-transparent hover:bg-emerald-50 disabled:opacity-50 rounded-lg inline-flex items-center gap-1.5"
              >
                <i v-if="revertingKey === `${row.srcip}|${row.dest_name}`" class="fas fa-circle-notch fa-spin"></i>
                Revertir
              </button>
            </td>
          </tr>
          <tr v-if="!destinationBlocks.length">
            <td colspan="4" class="px-3 py-6 text-center text-xs text-neutral-400">No hay páginas bloqueadas a mano en este firewall.</td>
          </tr>
        </tbody>
      </table>

      <div class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        Bitácora de operadores (quién pulsó qué)
      </div>
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Cuándo</th>
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Operador</th>
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Acción</th>
            <th class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Objetivo</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in nocAuditForFirewall" :key="log.id" class="border-b border-slate-100 last:border-0">
            <td class="px-3 py-2 text-[11px] text-neutral-500 whitespace-nowrap">{{ formatAuditWhen(log.timestamp) }}</td>
            <td class="px-3 py-2 text-xs font-semibold text-neutral-800">{{ log.username }}</td>
            <td class="px-3 py-2 text-xs text-neutral-700">{{ log.action }}</td>
            <td class="px-3 py-2 text-[11px] font-mono text-neutral-500">{{ log.target }}</td>
          </tr>
          <tr v-if="!nocAuditForFirewall.length">
            <td colspan="4" class="px-3 py-5 text-center text-xs text-neutral-400">
              Aún no hay bitácora en esta plataforma. Lo que sí está aplicado se ve en la tabla de arriba (lo lee el FortiGate).
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ============================================================ -->
    <!-- Cuarentena · Control de Aislamiento -->
    <!-- ============================================================ -->
    <div v-show="opsTab === 'quarantine'" ref="quarantinePanelRef">
      <div class="flex justify-between items-center mb-6 gap-3">
        <div>
          <h2 class="text-sm font-semibold text-slate-900">Control de Aislamiento de Red</h2>
          <p class="text-[11px] text-slate-500 mt-0.5">Aísla un host de toda la red y libéralo cuando el incidente cierre.</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            @click="loadBanned"
            class="px-3 py-2 text-[12px] font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Actualizar
          </button>
          <button
            type="button"
            @click="openIsolateDrawer('quarantine')"
            class="bg-red-600 hover:bg-red-700 text-white rounded-lg px-4 py-2 font-medium"
          >
            + Aislar Equipo
          </button>
        </div>
      </div>

      <div class="bg-white rounded-xl overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-slate-100">
              <th class="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">IP / Equipo</th>
              <th class="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Motivo</th>
              <th class="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Tiempo restante</th>
              <th class="px-4 py-3 w-28"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in quarantineRows" :key="entry.ip" class="border-b border-slate-100 last:border-0">
              <td class="px-4 py-3">
                <div class="font-mono font-semibold text-sm text-slate-900">{{ entry.ip }}</div>
                <div class="text-[11px] text-slate-500">{{ entry.hostname }}{{ entry.kind === 'mac' ? ' · capa 2' : '' }}</div>
              </td>
              <td class="px-4 py-3 text-sm text-slate-500">{{ entry.reason }}</td>
              <td class="px-4 py-3">
                <span class="inline-flex px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-orange-50 text-orange-700">
                  {{ entry.remaining }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  type="button"
                  :disabled="releasingIp === entry.ip"
                  @click="entry.kind === 'mac' ? releaseMacBlock(entry) : requestRelease(entry.ip)"
                  class="px-2.5 py-1.5 text-[12px] font-medium text-slate-600 hover:bg-slate-100 rounded-lg disabled:opacity-50"
                >
                  {{ releasingIp === entry.ip ? 'Liberando…' : 'Liberar' }}
                </button>
              </td>
            </tr>
            <tr v-if="!quarantineRows.length">
              <td colspan="4" class="px-4 py-16 text-center">
                <i class="fas fa-shield-halved text-3xl text-slate-200 mb-3 block"></i>
                <p class="text-sm font-medium text-slate-500">Red segura. No hay equipos en cuarentena actualmente</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <IsolateHostDrawer
      :open="isolateDrawerOpen"
      :default-action="isolateDrawerAction"
      :default-firewall-ip="selectedFirewallIp"
      :live-hosts="uniqueSourceHosts"
      :seed-host="isolateSeedHost"
      :processing="isolating"
      @close="closeIsolateDrawer"
      @isolate="executeIsolation"
    />

    <!-- ============================================================ -->
    <!-- Traffic Shaping Panel -->
    <!-- ============================================================ -->
    <div v-show="opsTab === 'shaping'" class="grid grid-cols-1 xl:grid-cols-12 gap-5">
      <aside class="xl:col-span-3">
        <div class="bg-white rounded-xl border border-slate-200/80 p-3.5">
          <div class="flex items-center justify-between gap-2">
            <h2 class="text-[13px] font-semibold text-slate-900">Shaper</h2>
            <div class="flex rounded-md bg-slate-100 p-0.5">
              <button
                type="button"
                class="px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide"
                :class="shapeDirection === 'rx' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                @click="shapeDirection = 'rx'"
              >RX</button>
              <button
                type="button"
                class="px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide"
                :class="shapeDirection === 'symmetric' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                @click="shapeDirection = 'symmetric'"
              >TX/RX</button>
            </div>
          </div>

          <select
            v-model="quickAssignIp"
            class="mt-3 w-full border-0 border-b border-slate-200 bg-transparent pb-1.5 text-xs font-mono text-slate-800 outline-none focus:border-slate-400"
          >
            <option value="" disabled>Host / IP…</option>
            <option v-for="host in uniqueSourceHosts" :key="host.ip" :value="host.ip">{{ host.ip }} · {{ host.label }}</option>
          </select>

          <div class="mt-3 flex flex-wrap gap-1">
            <button
              v-for="preset in shapePresets"
              :key="preset.id"
              type="button"
              class="px-2 py-0.5 rounded-full text-[11px] font-medium transition-colors"
              :class="shapePreset === preset.id
                ? 'bg-orange-50 text-orange-700 ring-1 ring-orange-400'
                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'"
              @click="shapePreset = preset.id"
            >
              {{ preset.label }}
            </button>
          </div>
          <div v-if="shapePreset === 'manual'" class="mt-2 flex items-center gap-1.5">
            <input
              v-model.number="shapeManualMbps"
              type="number"
              min="1"
              max="10000"
              class="w-20 border-0 border-b border-slate-200 bg-transparent py-0.5 text-xs font-mono text-slate-800 outline-none focus:border-orange-400"
            />
            <span class="text-[10px] text-slate-400">Mbps</span>
          </div>

          <button
            type="button"
            :disabled="!canApplyShaping || isProcessingAction"
            class="mt-3.5 text-[12px] font-semibold text-orange-700 hover:text-orange-800 disabled:opacity-40 disabled:cursor-not-allowed"
            @click="quickApplyShaping"
          >
            {{ isProcessingAction ? 'Aplicando…' : `Aplicar ${shapeLimitPreview}` }}
          </button>
        </div>
      </aside>

      <section class="xl:col-span-9">
        <div class="bg-white rounded-xl border border-slate-200/80 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between gap-3">
            <h2 class="text-[13px] font-semibold text-slate-900">Perfiles activos</h2>
            <span class="text-[11px] text-slate-400">{{ shapedCount ? `${shapedCount} activas` : 'Sin restricciones' }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-slate-100">
                  <th class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">IP / Equipo</th>
                  <th class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Límite aplicado</th>
                  <th class="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Origen</th>
                  <th class="px-4 py-2 w-24"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in shapingAssignments" :key="a.policyName || a.ip" class="border-b border-slate-50 last:border-0">
                  <td class="px-4 py-2.5">
                    <div class="font-mono font-medium text-[13px] text-slate-900">{{ a.ip }}</div>
                    <div class="text-[11px] text-slate-500">{{ destBlockHostLabel(a.ip) }}{{ a.destLabel && a.scope !== 'host' ? ` · ${a.destLabel}` : '' }}</div>
                  </td>
                  <td class="px-4 py-2.5">
                    <span class="bg-orange-50 text-orange-700 px-2 py-0.5 rounded text-[11px] font-semibold">{{ shapeAssignmentBadge(a) }}</span>
                  </td>
                  <td class="px-4 py-2.5 text-[12px] text-slate-400">{{ shapeOriginLabel(a) }}</td>
                  <td class="px-4 py-2.5 text-right">
                    <button
                      type="button"
                      class="text-[11px] font-medium text-red-600 hover:bg-red-50 px-2 py-0.5 rounded"
                      @click="removeShaping(a)"
                    >
                      Revocar
                    </button>
                  </td>
                </tr>
                <tr v-if="!shapingAssignments.length">
                  <td colspan="4" class="px-4 py-10 text-center text-[13px] text-slate-400">
                    Tráfico Normalizado. No hay restricciones de ancho de banda activas.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <!-- ============================================================ -->
    <!-- Floating Dropdown Menu (Acciones Tácticas · God Mode) -->
    <!-- ============================================================ -->
    <div
      v-if="openMenuFor"
      ref="menuRef"
      class="fixed z-[90] w-64 bg-white rounded-xl shadow-[0_8px_24px_-6px_rgba(0,0,0,0.18)] py-1.5"
      :style="{ top: menuPosition.top + 'px', left: menuPosition.left + 'px' }"
    >
      <div class="px-3 py-1.5 mb-1 border-b border-neutral-100">
        <div class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Acciones tácticas</div>
        <div class="font-mono text-[11px] text-neutral-700">{{ activeMenuRow?.srcIp }} → {{ activeMenuRow?.dstIp }}</div>
      </div>

      <button type="button" @click="requestAction('kill', activeMenuRow)" class="w-full flex items-center gap-2.5 px-3 py-2 text-[12.5px] font-medium text-red-600 hover:bg-red-50 transition-colors">
        <i class="fas fa-power-off text-[11px]"></i> Kill Session
      </button>
      <button type="button" @click="requestAction('shape', activeMenuRow)" class="w-full flex items-center gap-2.5 px-3 py-2 text-[12.5px] font-medium text-orange-600 hover:bg-orange-50 transition-colors">
        <i class="fas fa-gauge-high text-[11px]"></i> Traffic Shaping
      </button>
      <button type="button" @click="requestAction('block', activeMenuRow)" class="w-full flex items-center gap-2.5 px-3 py-2 text-[12.5px] font-medium text-amber-600 hover:bg-amber-50 transition-colors">
        <i class="fas fa-ban text-[11px]"></i> Block Application
      </button>
      <div class="my-1 border-t border-neutral-100"></div>
      <button
        v-if="!activeMenuRow?.blocked"
        type="button"
        @click="requestAction('quarantine', activeMenuRow)"
        class="w-full flex items-center gap-2.5 px-3 py-2 text-[12.5px] font-semibold text-white bg-red-600 hover:bg-red-700 transition-colors"
      >
        <i class="fas fa-shield-halved text-[11px]"></i> Quarantine Host
      </button>
      <button
        v-else
        type="button"
        @click="requestAction('unquarantine', activeMenuRow)"
        class="w-full flex items-center gap-2.5 px-3 py-2 text-[12.5px] font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 transition-colors"
      >
        <i class="fas fa-unlock text-[11px]"></i> Habilitar de nuevo
      </button>
    </div>

    <!-- ============================================================ -->
    <!-- Modales de confirmación (acciones críticas) -->
    <!-- ============================================================ -->
    <transition name="fade">
      <div v-if="pendingAction" class="fixed inset-0 bg-slate-900/50 z-[120] flex items-center justify-center p-4" @click.self="cancelAction">
        <div class="bg-white w-full max-w-md rounded-md shadow-2xl overflow-hidden border border-neutral-200">

          <!-- Kill Session -->
          <template v-if="pendingAction.type === 'kill'">
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                <i class="fas fa-power-off"></i>
              </div>
              <div>
                <h3 class="text-sm font-bold text-neutral-900">Kill Session</h3>
                <p class="text-[11px] text-neutral-500">Terminar la conexión TCP/UDP inmediatamente</p>
              </div>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div class="bg-neutral-50 border border-neutral-200 rounded-sm p-3 font-mono text-xs text-neutral-700 flex items-center justify-between">
                <span>{{ pendingAction.row.srcIp }}</span>
                <i class="fas fa-arrow-right text-neutral-400"></i>
                <span>{{ pendingAction.row.dstIp }}</span>
              </div>
              <div class="grid grid-cols-2 gap-2 text-[11px] text-neutral-500">
                <div>Aplicación: <span class="font-semibold text-neutral-800">{{ pendingAction.row.app }}</span></div>
                <div>Duración: <span class="font-mono text-neutral-800">{{ formatDuration(pendingAction.row.sessionSeconds) }}</span></div>
              </div>
              <p class="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-sm p-2">
                <i class="fas fa-triangle-exclamation mr-1"></i>
                Solo cierra la sesión activa; el cliente puede reconectar de inmediato. Para bloquear al host usa "Quarantine Host".
              </p>
            </div>
            <div class="px-5 py-3.5 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
              <button type="button" @click="cancelAction" class="px-3.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 rounded-sm transition-colors">Cancelar</button>
              <button type="button" @click="confirmKill" :disabled="isProcessingAction" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-sm inline-flex items-center gap-2 transition-colors">
                <i v-if="isProcessingAction" class="fas fa-circle-notch fa-spin"></i>
                Terminar sesión
              </button>
            </div>
          </template>

          <!-- Traffic Shaping -->
          <template v-else-if="pendingAction.type === 'shape'">
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-orange-50 text-orange-600 flex items-center justify-center shrink-0">
                <i class="fas fa-gauge-high"></i>
              </div>
              <div>
                <h3 class="text-sm font-bold text-neutral-900">Traffic Shaping</h3>
                <p class="text-[11px] text-neutral-500">Limitar el ancho de banda de este host</p>
              </div>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div class="bg-neutral-50 border border-neutral-200 rounded-sm p-3 flex items-center justify-between">
                <span class="font-mono text-xs text-neutral-800">{{ pendingAction.row.srcIp }}</span>
                <span class="text-[11px] text-neutral-500">{{ pendingAction.row.srcUser || pendingAction.row.srcHost }}</span>
              </div>
              <input type="range" min="0" :max="UNLIMITED_INDEX" step="1" v-model.number="pendingShapeIndex" class="w-full accent-orange-500" />
              <div class="flex justify-between text-[8px] text-neutral-400 font-mono px-0.5 gap-0.5">
                <span v-for="(mbps, idx) in LIMIT_TICKS" :key="mbps" :class="pendingShapeIndex === idx ? 'text-orange-600 font-bold' : ''">{{ formatLimitTick(mbps) }}</span>
                <span :class="pendingShapeIndex === UNLIMITED_INDEX ? 'text-orange-600 font-bold' : ''">Libre</span>
              </div>
              <div class="flex items-center justify-between px-3 py-2 rounded-sm border" :class="isUnlimitedIndex(pendingShapeIndex) ? 'bg-white border-neutral-200' : 'bg-orange-50 border-orange-200'">
                <span class="text-xs font-semibold text-neutral-800">{{ formatLimitLabel(limitMbpsAt(pendingShapeIndex)) }}</span>
                <span class="text-[11px] text-neutral-500">{{ isUnlimitedIndex(pendingShapeIndex) ? 'No aplica tope. Si ya hay uno, quítalo.' : 'Tope de bajada y subida' }}</span>
              </div>
            </div>
            <div class="px-5 py-3.5 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
              <button type="button" @click="cancelAction" class="px-3.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 rounded-sm transition-colors">Cancelar</button>
              <button type="button" @click="confirmShape" :disabled="isProcessingAction || isUnlimitedIndex(pendingShapeIndex)" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded-sm inline-flex items-center gap-2 transition-colors">
                <i v-if="isProcessingAction" class="fas fa-circle-notch fa-spin"></i>
                Aplicar límite
              </button>
            </div>
          </template>

          <!-- Block Application -->
          <template v-else-if="pendingAction.type === 'block'">
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
                <i class="fas fa-ban"></i>
              </div>
              <div>
                <h3 class="text-sm font-bold text-neutral-900">Block Application</h3>
                <p class="text-[11px] text-neutral-500">Añadir la firma a la lista negra del perfil de aplicaciones</p>
              </div>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div class="bg-neutral-50 border border-neutral-200 rounded-sm p-3 flex items-center gap-2.5">
                <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-[11px] font-semibold" :class="appMeta(pendingAction.row.app).badge">
                  <i :class="appMeta(pendingAction.row.app).icon" class="text-[11px]"></i>
                  {{ pendingAction.row.app }}
                </span>
                <span class="text-[11px] text-neutral-500">{{ sessionsUsingApp(pendingAction.row.app) }} sesión(es) activa(s) con esta firma</span>
              </div>
              <div>
                <label class="block text-[11px] text-neutral-500 mb-1">Perfil de Application Control</label>
                <input v-model="blockProfileName" type="text" placeholder="default" class="w-full text-xs font-mono border border-neutral-300 rounded-sm px-2.5 py-1.5 text-neutral-800 outline-none focus:border-amber-500" />
              </div>
              <p class="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-sm p-2">
                <i class="fas fa-triangle-exclamation mr-1"></i>
                Esto bloquea "{{ pendingAction.row.app }}" para <strong>todos</strong> los hosts que usen este perfil, no solo el host seleccionado.
              </p>
            </div>
            <div class="px-5 py-3.5 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
              <button type="button" @click="cancelAction" class="px-3.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 rounded-sm transition-colors">Cancelar</button>
              <button type="button" @click="confirmBlockApp" :disabled="isProcessingAction || !blockProfileName" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-sm inline-flex items-center gap-2 transition-colors">
                <i v-if="isProcessingAction" class="fas fa-circle-notch fa-spin"></i>
                Bloquear aplicación
              </button>
            </div>
          </template>

          <!-- Unquarantine Host -->
          <template v-else-if="pendingAction.type === 'unquarantine'">
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
                <i class="fas fa-unlock"></i>
              </div>
              <div>
                <h3 class="text-sm font-bold text-neutral-900">Habilitar de nuevo</h3>
                <p class="text-[11px] text-neutral-500">Sacar este equipo de la cuarentena del FortiGate</p>
              </div>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div class="bg-neutral-50 border border-neutral-200 rounded-sm p-3 flex items-center justify-between">
                <span class="font-mono text-xs font-semibold text-neutral-900">{{ pendingAction.row.srcIp || pendingAction.row.ip }}</span>
                <span class="text-[11px] text-neutral-500">{{ pendingAction.row.srcUser || pendingAction.row.srcHost || pendingAction.row.hostname }}</span>
              </div>
              <p class="text-[11px] text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-sm p-2">
                El equipo vuelve a tener salida a red por las políticas normales. No se tocan límites ni bloqueos de página que hayas aplicado aparte.
              </p>
            </div>
            <div class="px-5 py-3.5 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
              <button type="button" @click="cancelAction" class="px-3.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 rounded-sm transition-colors">Cancelar</button>
              <button type="button" @click="confirmUnquarantine" :disabled="isProcessingAction" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-sm inline-flex items-center gap-2 transition-colors">
                <i v-if="isProcessingAction" class="fas fa-circle-notch fa-spin"></i>
                Habilitar ahora
              </button>
            </div>
          </template>

          <!-- Quarantine Host -->
          <template v-else-if="pendingAction.type === 'quarantine'">
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-red-50 text-red-600 flex items-center justify-center shrink-0">
                <i class="fas fa-shield-halved"></i>
              </div>
              <div>
                <h3 class="text-sm font-bold text-neutral-900">Quarantine Host</h3>
                <p class="text-[11px] text-neutral-500">Aislar completamente esta IP (sin salida a red)</p>
              </div>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div class="bg-neutral-50 border border-neutral-200 rounded-sm p-3 flex items-center justify-between">
                <span class="font-mono text-xs font-semibold text-neutral-900">{{ pendingAction.row.srcIp }}</span>
                <span class="text-[11px] text-neutral-500">{{ pendingAction.row.srcUser || pendingAction.row.srcHost }}</span>
              </div>
              <div>
                <div class="text-[11px] text-neutral-500 mb-1.5">Duración de la cuarentena</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="opt in quarantineDurations"
                    :key="opt.seconds"
                    type="button"
                    @click="quarantineDuration = opt.seconds"
                    class="px-2.5 py-1 text-[11px] font-medium border rounded-sm transition-colors"
                    :class="quarantineDuration === opt.seconds ? 'bg-red-600 text-white border-red-700' : 'bg-white border-neutral-300 text-neutral-700 hover:bg-neutral-50'"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>
              <p class="text-[11px] text-red-700 bg-red-50 border border-red-200 rounded-sm p-2">
                <i class="fas fa-triangle-exclamation mr-1"></i>
                El host quedará bloqueado en el Address Group de cuarentena del FortiGate hasta que expire o lo liberes manualmente.
              </p>
            </div>
            <div class="px-5 py-3.5 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
              <button type="button" @click="cancelAction" class="px-3.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 rounded-sm transition-colors">Cancelar</button>
              <button type="button" @click="confirmQuarantine" :disabled="isProcessingAction" class="px-3.5 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-sm inline-flex items-center gap-2 transition-colors">
                <i v-if="isProcessingAction" class="fas fa-circle-notch fa-spin"></i>
                Confirmar cuarentena
              </button>
            </div>
          </template>

        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import zabbixService from '../services/zabbix.service';
import fortigateService from '../services/fortigate.service';
import SessionDetailDrawer from '../components/SessionDetailDrawer.vue';
import IsolateHostDrawer from '../components/IsolateHostDrawer.vue';
import HostsInventoryPanel from '../components/HostsInventoryPanel.vue';
import { pickFortigateIp, saveLastFortigateIp } from '../utils/fortigatePreference';

// ------------------------------------------------------------------
// Constantes
// ------------------------------------------------------------------
const GB = 1024 ** 3;
const MB = 1024 ** 2;
const KB = 1024;
const LIVE_POLL_MS = 15000;

const LIMIT_TICKS = [1, 2, 5, 10, 20, 50, 100, 250, 500, 1000];
const DEFAULT_LIMIT_INDEX = 5;
const UNLIMITED_INDEX = LIMIT_TICKS.length;

function formatLimitTick(mbps) {
  return mbps >= 1000 ? `${mbps / 1000}G` : `${mbps}M`;
}

function formatLimitLabel(mbps) {
  const n = Number(mbps);
  if (mbps == null || mbps === '' || n <= 0) return 'Sin límite';
  const nice = Math.abs(n - Math.round(n)) < 0.05 ? Math.round(n) : n;
  if (nice >= 1000) return `${nice / 1000} Gbps`;
  return `${nice} Mbps`;
}

function isUnlimitedIndex(index) {
  return Number(index) >= UNLIMITED_INDEX;
}

function limitMbpsAt(index) {
  if (isUnlimitedIndex(index) || index == null || index < 0) return null;
  return LIMIT_TICKS[index] ?? null;
}

function indexForMbps(mbps) {
  const n = Number(mbps);
  const idx = LIMIT_TICKS.indexOf(n);
  return idx >= 0 ? idx : DEFAULT_LIMIT_INDEX;
}

const limitSelectOptions = LIMIT_TICKS.map((mbps) => ({ mbps, label: formatLimitLabel(mbps) }));

const APP_CATALOG = {
  'Steam': { icon: 'fab fa-steam', badge: 'bg-indigo-50 text-indigo-600' },
  'Windows Update': { icon: 'fab fa-microsoft', badge: 'bg-blue-50 text-blue-600' },
  'Microsoft 365': { icon: 'fab fa-microsoft', badge: 'bg-blue-50 text-blue-600' },
  'Netflix': { icon: 'fas fa-film', badge: 'bg-red-50 text-red-600' },
  'YouTube': { icon: 'fab fa-youtube', badge: 'bg-red-50 text-red-600' },
  'Zoom': { icon: 'fas fa-video', badge: 'bg-sky-50 text-sky-600' },
  'Dropbox': { icon: 'fab fa-dropbox', badge: 'bg-blue-50 text-blue-600' },
  'Spotify': { icon: 'fab fa-spotify', badge: 'bg-emerald-50 text-emerald-600' },
  'BitTorrent': { icon: 'fas fa-share-nodes', badge: 'bg-red-50 text-red-600' },
  'TOR': { icon: 'fas fa-mask', badge: 'bg-amber-50 text-amber-600' },
  'SMB/Backup': { icon: 'fas fa-database', badge: 'bg-neutral-100 text-neutral-600' },
  'HTTPS': { icon: 'fas fa-lock', badge: 'bg-neutral-100 text-neutral-600' },
  'Facebook': { icon: 'fab fa-facebook', badge: 'bg-blue-50 text-blue-600' },
  'Instagram': { icon: 'fab fa-instagram', badge: 'bg-pink-50 text-pink-600' },
  'DNS': { icon: 'fas fa-network-wired', badge: 'bg-neutral-100 text-neutral-600' },
  'Discord': { icon: 'fab fa-discord', badge: 'bg-indigo-50 text-indigo-600' },
  'speed.cloudflare.com': { icon: 'fas fa-gauge-high', badge: 'bg-orange-50 text-orange-600' },
  'Cloudflare': { icon: 'fas fa-cloud', badge: 'bg-orange-50 text-orange-600' },
  'Google': { icon: 'fab fa-google', badge: 'bg-red-50 text-red-600' },
  'Akamai CDN': { icon: 'fas fa-server', badge: 'bg-neutral-100 text-neutral-600' },
};

function appMeta(name) {
  const key = Object.keys(APP_CATALOG).find((k) => String(name || '').toLowerCase().includes(k.toLowerCase()));
  return (key && APP_CATALOG[key]) || { icon: 'fas fa-diagram-project', badge: 'bg-neutral-100 text-neutral-600' };
}

function riskForApp(app) {
  const name = String(app || '').toLowerCase();
  if (/(bittorrent|torrent|p2p|emule)/.test(name)) return 'high';
  if (/(tor\b|onion|proxy|anonym)/.test(name)) return 'medium';
  return 'none';
}

const talkers = ref([]);
const bannedIps = ref([]);
const isolateDrawerOpen = ref(false);
const isolateDrawerAction = ref('quarantine');
const isolateSeedHost = ref(null);
const hostsPanelRef = ref(null);
const isolating = ref(false);
const quarantineReasons = ref({});
const macBlocks = ref([]);
const destinationBlocks = ref([]);
const nocAudit = ref([]);
const opsTab = ref('live');
const blockedApps = ref(new Set());
const shapingAssignments = ref([]);
const isLoadingAudit = ref(false);
const auditError = ref('');
const auditSource = ref('');
const auditSessionCount = ref(null);

// ------------------------------------------------------------------
// Estado: firewall objetivo
// ------------------------------------------------------------------
const fortigates = ref([]);
const selectedFirewallIp = ref('');
const manualIpMode = ref(false);

function looksLikeIp(value) {
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(String(value || '').split(':')[0]);
}

function sessionId(session) {
  return [session.srcip, session.dstip, session.dst_host, session.app, session.dport].join('|');
}

const PROTOCOL_APPS = new Set(['DNS', 'NTP', 'SNMP', 'DHCP', 'ICMP', 'HTTP', 'HTTPS', 'SSH', 'FTP']);

function mapSession(session) {
  const srcIp = session.srcip || '';
  const assignment = shapingAssignments.value.find((a) => a.ip === srcIp && a.scope === 'host');
  const domain = session.dst_host && !looksLikeIp(session.dst_host) ? session.dst_host : '';
  const rawApp = session.app || '';
  const app = domain && PROTOCOL_APPS.has(String(rawApp).toUpperCase())
    ? domain
    : (rawApp && !['Tráfico no clasificado', 'Cloudflare', 'Akamai CDN'].includes(rawApp)
      ? rawApp
      : (domain || 'HTTPS'));
  const destHit = destinationBlocks.value.find((b) => (
    b.srcip === srcIp && destMatchesBlock(session, b, { app, domain })
  ));
  return {
    id: sessionId(session),
    srcIp,
    srcUser: session.user || '',
    srcHost: session.hostname || '',
    dstIp: domain || session.dstip || '—',
    dstHost: domain && session.dstip && session.dstip !== domain ? session.dstip : '',
    destIpRaw: session.dstip || '',
    destDomain: domain,
    srcIntf: session.srcintf || '',
    dstIntf: session.dstintf || '',
    country: session.country || '',
    natIp: session.nat_ip || '',
    txPackets: Number(session.tx_packets || 0),
    rxPackets: Number(session.rx_packets || 0),
    policy: session.policy || '',
    app,
    proto: session.proto || 'tcp',
    sport: session.sport || 0,
    dport: session.dport || 0,
    txBytes: Number(session.tx_bytes || 0),
    rxBytes: Number(session.rx_bytes || 0) || (session.tx_bytes ? 0 : Number(session.bytes || 0)),
    sessionSeconds: Number(session.duration || 0),
    status: 'active',
    blocked: bannedIps.value.some((b) => b.ip === srcIp),
    destBlocked: Boolean(destHit),
    destBlockedLabel: destHit?.dest_label || '',
    appBlocked: blockedApps.value.has(session.app),
    shaped: Boolean(assignment),
    shaperLabel: assignment?.mbps ? formatLimitLabel(assignment.mbps) : (assignment?.profileLabel || ''),
    shaperMbps: assignment?.mbps || 0,
    risk: riskForApp(session.app),
  };
}

async function fetchFirewalls() {
  try {
    const data = await zabbixService.getFortigates();
    fortigates.value = Array.isArray(data) ? data : [];
    if (fortigates.value.length) {
      selectedFirewallIp.value = pickFortigateIp(fortigates.value, selectedFirewallIp.value);
    } else {
      manualIpMode.value = true;
    }
  } catch (error) {
    console.warn('No se pudo cargar la lista de FortiGates, se usará IP manual:', error.message);
    manualIpMode.value = true;
  }
}

async function loadBanned() {
  if (!selectedFirewallIp.value) return;
  try {
    const res = await fortigateService.getBannedIps(selectedFirewallIp.value);
    bannedIps.value = res?.banned || [];
    macBlocks.value = res?.mac_blocks || [];
  } catch (error) {
    console.warn('No se pudo leer la cuarentena del FortiGate:', error.message);
  }
}

async function loadShapingAssignments() {
  if (!selectedFirewallIp.value) return;
  try {
    const res = await fortigateService.getShapingAssignments(selectedFirewallIp.value);
    shapingAssignments.value = (res?.assignments || []).map((a) => {
      return {
        ip: a.srcip || a.ip,
        destLabel: a.dest_label || (a.scope === 'host' ? 'Todo el equipo' : a.ip),
        policyName: a.policy_name,
        profileName: String(a.shaper || '').replace(/-pipe$/, ''),
        profileLabel: a.label || formatLimitLabel(a.mbps),
        mbps: a.mbps || 0,
        scope: a.scope || 'host',
        direction: a.direction || 'symmetric',
        origin: a.origin || (a.scope === 'destination' ? 'destination' : 'manual'),
        appliedAt: Date.now(),
      };
    });
  } catch (error) {
    console.warn('No se pudieron leer las políticas de shaping:', error.message);
  }
}

let loadInFlight = false;

async function loadLiveData(silent = false) {
  if (!selectedFirewallIp.value || loadInFlight) return;
  loadInFlight = true;
  if (!silent && !talkers.value.length) isLoadingAudit.value = true;
  try {
    const audit = await fortigateService.getTrafficAudit(selectedFirewallIp.value, { realtime: true });
    auditSource.value = audit?.cached ? `${audit.source || 'api'} (caché)` : (audit?.source || '');
    let sessions = [...(audit?.sessions || [])];
    if (!sessions.length && (audit?.sources || []).length) {
      sessions = audit.sources.map((item) => ({
        srcip: item.key,
        hostname: item.hostname,
        dstip: (audit.destinations || [])[0]?.key || '',
        dst_host: item.hostname || '',
        app: (audit.applications || []).find((a) => a.key && !['Tráfico no clasificado', 'Cloudflare'].includes(a.key))?.key || 'HTTPS',
        bytes: item.bytes,
        tx_bytes: 0,
        rx_bytes: item.bytes,
        duration: 0,
        sessions: item.sessions,
        proto: '',
        sport: 0,
        dport: 0,
        user: '',
      }));
    }
    const firewallIp = selectedFirewallIp.value;
    sessions = sessions.filter((s) => s.srcip && s.srcip !== firewallIp && !String(s.srcip).startsWith(firewallIp + ':'));
    if (sessions.length) {
      auditError.value = '';
      auditSessionCount.value = audit?.session_count ?? sessions.length;
      talkers.value = sessions
        .sort((a, b) => Number(b.bytes || 0) - Number(a.bytes || 0))
        .map(mapSession);
    } else if (!talkers.value.length) {
      auditError.value = '';
    }
  } catch (error) {
    if (!talkers.value.length) {
      auditError.value = error.message?.includes('403')
        ? 'API Token no configurado para este FortiGate.'
        : 'No se pudo leer la API del FortiGate. Revisa token y permisos de FortiView/sesiones.';
    }
    console.error(error);
  } finally {
    isLoadingAudit.value = false;
    loadInFlight = false;
  }
}

// ------------------------------------------------------------------
// Búsqueda y filtrado en tiempo real
// ------------------------------------------------------------------
const searchQuery = ref('');
const filteredTalkers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return talkers.value;
  return talkers.value.filter((row) =>
    [row.srcIp, row.srcUser, row.srcHost, row.dstIp, row.dstHost, row.app]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(q))
  );
});

// ------------------------------------------------------------------
// KPIs
// ------------------------------------------------------------------
const activeSessionsCount = computed(() => talkers.value.filter((t) => t.status !== 'closed').length);
const totalBandwidth = computed(() => talkers.value.reduce((sum, t) => sum + t.txBytes + t.rxBytes, 0));
const quarantineRows = computed(() => [
  ...bannedIps.value.map((entry) => ({
    ip: entry.ip,
    hostname: bannedHostLabel(entry),
    reason: quarantineReasons.value[entry.ip] || entry.reason || 'Cuarentena',
    remaining: banExpiryLabel(entry),
    kind: 'ip',
  })),
  ...macBlocks.value.map((entry) => ({
    ip: entry.mac || entry.ip,
    mac: entry.mac || entry.ip,
    hostname: entry.hostname || 'MAC',
    reason: entry.reason || 'Bloqueo MAC',
    remaining: 'Permanente',
    kind: 'mac',
  })),
]);
const quarantinedCount = computed(() => quarantineRows.value.length);
const shapedCount = computed(() => shapingAssignments.value.length);
const opsTabs = computed(() => [
  { id: 'live', label: 'En vivo', icon: 'fas fa-list-check', count: () => activeSessionsCount.value },
  { id: 'hosts', label: 'Hosts', icon: 'fas fa-laptop', count: () => hostsPanelRef.value?.hostCount || 0 },
  { id: 'controls', label: 'Controles', icon: 'fas fa-user-shield', count: () => destinationBlocks.value.length },
  { id: 'quarantine', label: 'Cuarentena', icon: 'fas fa-shield-halved', count: () => quarantinedCount.value },
  { id: 'shaping', label: 'Ancho de banda', icon: 'fas fa-gauge-high', count: () => shapedCount.value },
]);

function setOpsTab(id) {
  opsTab.value = id;
  closeMenu();
}

// ------------------------------------------------------------------
// Auditoría en vivo (poll real a la API del FortiGate)
// ------------------------------------------------------------------
const isLive = ref(true);
let liveTimer = null;

let sideLoadTick = 0;

async function refreshAll(silent = false) {
  await loadLiveData(silent);
  sideLoadTick += 1;
  if (!silent || sideLoadTick % 3 === 1) {
    await Promise.all([loadBanned(), loadShapingAssignments(), loadControls()]);
    shapingAssignments.value.forEach((a) => {
      const row = talkers.value.find((t) => t.srcIp === a.ip);
      if (row) a.label = row.srcUser || row.srcHost || a.ip;
    });
  }
}

function startLive() {
  stopLive();
  liveTimer = setInterval(() => {
    if (isLive.value && selectedFirewallIp.value) refreshAll(true);
  }, LIVE_POLL_MS);
}
function stopLive() {
  if (liveTimer) {
    clearInterval(liveTimer);
    liveTimer = null;
  }
}
function toggleLive() {
  isLive.value = !isLive.value;
  if (isLive.value) {
    refreshAll(false);
    startLive();
  } else {
    stopLive();
  }
}

// ------------------------------------------------------------------
// Menú de Acciones Tácticas (dropdown flotante)
// ------------------------------------------------------------------
const openMenuFor = ref(null);
const activeMenuRow = ref(null);
const menuPosition = ref({ top: 0, left: 0 });
const menuRef = ref(null);

function openMenu(event, row) {
  if (openMenuFor.value === row.id) {
    closeMenu();
    return;
  }
  const rect = event.currentTarget.getBoundingClientRect();
  const menuWidth = 256;
  menuPosition.value = {
    top: rect.bottom + 6,
    left: Math.max(12, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - 12)),
  };
  openMenuFor.value = row.id;
  activeMenuRow.value = row;
}
function closeMenu() {
  openMenuFor.value = null;
  activeMenuRow.value = null;
}
function handleDocClick(e) {
  if (!openMenuFor.value) return;
  if (menuRef.value && menuRef.value.contains(e.target)) return;
  if (e.target.closest && e.target.closest('.actions-trigger')) return;
  closeMenu();
}

// ------------------------------------------------------------------
// Modales de confirmación
// ------------------------------------------------------------------
const pendingAction = ref(null); // { type: 'kill' | 'shape' | 'block' | 'quarantine' | 'unquarantine', row }
const isProcessingAction = ref(false);
const quarantinePanelRef = ref(null);
const controlsPanelRef = ref(null);
const releasingIp = ref('');
const revertingKey = ref('');
const quarantineDuration = ref(3600);
const blockProfileName = ref('default');
const pendingShapeIndex = ref(DEFAULT_LIMIT_INDEX);

const quarantineDurations = [
  { label: '5 min', seconds: 300 },
  { label: '30 min', seconds: 1800 },
  { label: '1 hora', seconds: 3600 },
  { label: '24 horas', seconds: 86400 },
  { label: 'Indefinido', seconds: 0 },
];

function requestAction(type, row) {
  if (!row) return;
  closeMenu();
  pendingAction.value = { type, row };
  if (type === 'quarantine') quarantineDuration.value = 3600;
  if (type === 'block') blockProfileName.value = 'default';
  if (type === 'shape') {
    pendingShapeIndex.value = indexForMbps(row.shaperMbps);
  }
}
function cancelAction() {
  if (isProcessingAction.value) return;
  pendingAction.value = null;
}

function sessionsUsingApp(appName) {
  return talkers.value.filter((t) => t.app === appName && t.status !== 'closed').length;
}

async function confirmKill() {
  const row = pendingAction.value.row;
  isProcessingAction.value = true;
  try {
    await fortigateService.killSession(selectedFirewallIp.value, row);
    alert(`Sesión terminada correctamente: ${row.srcIp} → ${row.dstIp}.`);
    pendingAction.value = null;
    await loadLiveData(true);
  } catch (error) {
    alert(`Error al terminar la sesión: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
  }
}

async function confirmShape() {
  const row = pendingAction.value.row;
  const mbps = limitMbpsAt(pendingShapeIndex.value);
  if (!mbps) return;
  isProcessingAction.value = true;
  try {
    await fortigateService.applyTrafficShaper(selectedFirewallIp.value, row.srcIp, mbps);
    alert(`Traffic shaping aplicado: ${row.srcIp} limitado a ${formatLimitLabel(mbps)}.`);
    pendingAction.value = null;
    await loadShapingAssignments();
    await loadLiveData(true);
  } catch (error) {
    alert(`Error al aplicar traffic shaping: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
  }
}

async function confirmBlockApp() {
  const row = pendingAction.value.row;
  isProcessingAction.value = true;
  try {
    await fortigateService.blockApplication(selectedFirewallIp.value, row.app, blockProfileName.value);
    alert(`'${row.app}' añadida a la lista negra del perfil '${blockProfileName.value}'.`);
    blockedApps.value = new Set([...blockedApps.value, row.app]);
    pendingAction.value = null;
    await loadLiveData(true);
  } catch (error) {
    alert(`Error al bloquear la aplicación: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
  }
}

async function confirmQuarantine() {
  const row = pendingAction.value.row;
  isProcessingAction.value = true;
  try {
    await fortigateService.banIp(selectedFirewallIp.value, row.srcIp, quarantineDuration.value);
    alert(`${row.srcIp} puesto en cuarentena correctamente.`);
    pendingAction.value = null;
    await loadBanned();
    await loadLiveData(true);
  } catch (error) {
    alert(`Error al poner en cuarentena: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
  }
}

function bannedHostLabel(entry) {
  const talker = talkers.value.find((t) => t.srcIp === entry.ip);
  return talker?.srcUser || talker?.srcHost || entry.hostname || '—';
}

function banExpiryLabel(entry) {
  const expires = Number(entry.expires || entry.expiry || 0);
  if (!expires) return 'Permanente';
  const remaining = expires - Math.floor(Date.now() / 1000);
  if (remaining <= 0) return 'Expirando…';
  const mins = Math.floor(remaining / 60);
  if (mins < 60) return `${Math.max(mins, 1)} min`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m`;
}

function openIsolateDrawer(action) {
  isolateDrawerAction.value = action;
  isolateDrawerOpen.value = true;
}

function closeIsolateDrawer() {
  isolateDrawerOpen.value = false;
  isolateSeedHost.value = null;
}

function viewHostTraffic(host) {
  searchQuery.value = host?.ip || host?.hostname || '';
  setOpsTab('live');
}

function isolateFromInventory(host) {
  isolateSeedHost.value = host || null;
  openIsolateDrawer('quarantine');
}

async function executeIsolation(payload) {
  const fw = payload.firewallIp || selectedFirewallIp.value;
  isolating.value = true;
  try {
    if (payload.action === 'mac') {
      if (!payload.mac) throw new Error('Elige un equipo con MAC o escribe la MAC.');
      await fortigateService.banMac(fw, payload.mac, payload.reason, payload.ip);
    } else {
      const res = await fortigateService.banIp(fw, payload.ip, payload.duration, { reason: payload.reason });
      const isolatedIp = res?.ip || payload.ip;
      if (isolatedIp) {
        quarantineReasons.value = {
          ...quarantineReasons.value,
          [isolatedIp]: payload.reason || 'Cuarentena',
        };
      }
    }
    isolateDrawerOpen.value = false;
    await loadBanned();
    await loadLiveData(true);
  } catch (error) {
    alert(error.message || 'No se pudo aplicar el aislamiento en el FortiGate.');
  } finally {
    isolating.value = false;
  }
}

async function releaseMacBlock(entry) {
  const mac = entry.mac || entry.ip;
  if (!mac) return;
  releasingIp.value = mac;
  try {
    await fortigateService.unbanMac(selectedFirewallIp.value, mac);
    await loadBanned();
  } catch (error) {
    alert(error.message || `No se pudo liberar la MAC ${mac}.`);
  } finally {
    releasingIp.value = '';
  }
}

const nocAuditForFirewall = computed(() => {
  const ip = selectedFirewallIp.value;
  if (!ip) return nocAudit.value;
  return nocAudit.value.filter((log) => String(log.target || '').includes(ip));
});

function destBlockHostLabel(ip) {
  const talker = talkers.value.find((t) => t.srcIp === ip);
  return talker?.srcUser || talker?.srcHost || '—';
}

function destBlockNeedles(block) {
  const needles = [];
  const push = (value) => {
    const text = String(value || '').trim().toLowerCase().replace(/^\*\./, '');
    if (text.length >= 4 && !text.startsWith('noc-')) needles.push(text);
  };
  push(block.dest_label);
  String(block.domains_label || '').split(',').forEach(push);
  return [...new Set(needles)];
}

function destMatchesBlock(session, block, extras = {}) {
  const app = String(extras.app || session.app || '').toLowerCase();
  const host = String(extras.domain || session.dst_host || '').toLowerCase();
  const destIp = String(session.dstip || '').toLowerCase();
  const hay = `${app} ${host} ${destIp}`;
  return destBlockNeedles(block).some((needle) => hay.includes(needle));
}

function formatAuditWhen(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
}

async function loadControls() {
  if (!selectedFirewallIp.value) return;
  try {
    const [blocksRes, logs] = await Promise.all([
      fortigateService.getDestinationBlocks(selectedFirewallIp.value),
      fortigateService.getNocAudit(80).catch(() => []),
    ]);
    destinationBlocks.value = blocksRes?.blocks || [];
    nocAudit.value = Array.isArray(logs) ? logs : [];
  } catch (error) {
    console.warn('No se pudieron leer los controles NOC:', error.message);
  }
}

async function revertDestinationBlock(row) {
  if (!row?.srcip) return;
  const key = `${row.srcip}|${row.dest_name}`;
  revertingKey.value = key;
  try {
    await fortigateService.unblockDestination(selectedFirewallIp.value, {
      srcip: row.srcip,
      dest_name: row.dest_name,
    });
    await loadControls();
    await loadLiveData(true);
  } catch (error) {
    alert(`No se pudo revertir ${row.dest_label} para ${row.srcip}: ${error.message}`);
  } finally {
    revertingKey.value = '';
  }
}

function requestRelease(ip) {
  const talker = talkers.value.find((t) => t.srcIp === ip);
  pendingAction.value = {
    type: 'unquarantine',
    row: talker || { srcIp: ip, ip, hostname: bannedHostLabel({ ip }) },
  };
}

async function confirmUnquarantine() {
  const row = pendingAction.value?.row;
  const ip = row?.srcIp || row?.ip;
  if (!ip) return;
  isProcessingAction.value = true;
  releasingIp.value = ip;
  try {
    await fortigateService.unbanIp(selectedFirewallIp.value, ip);
    pendingAction.value = null;
    await loadBanned();
    await loadLiveData(true);
  } catch (error) {
    alert(`No se pudo habilitar ${ip}: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
    releasingIp.value = '';
  }
}

// ------------------------------------------------------------------
// Traffic Shaping: panel dedicado (perfiles + asignación rápida)
// ------------------------------------------------------------------
const shapePresets = [
  { id: 2, label: '2M' },
  { id: 5, label: '5M' },
  { id: 10, label: '10M' },
  { id: 20, label: '20M' },
  { id: 50, label: '50M' },
  { id: 'manual', label: 'Manual' },
];
const quickAssignIp = ref('');
const shapePreset = ref(5);
const shapeManualMbps = ref(8);
const shapeDirection = ref('symmetric');

const uniqueSourceHosts = computed(() => {
  const seen = new Set();
  const list = [];
  const push = (ip, label) => {
    const hostIp = String(ip || '').trim();
    if (!hostIp || seen.has(hostIp)) return;
    seen.add(hostIp);
    list.push({ ip: hostIp, label: label || 'Desconocido' });
  };
  talkers.value.forEach((t) => {
    if (t.status === 'closed') return;
    push(t.srcIp, t.srcUser || t.srcHost);
  });
  shapingAssignments.value.forEach((a) => push(a.ip, destBlockHostLabel(a.ip)));
  return list;
});

const selectedShapeMbps = computed(() => {
  if (shapePreset.value === 'manual') {
    const n = Number(shapeManualMbps.value);
    return n > 0 ? n : null;
  }
  return Number(shapePreset.value) || null;
});

const shapeLimitPreview = computed(() => {
  if (!selectedShapeMbps.value) return 'límite';
  const n = selectedShapeMbps.value;
  const short = n >= 1000 ? `${n / 1000}G` : `${n}M`;
  return `${short} · ${shapeDirection.value === 'rx' ? 'RX' : 'TX/RX'}`;
});

const canApplyShaping = computed(() => Boolean(quickAssignIp.value && selectedShapeMbps.value));

function shapeAssignmentBadge(row) {
  const dir = row.direction === 'rx' ? 'Descarga' : 'Simétrico';
  return `${formatLimitLabel(row.mbps)} ${dir}`;
}

function shapeOriginLabel(row) {
  if (row.scope === 'destination' || row.origin === 'destination') return 'Por destino';
  if (row.origin === 'preset') return 'Preset';
  if (row.origin === 'manual') return 'Manual';
  return [2, 5, 10, 20, 50].includes(Number(row.mbps)) ? 'Preset' : 'Manual';
}

async function quickApplyShaping() {
  if (!canApplyShaping.value) return;
  const mbps = selectedShapeMbps.value;
  isProcessingAction.value = true;
  try {
    await fortigateService.applyTrafficShaper(selectedFirewallIp.value, quickAssignIp.value, mbps, {
      direction: shapeDirection.value,
      origin: shapePreset.value === 'manual' ? 'manual' : 'preset',
    });
    await loadShapingAssignments();
    await loadLiveData(true);
  } catch (error) {
    alert(`Error al aplicar traffic shaping: ${error.message}`);
  } finally {
    isProcessingAction.value = false;
  }
}

async function removeShaping(row) {
  try {
    await fortigateService.removeTrafficShaper(selectedFirewallIp.value, row.ip, row.policyName);
    await loadShapingAssignments();
    await loadLiveData(true);
  } catch (error) {
    alert(`No se pudo quitar el límite: ${error.message}`);
  }
}

function agoLabel(timestamp) {
  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return 'justo ahora';
  const mins = Math.floor(diffSeconds / 60);
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  return `hace ${hours}h ${mins % 60}m`;
}

// ------------------------------------------------------------------
// Utilidades de formato
// ------------------------------------------------------------------
function formatBytes(bytes) {
  const n = Number(bytes) || 0;
  if (n >= GB) return (n / GB).toFixed(2) + ' GB';
  if (n >= MB) return (n / MB).toFixed(1) + ' MB';
  if (n >= KB) return (n / KB).toFixed(0) + ' KB';
  return Math.round(n) + ' B';
}

const detailRow = ref(null);
const detail = ref(null);
const detailLoading = ref(false);
const detailError = ref('');
const detailNow = ref(Math.floor(Date.now() / 1000));
const detailShapeIndex = ref(-1);
const detailActionNote = ref('');
const detailConfirm = ref('');
const blockPreview = ref({});
const localChartHistory = ref([]);
let detailClock = null;
let detailPoll = null;

const liveDuration = computed(() => {
  if (detail.value?.started_at && (detail.value.active || detail.value.ended_at)) {
    const end = detail.value.active ? detailNow.value : detail.value.ended_at;
    return Math.max(0, end - detail.value.started_at);
  }
  return detailRow.value?.sessionSeconds || 0;
});

function sameTrafficFamily(a, b) {
  const left = String(a || '').toLowerCase();
  const right = String(b || '').toLowerCase();
  return ['googlevideo', 'youtube', 'ytimg', 'speed.cloudflare', 'office', 'microsoft', 'bing.'].some(
    (token) => left.includes(token) && right.includes(token)
  );
}

const successorRow = computed(() => {
  const current = detailRow.value;
  if (!current || detail.value?.active) return null;
  return talkers.value.find((row) => (
    row.srcIp === current.srcIp
    && row.id !== current.id
    && row.status !== 'closed'
    && (row.txBytes + row.rxBytes) > 50 * 1024
    && (
      sameTrafficFamily(row.dstIp, current.dstIp)
      || sameTrafficFamily(row.app, current.app)
      || row.destIpRaw === current.destIpRaw
    )
  )) || null;
});

function formatClock(epoch) {
  if (!epoch) return '—';
  return new Date(Number(epoch) * 1000).toLocaleString('es-CO', {
    hour12: false,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatRate(bps) {
  const n = Number(bps) || 0;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} Mbps`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)} Kbps`;
  return `${n} bps`;
}

async function refreshDetail() {
  if (!detailRow.value || !selectedFirewallIp.value) return;
  try {
    const data = await fortigateService.getSessionDetail(selectedFirewallIp.value, {
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
        story: `${prev.hostname || detailRow.value.srcIp} cerró esta sesión hacia ${prev.dst_host || prev.dstip}. El consumo quedó en los valores de abajo. Si das play otra vez, YouTube (u otro CDN) abre otra conversación: no sigue subiendo aquí.`,
      };
    } else {
      detail.value = data;
      if (localChartHistory.value.length === 0 && data.series) {
        localChartHistory.value = [...data.series];
      } else if (incomingBytes > 0) {
        const last = localChartHistory.value[localChartHistory.value.length - 1];
        const lastTotal = Number(last?.tx || 0) + Number(last?.rx || 0);
        if (!last || incomingBytes >= lastTotal * 0.35) {
          localChartHistory.value.push({
            t: Math.floor(Date.now() / 1000),
            tx: data.tx_bytes || 0,
            rx: data.rx_bytes || 0,
          });
          if (localChartHistory.value.length > 50) localChartHistory.value.shift();
        }
      }
    }
    detailError.value = '';
  } catch (error) {
    if (!detail.value) detailError.value = error.message || 'No se pudo leer el detalle.';
  } finally {
    detailLoading.value = false;
  }
}

function openDetail(row) {
  if (!row) return;
  closeMenu();
  detailRow.value = row;
  detail.value = null;
  detailError.value = '';
  localChartHistory.value = [];
  detailLoading.value = true;
  detailNow.value = Math.floor(Date.now() / 1000);
  refreshDetail();
  stopDetailTimers();
  detailClock = setInterval(() => {
    detailNow.value = Math.floor(Date.now() / 1000);
  }, 1000);
  detailPoll = setInterval(() => refreshDetail(), 8000);
}

function stopDetailTimers() {
  if (detailClock) {
    clearInterval(detailClock);
    detailClock = null;
  }
  if (detailPoll) {
    clearInterval(detailPoll);
    detailPoll = null;
  }
}

function closeDetail() {
  stopDetailTimers();
  detailRow.value = null;
  detail.value = null;
  detailError.value = '';
  detailActionNote.value = '';
  detailConfirm.value = '';
  detailShapeIndex.value = -1;
  blockPreview.value = {};
}

async function confirmDetailAction(payload = {}) {
  if (detailConfirm.value === 'cut') await cutThisConversation();
  else if (detailConfirm.value === 'limit') await limitThisDestination();
  else if (detailConfirm.value === 'block' || detailConfirm.value === 'block-cascade') {
    await blockThisDestination(Boolean(payload.cascade));
  }
  detailConfirm.value = '';
}

function detailTarget() {
  return {
    srcip: detail.value?.srcip || detailRow.value?.srcIp,
    dstip: detail.value?.dstip || detailRow.value?.destIpRaw,
    dst_host: detail.value?.dst_host || detailRow.value?.destDomain,
    srcintf: detail.value?.srcintf || detailRow.value?.srcIntf,
    dstintf: detail.value?.dstintf || detailRow.value?.dstIntf,
  };
}

async function cutThisConversation() {
  if (!detail.value?.dstip) return;
  isProcessingAction.value = true;
  detailActionNote.value = '';
  try {
    await fortigateService.killSession(selectedFirewallIp.value, {
      srcIp: detail.value.srcip,
      dstIp: detail.value.dstip,
      proto: detail.value.proto,
      sport: detail.value.sport,
      dport: detail.value.dport,
    });
    detailActionNote.value = 'Sesión cortada. El PC sigue en red; si el video se reanuda, YouTube puede abrir otra.';
    await refreshDetail();
  } catch (error) {
    detailActionNote.value = error.message || 'No se pudo cortar la sesión.';
  } finally {
    isProcessingAction.value = false;
  }
}

async function limitThisDestination() {
  const target = detailTarget();
  const mbps = limitMbpsAt(detailShapeIndex.value);
  if (!mbps) return;
  isProcessingAction.value = true;
  detailActionNote.value = '';
  try {
    const res = await fortigateService.applyDestinationShaper(selectedFirewallIp.value, {
      ...target,
      max_mbps: mbps,
    });
    if (detail.value?.dstip) {
      try {
        await fortigateService.killSession(selectedFirewallIp.value, {
          srcIp: target.srcip,
          dstIp: target.dstip,
          proto: detail.value.proto,
          sport: detail.value.sport,
          dport: detail.value.dport,
        });
      } catch (_) { /* el tope aplica a la sesión nueva */ }
    }
    detailActionNote.value = res.message || `Límite de ${formatLimitLabel(mbps)} solo hacia esta página. Vuelve a abrir la descarga.`;
    await refreshDetail();
  } catch (error) {
    detailActionNote.value = error.message || 'No se pudo limitar el destino.';
  } finally {
    isProcessingAction.value = false;
  }
}

async function requestDestinationBlock() {
  const target = detailTarget();
  isProcessingAction.value = true;
  detailActionNote.value = '';
  try {
    const preview = await fortigateService.previewDestinationBlock(selectedFirewallIp.value, target);
    blockPreview.value = preview || {};
    detailConfirm.value = preview?.can_cascade ? 'block-cascade' : 'block';
  } catch (error) {
    detailActionNote.value = error.message || 'No se pudo preparar el bloqueo.';
  } finally {
    isProcessingAction.value = false;
  }
}

async function blockThisDestination(cascade = false) {
  const target = detailTarget();
  isProcessingAction.value = true;
  detailActionNote.value = '';
  try {
    const res = await fortigateService.blockDestination(selectedFirewallIp.value, { ...target, cascade });
    if (detail.value?.dstip) {
      try {
        await fortigateService.killSession(selectedFirewallIp.value, {
          srcIp: target.srcip,
          dstIp: target.dstip,
          proto: detail.value.proto,
          sport: detail.value.sport,
          dport: detail.value.dport,
        });
      } catch (_) { /* la política ya niega el destino */ }
    }
    detailActionNote.value = res.message || (cascade ? 'Servicio bloqueado.' : 'Destino bloqueado.');
    await loadControls();
    await refreshDetail();
  } catch (error) {
    detailActionNote.value = error.message || 'No se pudo bloquear el destino.';
  } finally {
    isProcessingAction.value = false;
  }
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

// ------------------------------------------------------------------
// Ciclo de vida
// ------------------------------------------------------------------
watch(selectedFirewallIp, (ip, prev) => {
  if (ip) saveLastFortigateIp(ip);
  if (!ip || ip === prev) return;
  auditError.value = '';
  refreshAll(false);
});

watch(opsTab, (id) => {
  if (id === 'hosts') hostsPanelRef.value?.reload?.();
});

onMounted(async () => {
  document.addEventListener('click', handleDocClick);
  await fetchFirewalls();
  startLive();
});
onUnmounted(() => {
  stopLive();
  stopDetailTimers();
  document.removeEventListener('click', handleDocClick);
});
</script>

<style scoped>
table {
  border-spacing: 0;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
