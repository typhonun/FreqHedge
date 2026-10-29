import { computed, ref } from 'vue'

const STORAGE_KEY = 'dcatp-trading-mode'
const storedMode = typeof window !== 'undefined'
  ? window.localStorage.getItem(STORAGE_KEY)
  : null

const mode = ref(storedMode === 'live' ? 'live' : 'simulation')

export function useModeStore() {
  const isSimulation = computed(() => mode.value === 'simulation')
  const label = computed(() => (isSimulation.value ? '模拟模式' : '实盘模式'))

  const setMode = (nextMode) => {
    mode.value = nextMode === 'live' ? 'live' : 'simulation'
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
    setMode,
    toggleMode,
  }
}
