<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const terminalContainer = ref(null)
const connectionStatus = ref('Desconectado')
let term = null
let fitAddon = null
let ws = null

function initTerminal() {
  term = new Terminal({
    cursorBlink: true,
    fontFamily: '"Fira Code", monospace, courier-new, courier',
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#0052cc',
      selectionBackground: 'rgba(0, 82, 204, 0.3)'
    },
    convertEol: true
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  
  if (terminalContainer.value) {
    term.open(terminalContainer.value)
    fitAddon.fit()
    // Limpiar terminal antes de conectar (PTY enviará su propia info)
    term.clear()
    
    connectWebSocket()
  }

  // Con PTY real, enviamos la tecla instantáneamente (el servidor hace echo)
  term.onData(data => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // Asegurar apuntar al backend que suele estar en puerto 8000 en dev
  const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/terminal/ws`
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    connectionStatus.value = 'Conectado (PowerShell)'
    // Enviar el tamaño inicial apenas conecte
    if (term) {
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    }
  }
  
  ws.onmessage = (event) => {
    term.write(event.data)
  }
  
  ws.onclose = () => {
    connectionStatus.value = 'Desconectado'
    term.writeln('\r\n\x1b[31m[!] Conexión cerrada.\x1b[0m')
  }
  
  ws.onerror = (err) => {
    console.error('WS Error:', err)
  }
}

onMounted(() => {
  initTerminal()
  window.addEventListener('resize', () => {
    if (fitAddon && term && ws && ws.readyState === WebSocket.OPEN) {
      fitAddon.fit()
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    }
  })
})

onBeforeUnmount(() => {
  if (ws) ws.close()
  if (term) term.dispose()
})
</script>

<template>
  <div class="h-[calc(100vh-64px)] flex flex-col p-4 bg-slate-50">
    <div class="flex justify-between items-center mb-4 shrink-0">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Consola PowerShell</h2>
        <p class="text-sm text-slate-500">Ejecución directa en el servidor remoto</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="relative flex h-3 w-3">
          <span :class="['animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', connectionStatus.includes('Conectado') ? 'bg-emerald-400' : 'bg-red-400']"></span>
          <span :class="['relative inline-flex rounded-full h-3 w-3', connectionStatus.includes('Conectado') ? 'bg-emerald-500' : 'bg-red-500']"></span>
        </span>
        <span class="text-sm font-medium text-slate-700">{{ connectionStatus }}</span>
      </div>
    </div>
    
    <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4 rounded shadow-sm flex items-start gap-3 shrink-0">
      <svg class="w-6 h-6 text-blue-600 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
      <div>
        <p class="text-sm font-bold text-blue-800">Conexión a Exchange Online</p>
        <p class="text-xs text-blue-700 mt-1">
          Para ejecutar comandos de Exchange (ej. <code>Set-Mailbox</code>), primero autentícate usando el flujo de dispositivo:<br>
          <code class="bg-blue-100 px-1 py-0.5 rounded text-blue-900 font-mono select-all">Connect-ExchangeOnline -Device</code><br>
          Luego visita <b>https://microsoft.com/devicelogin</b> desde tu navegador e ingresa el código mostrado.
        </p>
      </div>
    </div>

    <div class="flex-1 w-full bg-[#1e1e1e] rounded-lg shadow-inner overflow-hidden border border-slate-800 relative">
      <div ref="terminalContainer" class="absolute inset-0 p-2"></div>
    </div>
  </div>
</template>

<style scoped>
/* Asegurar que la consola ocupe el 100% */
:deep(.xterm) {
  height: 100%;
  width: 100%;
}
:deep(.xterm-viewport) {
  overflow-y: auto !important;
}
</style>
