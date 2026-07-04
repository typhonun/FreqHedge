import axios from "axios"
import { ref, onMounted, onUnmounted } from "vue"

const API = "http://localhost:9000"

export function useStatus() {

    const longRunning = ref(false)
    const shortRunning = ref(false)

    let timer = null

    const loadStatus = async () => {

        try {

            const res =
                await axios.get(
                    `${API}/control/status`
                )

            longRunning.value =
                res.data.long

            shortRunning.value =
                res.data.short

        } catch (err) {

            longRunning.value = false
            shortRunning.value = false

            console.error(err)
        }
    }

    onMounted(() => {
        loadStatus()
        timer = setInterval(loadStatus, 5000)
    })

    onUnmounted(() => {
        if (timer) clearInterval(timer)
    })

    return {
        longRunning,
        shortRunning,
        loadStatus
    }
}