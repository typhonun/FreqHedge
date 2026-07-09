import {
    createRouter,
    createWebHistory
} from "vue-router"

import MainLayout from "@/layouts/MainLayout.vue"

import Dashboard from "@/views/Dashboard.vue"
import StrategyConfig from "@/views/StrategyConfig.vue"
import Charts from "@/views/Charts.vue"
import Control from "@/views/Control.vue"
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
                path: "/control",
                component: Control
            },
            {
                path: "strategyConfig",
                component: StrategyConfig
            },
            {
                path: "charts",
                component: Charts
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