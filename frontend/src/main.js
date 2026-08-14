import { createApp } from "vue"
import { createPinia } from "pinia"

import ElementPlus from "element-plus"
import "element-plus/dist/index.css"

import App from "./App.vue"
import router from "./router"

// ===== ECharts =====
import { use } from "echarts/core"

import { CanvasRenderer } from "echarts/renderers"

import {
  LineChart
} from "echarts/charts"

import { PieChart } from "echarts/charts"

import {
  GridComponent,
  TooltipComponent,
  LegendComponent
} from "echarts/components"

// 注册
use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  PieChart,
  TooltipComponent,
  LegendComponent
])

const app = createApp(App)

app.use(router)
app.use(createPinia())
app.use(ElementPlus)

app.mount("#app")