<template>
  <div>
    <el-card class="status-card">
      <h2>系统状态</h2>

      <el-row :gutter="20">
        <el-col
          :span="6"
          v-for="item in services"
          :key="item.name"
        >
          <el-card shadow="hover">
            <div class="service">
              <span>{{ item.name }}</span>
              <el-tag type="success">运行中</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <template #header>
        <div class="toolbar">
          <div>系统日志</div>

          <div>
            <el-select v-model="source" style="width:130px">
              <el-option label="全部" value="all" />
              <el-option label="Backend" value="backend" />
              <el-option label="Frontend" value="frontend" />
              <el-option label="Long" value="long" />
              <el-option label="Short" value="short" />
            </el-select>

            <el-input
              ref="searchInput"
              class="search-input"
              v-model="keyword"
              placeholder="搜索日志 Ctrl+F"
              style="width:250px;margin-left:10px"
              clearable
              @keydown.enter="nextMatch"
              @keydown.shift.enter.prevent="prevMatch"
              @keydown.esc="clearSearch"
            />

            <span class="match-count" v-if="keyword && filteredLogs.length">
              {{ matchIndex + 1 }} / {{ filteredLogs.length }}
            </span>
          </div>
        </div>
      </template>

      <div
        ref="logBox"
        class="log-box"
        @scroll="checkScroll"
      >
        <div
          class="log-row"
          v-for="(log,index) in filteredLogs"
          :key="index"
        >
          <span class="time">{{ formatTime(log.time) }}</span>

          <el-tag size="small" :class="log.source">{{ log.source }}</el-tag>

          <el-tag
            size="small"
            :type="
              log.level==='ERROR' ? 'danger' :
              log.level==='WARNING' ? 'warning' : 'info'
            "
          >
            {{ log.level }}
          </el-tag>

          <span class="message" v-html="highlight(log.message)"></span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted, onUnmounted, watch } from "vue"
import axios from "axios"

const source = ref("all")
const keyword = ref("")
const logs = ref([])
const logBox = ref(null)
const searchInput = ref(null)
const matchIndex = ref(0)
const timer = ref(null)
let searchTimer = null
const autoScroll = ref(true)

const services = [
  { name: "Backend API" },
  { name: "Frontend" },
  { name: "Long Bot" },
  { name: "Short Bot" }
]

const load = async () => {
  let url = source.value === "all"
    ? "http://localhost:9000/logs/all/list"
    : `http://localhost:9000/logs/${source.value}`

  const res = await axios.get(url)
  logs.value = res.data.data

  await nextTick()
  if (logBox.value && autoScroll.value && !keyword.value) {
    logBox.value.scrollTop = logBox.value.scrollHeight
  }
}

const filteredLogs = computed(() => {
  if (!keyword.value) return logs.value
  return logs.value.filter(x => x.message.toLowerCase().includes(keyword.value.toLowerCase()))
})

function highlight(text) {
  if (!keyword.value) return text
  const key = keyword.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const reg = new RegExp(key, "gi")
  return text.replace(reg, m => `<mark>${m}</mark>`)
}

function formatTime(t) {
  if (!t) return ""
  return new Date(t * 1000).toLocaleTimeString()
}

function checkScroll() {
  if (!logBox.value) return
  const box = logBox.value
  autoScroll.value = box.scrollHeight - box.scrollTop - box.clientHeight < 50
}

function scrollToMatch() {
  nextTick(() => {
    const rows = document.querySelectorAll(".log-row")
    if (rows[matchIndex.value]) {
      rows[matchIndex.value].scrollIntoView({ behavior: "smooth", block: "center" })
    }
  })
}

watch(source, load)

watch(keyword, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    matchIndex.value = 0
    scrollToMatch()
  }, 300)
})

function nextMatch() {
  if (!keyword.value || filteredLogs.value.length === 0) return
  matchIndex.value++
  if (matchIndex.value >= filteredLogs.value.length) matchIndex.value = 0
  scrollToMatch()
}

function prevMatch() {
  if (!keyword.value || filteredLogs.value.length === 0) return
  matchIndex.value--
  if (matchIndex.value < 0) matchIndex.value = filteredLogs.value.length - 1
  scrollToMatch()
}

function clearSearch() {
  keyword.value = ""
  matchIndex.value = 0
}

const searchFocus = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "f") {
    e.preventDefault()
    nextTick(() => {
      const input = searchInput.value?.$el.querySelector("input")
      input?.focus()
      input?.select()
    })
  }
}

onMounted(() => {
  load()
  window.addEventListener("keydown", searchFocus)
  timer.value = setInterval(load, 3000)
})

onUnmounted(() => {
  window.removeEventListener("keydown", searchFocus)
  clearInterval(timer.value)
  clearTimeout(searchTimer)
})
</script>

<style scoped>
.status-card {
  margin-bottom: 20px;
}

.service {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-box {
  background: #0d1117;
  height: 650px;
  overflow: auto;
  padding: 15px;
  font-family: "Consolas", "Microsoft YaHei", monospace;
  font-size: 14px;
}

.log-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid #222;
}

.time {
  color: #888;
  width: 90px;
}

.message {
  color: #ddd;
  white-space: pre-wrap;
}

.backend {
  background: #409eff;
  color: white;
}

.frontend {
  background: #909399;
  color: white;
}

.long {
  background: #67c23a;
  color: white;
}

.short {
  background: #f56c6c;
  color: white;
}

mark {
  background: #ffd04b;
  color: black;
}

.match-count {
  margin-left: 10px;
  color: #888;
  font-size: 13px;
}
</style>