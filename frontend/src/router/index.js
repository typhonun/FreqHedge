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

import Settings from '@/views/Settings.vue'
import SettingsProfile from '@/views/settings/Profile.vue'
// ============ 新增多实例页面 ============
import BotList from "@/views/bots/BotList.vue"
import BotConfig from "@/views/bots/BotConfig.vue"

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
            // ============ 新增：多实例机器人管理 ============
            {
                path: "bots",
                name: "BotList",
                component: BotList,
                meta: { title: "机器人管理" }
            },
            {
                path: "bots/new",
                name: "BotNew",
                component: BotConfig,
                meta: { title: "新建机器人" }
            },
            {
                path: "bots/:id",
                name: "BotDetail",
                component: BotConfig,
                meta: { title: "机器人配置" }
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
                path: 'settings',
                component: Settings,
                redirect: '/settings/profile',       // 进设置默认到「账户」
                meta: { title: '设置' },
                children: [
                  {
                    path: 'profile',
                    name: 'SettingsProfile',
                    component: SettingsProfile,
                    meta: { title: '账户' }

                  }
                ]
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