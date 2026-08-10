import axios from "axios"
import { ref } from "vue"


const API = "http://localhost:9000"

const normalizeStatus = (value) => {
    if (typeof value === "string") {
        return value.toUpperCase()
    }

    if (typeof value === "boolean") {
        return value ? "RUNNING" : "STOPPED"
    }

    if (value && typeof value === "object") {
        if (typeof value.state === "string") {
            return value.state.toUpperCase()
        }

        if (typeof value.status === "string") {
            return value.status.toUpperCase()
        }

        if (typeof value.running === "boolean") {
            return value.running ? "RUNNING" : "STOPPED"
        }
    }

    return "STOPPED"
}


export function useStatus() {


    const longState = ref("STOPPED")

    const shortState = ref("STOPPED")


    const loadStatus = async()=>{

        try{

            const res =
                await axios.get(
                    `${API}/control/status`
                )


            console.log(
                "STATUS:",
                res.data
            )

            longState.value = normalizeStatus(res.data.long)
            shortState.value = normalizeStatus(res.data.short)


        }
        catch(e){

            console.error(e)

            longState.value="STOPPED"

            shortState.value="STOPPED"

        }

    }


    return {

        longState,

        shortState,

        loadStatus

    }

}