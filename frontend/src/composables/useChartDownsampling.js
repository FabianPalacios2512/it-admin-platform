import { computed } from 'vue'

export function useChartDownsampling() {
  /**
   * Agrupa los datos crudos del backend calculando promedios por ventanas de TIEMPO.
   * Esto evita distorsión cuando hay huecos (gaps) en los datos o densidad irregular.
   * @param {Array} rawData - Array de datos bidimensionales [[timestamp, value], ...]
   * @param {Number} maxPoints - Puntos máximos a renderizar por serie (Recomendado: 150-300)
   * @returns {Array} Datos reducidos uniformemente en el tiempo sin overplotting
   */
  const downsampleSeries = (rawData, maxPoints = 200) => {
    if (!rawData || rawData.length === 0) return []
    
    // Si la API nos devuelve menos puntos que el límite, no intervenimos.
    if (rawData.length <= maxPoints) return rawData

    const isObjectFormat = !Array.isArray(rawData[0])

    // 1. Encontrar min y max tiempo
    const getTs = (item) => isObjectFormat ? item.timestamp : item[0]
    const getVal = (item) => isObjectFormat ? (item.value || 0) : (item[1] || 0)

    const minTs = getTs(rawData[0])
    const maxTs = getTs(rawData[rawData.length - 1])
    const timeSpan = maxTs - minTs
    
    // Si el tiempo es inválido o muy corto, retornar raw
    if (timeSpan <= 0) return rawData

    // 2. Definir tamaño del bucket de tiempo
    const binSize = timeSpan / maxPoints
    const bins = new Map() // Mapeamos por el índice del bucket

    // 3. Agrupar por tiempo
    for (let i = 0; i < rawData.length; i++) {
      const item = rawData[i]
      const ts = getTs(item)
      const val = getVal(item)
      
      const binIndex = Math.floor((ts - minTs) / binSize)
      
      if (!bins.has(binIndex)) {
        bins.set(binIndex, { sum: 0, count: 0, minTs: ts })
      }
      
      const bin = bins.get(binIndex)
      bin.sum += val
      bin.count++
    }

    // 4. Calcular promedio por bucket y armar el nuevo array
    const sampledData = []
    
    // Ordenar los índices de los buckets para mantener el orden cronológico
    const sortedBinIndices = Array.from(bins.keys()).sort((a, b) => a - b)
    
    for (const binIndex of sortedBinIndices) {
      const bin = bins.get(binIndex)
      const avgValue = Number((bin.sum / bin.count).toFixed(2))
      
      // El timestamp de la muestra será el centro teórico del bucket
      const bucketTimestamp = minTs + (binIndex * binSize) + (binSize / 2)
      
      if (isObjectFormat) {
         sampledData.push({ timestamp: bucketTimestamp, value: avgValue })
      } else {
         sampledData.push([Math.round(bucketTimestamp), avgValue])
      }
    }

    return sampledData
  }

  return { downsampleSeries }
}
