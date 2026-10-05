// src/api/backtest.js
import axios from 'axios'

const API = 'http://localhost:9000'

/** 同步回测（保留兼容，不推荐前端使用） */
export async function runBacktest(botId, payload) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/backtest`,
    payload
  )
  return data
}

/** ★ 启动异步回测，返回 { job_id, status } */
export async function startBacktest(botId, payload) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/backtest/start`,
    payload
  )
  return data
}

/** ★ 查询回测进度；完成时返回体里会带 result */
export async function getBacktestProgress(botId, jobId) {
  const { data } = await axios.get(
    `${API}/bots/${botId}/backtest/progress/${jobId}`
  )
  return data
}

/** ★ 取消回测 */
export async function cancelBacktest(botId, jobId) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/backtest/cancel/${jobId}`
  )
  return data
}

/** 下载数据（耗时可能几分钟，关闭 axios 超时） */
export async function downloadData(botId, payload) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/download-data`,
    payload,
    { timeout: 0 }
  )
  return data
}

/** ★ 启动异步下载，返回 { job_id, status, skipped } */
export async function startDownload(botId, payload) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/download-data/start`,
    payload
  )
  return data
}

/** ★ 查询下载进度 */
export async function getDownloadProgress(botId, jobId) {
  const { data } = await axios.get(
    `${API}/bots/${botId}/download-data/progress/${jobId}`
  )
  return data
}

/** ★ 取消下载 */
export async function cancelDownload(botId, jobId) {
  const { data } = await axios.post(
    `${API}/bots/${botId}/download-data/cancel/${jobId}`
  )
  return data
}