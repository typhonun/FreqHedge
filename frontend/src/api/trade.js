import axios from "axios"

const api = axios.create({
    baseURL: "http://localhost:9000"
})

export const getStatus = () =>
    api.get("/trade/status")

export const getBalance = () =>
    api.get("/trade/balance")

export const startBot = () =>
    api.post("/trade/start")

export const stopBot = () =>
    api.post("/trade/stop")