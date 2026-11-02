import { computed, ref } from 'vue'

const STORAGE_KEY = 'dcatp-trading-mode'
const storedMode = typeof window !== 'undefined'
  ? window.localStorage.getItem(STORAGE_KEY)
  : null

const mode = ref(storedMode === 'live' ? 'live' : 'simulation')
const requestVersion = ref(0)
let requestController = new AbortController()

export function useModeStore() {
  const isSimulation = computed(() => mode.value === 'simulation')
  const label = computed(() => (isSimulation.value ? '模拟模式' : '实盘模式'))

  const setMode = (nextMode) => {
    const normalizedMode = nextMode === 'live' ? 'live' : 'simulation'
    if (mode.value === normalizedMode) return

    // Cancel reads for the previous mode. This never touches bot lifecycle APIs.
    requestController.abort()
    requestController = new AbortController()
    requestVersion.value += 1
    mode.value = normalizedMode
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, mode.value)
    }
  }

  const toggleMode = () => setMode(isSimulation.value ? 'live' : 'simulation')

  return {
    mode,
    isSimulation,
    label,
    dryRun: isSimulation,
    requestVersion,
    getRequestConfig: () => ({ signal: requestController.signal }),
    isCurrent: (modeKey, version) =>
      mode.value === modeKey && (version == null || requestVersion.value === version),
    setMode,
    toggleMode,
  }
}
