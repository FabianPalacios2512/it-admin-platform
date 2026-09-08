<template>
  <teleport to="body">
    <transition name="drawer">
      <div v-if="isOpen" class="fixed inset-0 z-[9999] flex justify-end" @keydown.esc="close">
        
        <!-- Backdrop tenue -->
        <div class="absolute inset-0 bg-slate-900/10 backdrop-blur-[2px] transition-opacity" @click="close"></div>
        
        <!-- Drawer Panel (Right Side, 60vw / max-w-5xl) -->
        <div class="relative bg-white h-full w-[60vw] max-w-5xl shadow-2xl flex flex-col border-l border-gray-200 overflow-hidden drawer-panel">
          
          <!-- Sticky Header (Compacto) -->
          <div class="sticky top-0 bg-white border-b border-gray-200 z-10 shrink-0">
            <!-- Título y Botón Cerrar -->
            <div class="flex items-center justify-between px-4 py-3">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                  <i class="fas fa-headphones-alt text-blue-600 text-sm"></i>
                </div>
                <h2 class="text-sm font-bold text-gray-800 tracking-wide">Explorador de Grabaciones</h2>
              </div>
              <button @click="close" class="text-gray-400 hover:text-gray-700 transition-colors p-1.5 rounded-full hover:bg-gray-100" title="Cerrar">
                <i class="fas fa-times text-base"></i>
              </button>
            </div>

            <!-- Toolbar (Filtros Compactos) -->
            <div class="px-4 pb-3 flex gap-2">
              <div class="relative w-40">
                <i class="fas fa-calendar-alt absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-[11px]"></i>
                <input type="date" v-model="selectedDate" @change="fetchRecordings"
                       class="w-full h-8 pl-7 pr-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-gray-700 bg-white transition-all">
              </div>
              <div class="relative flex-1">
                <i class="fas fa-search absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-[11px]"></i>
                <input type="text" v-model="extensionFilter" @keyup.enter="fetchRecordings" placeholder="Filtrar por Extensión o Número Destino..."
                       class="w-full h-8 pl-7 pr-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-gray-700 bg-white transition-all">
              </div>
              <button @click="fetchRecordings" :disabled="loading" 
                      class="h-8 px-4 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700 transition-colors flex items-center gap-1.5 disabled:opacity-50 shrink-0">
                <i class="fas fa-sync-alt text-[11px]" :class="{'fa-spin': loading}"></i>
                Buscar
              </button>
            </div>
          </div>

          <!-- Main Content (High Density Table) -->
          <div class="flex-1 overflow-y-auto bg-white relative">
            
            <!-- Loading State -->
            <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm z-10">
              <div class="flex flex-col items-center gap-2">
                <i class="fas fa-circle-notch fa-spin text-3xl text-blue-500"></i>
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-500">Obteniendo registros...</span>
              </div>
            </div>

            <!-- Error State -->
            <div v-if="error" class="flex flex-col items-center justify-center h-full p-6 text-center">
              <i class="fas fa-exclamation-triangle text-red-400 text-4xl mb-3"></i>
              <p class="text-sm font-bold text-gray-800 mb-1">Error de consulta</p>
              <p class="text-xs text-gray-500">{{ error }}</p>
            </div>

            <!-- Empty State -->
            <div v-if="!loading && !error && recordings.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400 gap-3 p-6 text-center">
              <div class="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-1 border border-gray-100">
                <i class="fas fa-folder-open text-2xl text-gray-300"></i>
              </div>
              <div>
                <p class="text-sm font-bold text-gray-700">No hay grabaciones</p>
                <p class="text-xs text-gray-500 mt-0.5">No se encontraron archivos de audio para esta fecha o filtro.</p>
              </div>
            </div>

            <!-- Data Table -->
            <table v-if="!error && recordings.length > 0" class="min-w-full divide-y divide-gray-100">
              <thead class="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th scope="col" class="px-4 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider w-32">Fecha / Hora</th>
                  <th scope="col" class="px-4 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider w-24">Tipo</th>
                  <th scope="col" class="px-4 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Extensión (Origen)</th>
                  <th scope="col" class="px-4 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Destino</th>
                  <th scope="col" class="px-4 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase tracking-wider w-24">Tamaño (MB)</th>
                  <th scope="col" class="px-4 py-2 text-right text-[11px] font-semibold text-gray-500 uppercase tracking-wider w-16">Acción</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-50">
                <tr v-for="rec in recordings" :key="rec.filepath" 
                    @click="play(rec)"
                    class="hover:bg-blue-50/60 cursor-pointer transition-colors"
                    :class="{'bg-blue-50/80': currentRecording?.filepath === rec.filepath}">
                  <!-- Fecha/Hora -->
                  <td class="px-4 py-1.5 whitespace-nowrap text-sm text-gray-600 font-mono">
                    {{ rec.time }}
                  </td>
                  <!-- Tipo -->
                  <td class="px-4 py-1.5 whitespace-nowrap">
                    <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
                          :class="rec.type.includes('exten') ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
                      {{ rec.type }}
                    </span>
                  </td>
                  <!-- Origen (Clean Text) -->
                  <td class="px-4 py-1.5 whitespace-nowrap">
                    <span class="text-sm font-semibold text-gray-700">
                      {{ rec.source || '—' }}
                    </span>
                  </td>
                  <!-- Destino (Clean Text) -->
                  <td class="px-4 py-1.5 whitespace-nowrap">
                    <span class="text-sm font-medium text-gray-700">
                      {{ rec.destination || '—' }}
                    </span>
                  </td>
                  <!-- Tamaño -->
                  <td class="px-4 py-1.5 whitespace-nowrap text-[13px] text-gray-500 text-right font-mono">
                    {{ rec.size_mb }}
                  </td>
                  <!-- Acción -->
                  <td class="px-4 py-1.5 whitespace-nowrap text-right">
                    <button class="w-7 h-7 rounded-full inline-flex items-center justify-center transition-colors"
                            :class="currentRecording?.filepath === rec.filepath ? 'bg-blue-600 text-white' : 'text-blue-500 hover:bg-blue-100 hover:text-blue-700'">
                      <i class="fas fa-play text-[10px] ml-0.5" v-if="currentRecording?.filepath !== rec.filepath"></i>
                      <i class="fas fa-volume-up text-[11px]" v-else></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Sticky Footer Player (Compacto) -->
          <transition name="slide-up">
            <div v-if="currentRecording" class="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-2.5 shrink-0 w-full z-20">
              
              <div class="flex items-center justify-between max-w-4xl mx-auto gap-6">
                <!-- Info (Parsed from row data) -->
                <div class="min-w-0 flex-1">
                  <div class="text-[9px] font-bold text-blue-600 uppercase tracking-widest mb-0.5 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                    Reproduciendo Grabación
                  </div>
                  <div class="text-sm font-bold text-gray-800 truncate">
                    Origen: <span class="font-mono">{{ currentRecording.source }}</span>
                    <i class="fas fa-arrow-right text-gray-400 mx-2 text-[11px]"></i> 
                    Destino: <span class="font-mono">{{ currentRecording.destination }}</span>
                  </div>
                  <div class="text-[11px] text-gray-500 mt-0.5">
                    <i class="far fa-calendar-alt mr-1"></i> {{ selectedDate }} a las {{ currentRecording.time }}
                  </div>
                </div>

                <!-- Audio Control (Native with styled wrapper) -->
                <div class="w-[350px] flex items-center gap-3 shrink-0">
                  <div class="flex-1 bg-white rounded-lg border border-gray-200 h-9 flex items-center overflow-hidden">
                    <audio ref="audioPlayer" :src="currentAudioUrl" controls autoplay 
                           class="w-full h-full outline-none [&::-webkit-media-controls-panel]:bg-white [&::-webkit-media-controls-enclosure]:bg-white [&::-webkit-media-controls-enclosure]:border-none"></audio>
                  </div>
                  <button @click="stop" class="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-400 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors shrink-0" title="Detener reproducción">
                    <i class="fas fa-times text-xs"></i>
                  </button>
                </div>
              </div>
              
            </div>
          </transition>

        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  isOpen: Boolean
});

const emit = defineEmits(['close']);

// Format current date to YYYY-MM-DD
const today = new Date();
const formattedToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

const selectedDate = ref(formattedToday);
const extensionFilter = ref('');
const recordings = ref([]);
const loading = ref(false);
const error = ref(null);

const currentRecording = ref(null);
const audioPlayer = ref(null);

const currentAudioUrl = computed(() => {
  if (!currentRecording.value?.filepath) return '';
  return `/api/v1/pbx/recordings/play?filepath=${encodeURIComponent(currentRecording.value.filepath)}`;
});

const fetchRecordings = async () => {
  if (!selectedDate.value) return;
  
  loading.value = true;
  error.value = null;
  recordings.value = [];
  
  try {
    const res = await axios.get(`/api/v1/pbx/recordings/list`, {
      params: {
        date: selectedDate.value,
        extension: extensionFilter.value || undefined
      }
    });
    
    if (res.data.status === 'success') {
      recordings.value = res.data.data;
    } else {
      error.value = res.data.message || 'Error desconocido del servidor';
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message;
  } finally {
    loading.value = false;
  }
};

const play = (rec) => {
  currentRecording.value = rec;
};

const stop = () => {
  currentRecording.value = null;
};

const close = () => {
  stop();
  emit('close');
};

watch(() => props.isOpen, (open) => {
  if (open) {
    fetchRecordings();
  } else {
    stop();
  }
});
</script>

<style scoped>
/* Transición Drawer (Derecha a Izquierda) */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer-panel {
  transform: translateX(100%);
}
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}

/* Transición Slide Up para el Player */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
