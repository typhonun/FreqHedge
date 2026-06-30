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