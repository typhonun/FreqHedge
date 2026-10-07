import { createApp } from "vue"
import { createPinia } from "pinia"   // ★ 加这行

import ElementPlus from "element-plus"
import "element-plus/dist/index.css"

import App from "./App.vue"
import router from "./router"
import { useAuthStore } from '@/stores/authStore'

import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { LineChart } from "echarts/charts"
import { PieChart } from "echarts/charts"
import {
  GridComponent, TooltipComponent, LegendComponent, DataZoomComponent
} from "echarts/components"

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  PieChart,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent
])

const app = createApp(App)

app.use(createPinia())   // ★ Pinia 先装
app.use(router)          // ★ Router 后装
app.use(ElementPlus)

// ★ 有 token 时先拉一次用户，再挂载
const auth = useAuthStore()
auth.fetchMe().finally(() => {
  app.mount("#app")
})