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
        redirect: "/dashboard",   // 根路径默认跳到仪表盘
        children: [
            {
                path: "dashboard",           // 子路由不要写 / 开头
                name: "Dashboard",
                component: Dashboard,
                meta: { title: "仪表盘" }     // ← 新增
            },
            {
                path: "control",
                name: "Control",
                component: Control,
                meta: { title: "控制中心" }    // ← 新增
            },
            {
                path: "strategyConfig",
                name: "StrategyConfig",
                component: StrategyConfig,
                meta: { title: "策略配置" }    // ← 新增
            },
            {
                path: "charts",
                name: "Charts",
                component: Charts,
                meta: { title: "K线分析" }     // ← 新增
            },
            {
                path: "logs",
                name: "Logs",
                component: Logs,
                meta: { title: "系统日志" }    // ← 新增
            }
        ]
    }
]

export default createRouter({
    history: createWebHistory(),
    routes
})