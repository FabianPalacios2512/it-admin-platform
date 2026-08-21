import { ref } from 'vue'

// Estado global para notificaciones
const notifications = ref([])

export function useTasks() {
  const addNotification = (notif) => {
    const id = Date.now().toString()
    notifications.value.push({ ...notif, id })
    
    // Auto-remover después de 8 segundos si es success o info
    if (notif.type !== 'error') {
      setTimeout(() => {
        removeNotification(id)
      }, 8000)
    }
  }

  const removeNotification = (id) => {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  const startPolling = (adminUsername) => {
    // Evita múltiples pollings
    if (window._taskPollingInterval) clearInterval(window._taskPollingInterval)
    
    window._taskPollingInterval = setInterval(async () => {
      if (!adminUsername) return
      
      const token = localStorage.getItem('access_token')
      if (!token) return

      try {
        const res = await fetch(`/api/v1/tasks/?username=${adminUsername}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.success && data.data) {
            checkTaskUpdates(data.data)
          }
        }
      } catch (e) {
        // Ignorar errores de polling
      }
    }, 3000)
  }

  const stopPolling = () => {
    if (window._taskPollingInterval) {
      clearInterval(window._taskPollingInterval)
      window._taskPollingInterval = null
    }
  }

  // Compara el estado actual con el estado previo para lanzar notificaciones
  const _knownTasks = new Map()
  let isFirstFetch = true

  const checkTaskUpdates = (tasks) => {
    for (const task of tasks) {
      const knownState = _knownTasks.get(task.id)
      
      if (!knownState) {
        // Tarea nueva
        _knownTasks.set(task.id, task.status)
        
        // Si es el primer fetch, no notificamos tareas ya completadas/erróneas
        if (isFirstFetch) continue;

        if (task.status === 'processing') {
          // Feedback inicial omitido
        } else if (task.status === 'completed') {
          addNotification({
            type: 'success',
            title: 'Tarea Completada',
            message: task.description
          })
        } else if (task.status === 'error') {
          addNotification({
            type: 'error',
            title: 'Error en la Tarea',
            message: `Falló: ${task.description}. Detalles: ${task.error || ''}`
          })
        }
      } else if (knownState !== task.status) {
        // Hubo un cambio de estado
        _knownTasks.set(task.id, task.status)
        
        if (task.status === 'completed') {
          addNotification({
            type: 'success',
            title: 'Tarea Completada',
            message: task.description
          })
        } else if (task.status === 'error') {
          addNotification({
            type: 'error',
            title: 'Error en la Tarea',
            message: `Falló: ${task.description}. Detalles: ${task.error || ''}`
          })
        }
      }
    }
    isFirstFetch = false
  }

  return {
    notifications,
    addNotification,
    removeNotification,
    startPolling,
    stopPolling
  }
}
