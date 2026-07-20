<template>
  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans relative">
    
    <!-- BotÃ³n de ConfiguraciÃ³n de Servidores -->
    <div class="absolute top-4 right-4 sm:top-6 sm:right-6">
      <button 
        @click="showServerConfig = true" 
        class="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 rounded-full transition-all flex items-center justify-center group"
        title="Configuración del Sistema"
      >
        <svg class="w-6 h-6 group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    </div>

    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-10 px-6 shadow-md rounded-sm border border-slate-200 sm:px-10">
        
        <div class="mb-8 text-center flex flex-col items-center">
          <!-- Icono corporativo -->
          <img src="/logo.png" alt="Logo" class="w-auto h-16 mb-3 object-contain" />
          <h1 class="text-2xl font-bold text-slate-800 tracking-tight">AdInfra F2</h1>
          <p class="text-[11px] text-gray-500 mt-1 capitalize tracking-wide">Autenticación de Dominio</p>
        </div>

        <form class="space-y-5" @submit.prevent="handleLogin">
          <div>
            <label for="username" class="block text-sm font-medium text-slate-700 mb-1">
              Usuario
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                class="appearance-none block w-full pl-10 pr-3 py-2 bg-white border border-slate-300 rounded-sm shadow-sm placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-800 focus:border-slate-800 sm:text-sm transition-all"
              />
            </div>
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-slate-700 mb-1">
              Contraseña
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                autocomplete="current-password"
                class="appearance-none block w-full pl-10 pr-3 py-2 bg-white border border-slate-300 rounded-sm shadow-sm placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-800 focus:border-slate-800 sm:text-sm transition-all"
              />
            </div>
          </div>

          <div v-if="errorMessage" class="text-sm text-red-800 bg-red-50 py-2 px-3 rounded-sm border border-red-200 text-center">
            {{ errorMessage }}
          </div>

          <div class="pt-3">
            <button
              type="submit"
              :disabled="isLoading"
              class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-sm shadow-md text-sm font-medium text-white bg-slate-800 hover:bg-slate-700 hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-70 disabled:cursor-not-allowed transition-all duration-200"
            >
              {{ isLoading ? 'Verificando...' : 'Iniciar Sesión' }}
            </button>
          </div>
        </form>

      </div>
    </div>
    
    <!-- Modal de Configuración -->
    <Teleport to="body">
      <ServerConfigModal v-if="showServerConfig" @close="showServerConfig = false" />
    </Teleport>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ServerConfigModal from '@/components/ServerConfigModal.vue'

const router = useRouter()
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)
const showServerConfig = ref(false)

const handleLogin = async () => {
  errorMessage.value = ''
  isLoading.value = true
  
  try {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Credenciales inválidas')
      }
      throw new Error('Error de comunicación con el servidor')
    }

    const data = await response.json()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('display_name', data.display_name)
    router.push('/monitoring')
    
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}
</script>
