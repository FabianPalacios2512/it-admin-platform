import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import VueApexCharts from 'vue3-apexcharts'

// Global override for window.alert to convert native alerts into beautiful Tailwind toasts
window.alert = function(message) {
  // Determine toast type based on keywords
  const lowerMsg = String(message).toLowerCase();
  const isError = lowerMsg.includes('error') || lowerMsg.includes('falló') || lowerMsg.includes('fallido');
  const isWarning = lowerMsg.includes('límite') || lowerMsg.includes('seguridad') || lowerMsg.includes('atención');
  const isSuccess = lowerMsg.includes('correctamente') || lowerMsg.includes('exitoso') || lowerMsg.includes('asignada') || lowerMsg.includes('generado');
  
  let type = 'info';
  let title = 'Notificación';
  let iconHtml = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>';
  let colorClass = 'text-blue-500 bg-blue-100';

  if (isError) {
    type = 'error';
    title = 'Error';
    iconHtml = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>';
    colorClass = 'text-red-500 bg-red-100';
  } else if (isWarning) {
    type = 'warning';
    title = 'Atención';
    iconHtml = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>';
    colorClass = 'text-orange-500 bg-orange-100';
  } else if (isSuccess) {
    type = 'success';
    title = 'Completado';
    iconHtml = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>';
    colorClass = 'text-emerald-500 bg-emerald-100/50';
  }

  // Create toast container if it doesn't exist
  let container = document.getElementById('global-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'global-toast-container';
    container.className = 'fixed bottom-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none';
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement('div');
  toast.className = 'pointer-events-auto flex items-center p-4 w-full max-w-sm text-gray-500 bg-white rounded-lg shadow-lg border border-slate-100 transform transition-all duration-300 translate-y-10 opacity-0';
  
  toast.innerHTML = `
    <div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg ${colorClass}">
      ${iconHtml}
    </div>
    <div class="ml-3 text-sm font-normal">
      <span class="font-semibold text-gray-900 block">${title}</span>
      <span class="text-slate-600">${message}</span>
    </div>
    <button type="button" class="ml-auto -mx-1.5 -my-1.5 bg-white text-gray-400 hover:text-gray-900 rounded-lg focus:ring-2 focus:ring-gray-300 p-1.5 hover:bg-gray-100 inline-flex h-8 w-8 close-btn">
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
    </button>
  `;

  container.appendChild(toast);

  // Bind close button
  toast.querySelector('.close-btn').addEventListener('click', () => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('translate-y-2', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
  });

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-10', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');
  });

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (document.body.contains(toast)) {
      toast.classList.remove('translate-y-0', 'opacity-100');
      toast.classList.add('translate-y-2', 'opacity-0');
      setTimeout(() => {
        if (document.body.contains(toast)) toast.remove();
      }, 300);
    }
  }, 5000);
};

const app = createApp(App)
app.use(router)
// Registro global del componente <apexchart>. Sin esto, todas las gráficas
// (tendencias, sparklines y el panel de detalle) no se resuelven y el
// dashboard de Zabbix se ve roto ("Failed to resolve component: apexchart").
app.use(VueApexCharts)
app.component('apexchart', VueApexCharts)
app.mount('#app')
