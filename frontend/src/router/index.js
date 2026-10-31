import { createRouter, createWebHistory } from "vue-router"

import MainLayout from "@/layouts/MainLayout.vue"

// ============ Auth 页面 ============
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import ForgotPassword from '@/views/auth/ForgotPassword.vue'
import ResetPassword from '@/views/auth/ResetPassword.vue'

// ============ 业务页面 ============
import Dashboard from "@/views/Dashboard.vue"
import Charts from "@/views/Charts.vue"
import Logs from "@/views/Logs.vue"
import Positions from '@/views/Positions.vue'
import Settings from '@/views/Settings.vue'
import SettingsProfile from '@/views/settings/Profile.vue'
import SettingsPreferences from '@/views/settings/Preferences.vue'
import SettingsExchanges from '@/views/settings/Exchanges.vue'
import BotList from "@/views/bots/BotList.vue"
import BotConfig from "@/views/bots/BotConfig.vue"

import { useAuthStore } from '@/stores/authStore'

const routes = [
    // ============ Auth（无 MainLayout）============
    { path: '/login',           name: 'Login',          component: Login,          meta: { public: true } },
    { path: '/register',        name: 'Register',       component: Register,       meta: { public: true } },
    { path: '/forgot-password', name: 'ForgotPassword', component: ForgotPassword, meta: { public: true } },
    { path: '/reset-password',  name: 'ResetPassword',  component: ResetPassword,  meta: { public: true } },

    // ============ 主应用 ============
    {
        path: "/",
        component: MainLayout,
        redirect: "/dashboard",
        children: [
            { path: "dashboard",  name: "Dashboard",  component: Dashboard,  meta: { title: "仪表盘" } },
            { path: "bots",       name: "BotList",    component: BotList,    meta: { title: "机器人管理" } },
            { path: "bots/new",   name: "BotNew",     component: BotConfig,  meta: { title: "新建机器人" } },
            { path: "bots/:id",   name: "BotDetail",  component: BotConfig,  meta: { title: "机器人配置" } },
            { path: "positions",  name: "Positions",  component: Positions,  meta: { title: "持仓管理" } },
            { path: "charts",     name: "Charts",     component: Charts,     meta: { title: "K线分析" } },
            { path: "logs",       name: "Logs",       component: Logs,       meta: { title: "系统日志" } },
            {
                path: "settings",
                component: Settings,
                redirect: "/settings/profile",
                meta: { title: "设置" },
                children: [
                    { path: "profile",     name: "SettingsProfile",     component: SettingsProfile,     meta: { title: "设置" } },
                    { path: "preferences", name: "SettingsPreferences", component: SettingsPreferences, meta: { title: "偏好" } },
                    { path: "exchanges",   name: "SettingsExchanges",   component: SettingsExchanges,   meta: { title: "交易所 API" } },
                ]
            },
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// ============ 全局守卫 ============

router.beforeEach((to) => {
    const auth = useAuthStore()

    // 未登录访问受保护页 → 跳登录
    if (!to.meta.public && !auth.isLoggedIn) {
        return { name: 'Login', query: { redirect: to.fullPath } }
    }

    // 已登录访问 login/register → 跳 dashboard
    if (auth.isLoggedIn && ['Login', 'Register'].includes(to.name)) {
        return { name: 'Dashboard' }
    }
})

export default router