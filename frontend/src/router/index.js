import {
    createRouter,
    createWebHistory
} from "vue-router"

import MainLayout from "@/layouts/MainLayout.vue"

import Dashboard from "@/views/Dashboard.vue"
import Charts from "@/views/Charts.vue"
import Logs from "@/views/Logs.vue"
import Positions from '@/views/Positions.vue'
import Settings from '@/views/Settings.vue'
import SettingsProfile from '@/views/settings/Profile.vue'
import SettingsPreferences from '@/views/settings/Preferences.vue'
import SettingsExchanges from '@/views/settings/Exchanges.vue'
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
              path: 'positions',
              name: 'Positions',
              component: Positions,
              meta: { title: '持仓管理' }
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
                  },
                  {
                    path: 'preferences',                                          // ★ 新增
                    name: 'SettingsPreferences',
                    component: SettingsPreferences,
                    meta: { title: '偏好' }
                  },
                  { path: 'exchanges',
                    name: 'SettingsExchanges',
                    component: SettingsExchanges,
                    meta: { title: '交易所 API' }
                  },
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