import axios from "axios"

const api = axios.create({
    baseURL: "http://localhost:9000"
})

export const getCount = () =>
    api.get("/position/count")

export const getProfit = () =>
    api.get("/position/profit")

export const getOpenPositions = () =>
    api.get("/position/open")

export const getAvailablePairs = (params) =>
    api.get("/position/available_pairs", { params })

export const forceEnter = (payload) =>
    api.post("/position/force_enter", payload)

export const closeAll = (payload) =>
    api.post("/position/close_all", payload)