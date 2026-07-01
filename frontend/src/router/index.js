import {
    createRouter,
    createWebHistory
} from "vue-router"

import MainLayout from "@/layouts/MainLayout.vue"

import Dashboard from "@/views/Dashboard.vue"
import Positions from "@/views/Positions.vue"
import History from "@/views/History.vue"
import Charts from "@/views/Charts.vue"
import Bot from "@/views/Bot.vue"
import Logs from "@/views/Logs.vue"

const routes = [
    {
        path: "/",
        component: MainLayout,

        children: [
            {
                path: "",
                component: Dashboard
            },
            {
                path: "positions",
                component: Positions
            },
            {
                path: "history",
                component: History
            },
            {
                path: "charts",
                component: Charts
            },
            {
                path: "bot",
                component: Bot
            },
            {
                path: "logs",
                component: Logs
            }
        ]
    }
]

export default createRouter({
    history: createWebHistory(),
    routes
})