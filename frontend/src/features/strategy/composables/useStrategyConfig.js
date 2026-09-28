import axios from "axios"
import {ref, computed} from "vue"
import { ElMessage } from "element-plus"

const API = "http://localhost:9000"

const roiLevels = [
    { minutes: 1440, roi: 0 },
    { minutes: 720, roi: 2 },
    { minutes: 480, roi: 4 },
    { minutes: 360, roi: 6 },
    { minutes: 300, roi: 8 },
    { minutes: 240, roi: 10 },
    { minutes: 210, roi: 12 },
    { minutes: 180, roi: 14 },
    { minutes: 150, roi: 16 },
    { minutes: 120, roi: 18 },
    { minutes: 100, roi: 20 },
    { minutes: 80, roi: 22 },
    { minutes: 60, roi: 24 },
    { minutes: 40, roi: 26 },
    { minutes: 20, roi: 28 },
    { minutes: 0, roi: 30 }
]

const isPlainObject = (v) =>
    v !== null && typeof v === "object" && !Array.isArray(v)

/**
 * 深合并 default 与 incoming。
 * 规则：
 *  - incoming 中的数组 → 整体替换 default
 *  - incoming 中的对象 → 递归合并
 *  - incoming 中的原始值 → 覆盖 default
 *  - incoming 中不存在的 key → 保留 default
 */
const mergeConfig = (defaults, incoming) => {
    if (!isPlainObject(defaults) || !isPlainObject(incoming)) {
        return incoming === undefined ? defaults : incoming
    }

    const result = { ...defaults }

    for (const key of Object.keys(incoming)) {
        const dv = defaults[key]
        const iv = incoming[key]

        if (Array.isArray(iv)) {
            result[key] = iv
        } else if (isPlainObject(dv) && isPlainObject(iv)) {
            result[key] = mergeConfig(dv, iv)
        } else {
            result[key] = iv
        }
    }

    return result
}

const buildTradeInfo = (side, config) => {

    const isLong = side === "long"

    const roiLevels = config.tp?.enable
        ? config.tp.roi_levels || []
        : []


    return {

        side,

        direction: isLong
            ? "仅做多"
            : "仅做空",


        timeframe:
            config.timeframe || "30m",


        leverage:
            `${config.leverage || 10}x`,


        stoploss:
            config.sl?.enable
                ? `${config.sl.stoploss}%`
                : null,



        // 开仓逻辑
        entrySignal: (() => {
            const signals = []

            if (config.entry?.bb?.enable) {
                signals.push("Bollinger")
            }

            if (config.entry?.rsi?.enable) {
                signals.push(
                    isLong
                        ? `RSI < ${config.entry.rsi.value}`
                        : `RSI > ${config.entry.rsi.value}`
                )
            }

            if (config.entry?.macd?.enable) {
                signals.push("MACD")
            }

            if (!signals.length) return null

            const mode = config.entry?.condition || "and"
            const joiner = mode === "or" ? " 或 " : " + "

            return signals.join(joiner)
        })(),

        // Pump 保护兜底
        pumpProtectSignal:
            config.entry?.pump_protect?.enable
                ? "Pump 保护：开启"
                : null,



        // TP减仓
        tpSignal: config.tp?.enable
            ? (() => {
                if (!config.tp.rebuy_enable) {
                    return "不补仓，触发 TP 后全平"
                }
                if (config.amount_mode === "amount") {
                    return `减仓 ${config.tp.reduce_amount} USDT，加仓至 ${config.tp.target_wallet_amount} USDT`
                }
                return `减仓仓位大小 ${config.tp.reduce_percent}%，加仓总资金 ${config.tp.target_wallet_percent}%`
            })()
            : null,


        // 浮亏止盈
        lossTpSignal: (() => {
            if (!config.loss_tp?.enable) {
                return null
            }

            if (config.loss_tp.close_all) {
                return `全平，反弹止盈 ${config.loss_tp.dca_tp_profit}%`
            }

            if (config.amount_mode === "amount") {
                return `减仓至 ${config.loss_tp.target_wallet_amount} USDT，反弹止盈 ${config.loss_tp.dca_tp_profit}%`
            }

            return `目标仓位 ${config.loss_tp.target_wallet_percent}%，反弹止盈 ${config.loss_tp.dca_tp_profit}%`
        })(),


        trendSignal: (() => {
            if (!config.trend_add?.enable) return null

            const list = []
            if (config.trend_add.macd_enable) list.push("MACD")
            if (config.trend_add.kdj_enable) list.push("KDJ")
            if (config.trend_add.ema_enable) list.push("EMA")

            const cond = list.length ? list.join(" + ") : null
            if (!cond) return null

            const amountText = config.amount_mode === "amount"
                ? `加仓 ${config.trend_add.amount_amount} USDT`
                : `加仓 ${config.trend_add.amount_percent}%`

            return `${cond}，${amountText}`
        })(),


        dcaSignal: (() => {
            if (!config.dca?.enable) return null

            const d = config.dca
            const dcaMode = d.amount_mode || "auto"
            const globalMode = config.amount_mode || "percent"

            if (dcaMode === "auto") {
                if (globalMode === "amount") {
                    return `最多 ${d.max_count} 次，自动模式 基础 ${d.base_amount} USDT × ${d.amount_multiplier}^n，` +
                           `价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
                }
                return `最多 ${d.max_count} 次，自动模式 基础 ${d.base_percent}% × ${d.amount_multiplier}^n，` +
                       `价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
            }

            // manual
            if (globalMode === "amount") {
                return `最多 ${d.max_count} 次，手动分层 ${d.levels?.length || 0} 层（金额 USDT），` +
                       `价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
            }
            return `最多 ${d.max_count} 次，手动分层 ${d.levels?.length || 0} 层（百分比），` +
                   `价格下跌步骤 ${d.price_offset}%，价格偏差 ${d.price_multiplier}`
        })(),


        gridSignal:
            config.grid?.enable
                ? (() => {
                    const buyText = config.amount_mode === "amount"
                        ? `加仓 ${config.grid.buy_amount} USDT`
                        : `加仓 ${config.grid.buy_percent}%`

                    const sellText = config.amount_mode === "amount"
                        ? `减仓 ${config.grid.sell_amount} USDT`
                        : `减仓 ${config.grid.sell_percent}%`

                    return `网格下沿 ${config.grid.grid_lower}% ${buyText}，` +
                           `网格上沿 ${config.grid.grid_upper}% ${sellText}，` +
                           `订单规模 ${config.grid.order_scale}`
                })()
                : null,

        pairMaxPositionSignal:
            config.pair_max_position?.enable
                ? `单交易对持仓上限 ${config.pair_max_position.percent}%（超限停止 DCA 与网格加仓）`
                : null,

        timeStopSignal: (() => {
            if (!config.sl?.time_stop?.enable) return null
            const ts = config.sl.time_stop
            const modeText = ts.mode === "amount" ? "USDT" : "%"
            return `${ts.hours.toFixed(1)}h 未成交且收益 < ${ts.profit_threshold}${modeText} 触发`
        })(),

        htfTrendSignal: (() => {
            if (!config.htf_trend_filter?.enable) return null
            const h = config.htf_trend_filter
            const parts = []
            if (h.protect_entry) parts.push("开仓")
            if (h.protect_dca) parts.push("DCA")
            if (h.protect_grid) parts.push("网格")
            if (h.protect_rebuy) parts.push("浮盈回补")
            if (h.protect_trend) parts.push("趋势加仓")
            const protectText = parts.length ? parts.join(" / ") : "无"
            const dirText = isLong ? "空头排列" : "多头排列"
            return `${h.timeframe} ${dirText} 时暂停：${protectText}`
        })(),


        roiLevels:

            roiLevels.map(level=>({

                label:
                    `${level.minutes}m / ${level.roi}%`

            }))


    }
}

const defaultLongConfig = () => ({
    side: "long",

    timeframe:"30m",

    // 全局金额模式
    amount_mode: "percent",

    entry:{

        condition: "and",

        rsi:{
            enable:true,

            // RSI入场阈值
            value:35
        },


        macd:{
            enable:true
        },


        bb:{
            enable:true
        },

        pump_protect: {
            enable: false
        }

    },

    tp: {
        enable: true,
        roi_levels: roiLevels.map((level) => ({
            minutes: level.minutes,
            roi: level.roi
        })),
        reduce_percent: 30,
        reduce_amount: 10.0,
        rebuy_enable: true,
        target_wallet_percent: 5,
        target_wallet_amount: 50.0
    },

    sl: {
        enable: true,
        stoploss: -9,

        time_stop: {
            enable: false,
            hours: 24.0,
            profit_threshold: -5.0,
            mode: "percent"
        }
    },

    // 单交易对最大持仓限制（占总资金百分比）
    pair_max_position: {
        enable: false,
        percent: 30
    },

    // HTF 趋势过滤
    htf_trend_filter: {
        enable: false,
        timeframe: "4h",
        protect_entry: false,
        protect_dca: true,
        protect_grid: true,
        protect_rebuy: true,
        protect_trend: false
    },

    indicator:{


        rsi:{
            period:14
        },


        bb:{
            period:20,
            std:2
        },


        macd:{
            fast:12,
            slow:26,
            signal:9
        },


        kdj:{
            fastk:5,
            slowk:3,
            slowd:3
        },


        ema:{
            fast:9,
            mid:21,
            slow:99
        }

    },

    trend_add:{

        enable:false,

        amount_percent:0.5,

        amount_amount: 10.0,

        condition:"and",


        macd_enable:true,

        kdj_enable:true,

        ema_enable:true,


        kdj_reduce:{
            enable:false,
            reduce_percent:50,
            reduce_amount: 10.0
        }

    },

    dca: {
        enable: true,
        max_count: 7,
        condition: "or",
        cooldown_minutes: 60,

        // 新增：金额模式，"auto" 或 "manual"
        amount_mode: "auto",

        // 自动模式用
        base_percent: 2,
        base_amount: 10.0,
        amount_multiplier: 1.5,

        // 价格触发
        price_offset: 1.0,
        price_multiplier: 1.5,

        // 手动模式用
        levels: [
            {
                amount: 100,
                percent: 2.0,
                rsi_limit: 25,
                j_limit: 10
            }
        ]
    },
    loss_tp:{
        enable:true,
        dca_tp_profit:3,
        close_all: false,
        target_wallet_percent:5,
        target_wallet_amount: 50.0
    },
    grid: {
        enable: true,
        max_count: 5,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        buy_amount: 10.0,
        sell_percent: 2,
        sell_amount: 10.0,
        order_scale: 1,
        cooldown_minutes: 30
    }
})

const defaultShortConfig = () => ({
    side: "short",

    timeframe: "30m",

    amount_mode: "percent",

    entry:{

        condition: "and",

        rsi:{
            enable:true,

            // RSI入场阈值
            value:65
        },


        macd:{
            enable:true
        },


        bb:{
            enable:true
        },

        pump_protect: {
            enable: false
        }

    },

    tp: {
        enable: true,
        roi_levels: roiLevels.map((level) => ({
            minutes: level.minutes,
            roi: level.roi
        })),
        reduce_percent: 30,
        reduce_amount: 10.0,
        rebuy_enable: true,
        target_wallet_percent: 5,
        target_wallet_amount: 50.0
    },

    sl: {
        enable: true,
        stoploss: -9,
        time_stop: {
            enable: false,
            hours: 24.0,
            profit_threshold: -5.0,
            mode: "percent"
        }
    },

    pair_max_position: {
        enable: false,
        percent: 30
    },

    // HTF 趋势过滤
    htf_trend_filter: {
        enable: false,
        timeframe: "4h",
        protect_entry: false,
        protect_dca: true,
        protect_grid: true,
        protect_rebuy: true,
        protect_trend: false
    },

    indicator:{


        rsi:{
            period:14
        },


        bb:{
            period:20,
            std:2
        },


        macd:{
            fast:12,
            slow:26,
            signal:9
        },


        kdj:{
            fastk:5,
            slowk:3,
            slowd:3
        },


        ema:{
            fast:9,
            mid:21,
            slow:99
        }

    },


    trend_add:{

        enable:false,

        amount_percent:0.5,

        amount_amount: 10.0,

        condition:"and",

        macd_enable:true,

        kdj_enable:true,

        ema_enable:true,


        kdj_reduce:{
            enable:false,
            reduce_percent:50,
            reduce_amount: 10.0
        }

    },

    dca: {
        enable: true,
        max_count: 7,
        condition: "or",
        cooldown_minutes: 60,

        // 新增：金额模式，"auto" 或 "manual"
        amount_mode: "auto",

        // 自动模式用
        base_percent: 2,
        amount_multiplier: 1.5,
        base_amount: 10.0,

        // 价格触发
        price_offset: 1.0,
        price_multiplier: 1.5,

        // 手动模式用
        levels: [
            {
                amount: 100,
                percent: 2.0,
                rsi_limit: 25,
                j_limit: 10
            }
        ]
    },
    loss_tp:{
        enable:true,

        dca_tp_profit:3,

        close_all: false,

        target_wallet_percent:5,

        target_wallet_amount: 50.0
    },

    grid: {
        enable: true,
        max_count: 5,
        grid_lower: -2,
        grid_upper: 2,
        buy_percent: 2,
        buy_amount: 10.0,
        sell_percent: 2,
        sell_amount: 10.0,
        order_scale: 1,
        cooldown_minutes: 30
    }
})

export function getDefaultLongConfig() {
    return JSON.parse(JSON.stringify(defaultLongConfig()))
}

export function getDefaultShortConfig() {
    return JSON.parse(JSON.stringify(defaultShortConfig()))
}

export function useStrategyConfig() {

const longConfig = ref(
    defaultLongConfig()
)

const shortConfig = ref(
    defaultShortConfig()
)


// 保存后的配置快照
const savedLongConfig = ref(
    JSON.parse(
        JSON.stringify(longConfig.value)
    )
)

const savedShortConfig = ref(
    JSON.parse(
        JSON.stringify(shortConfig.value)
    )
)



const longTradeInfo = computed(()=>{

    return buildTradeInfo(
        "long",
        savedLongConfig.value
    )

})


const shortTradeInfo = computed(()=>{

    return buildTradeInfo(
        "short",
        savedShortConfig.value
    )

})

const normalizeDca = (config) => {
    if (!config || !config.dca) return config

    if (!config.dca.amount_mode) {
        config.dca.amount_mode = "auto"
    }

    if (config.dca.base_percent == null) {
        config.dca.base_percent = 2
    }

    if (config.dca.base_amount == null) {          // 新增
        config.dca.base_amount = 100.0
    }

    if (!config.dca.amount_multiplier) {
        config.dca.amount_multiplier = 1.5
    }

        // levels 兜底
    if (Array.isArray(config.dca.levels)) {        // 新增
        config.dca.levels.forEach((level) => {
            if (level.amount == null) {
                level.amount = 100
            }
            if (level.percent == null) {
                level.percent = 2.0
            }
        })
    }

    return config
}

const normalizeAmountMode = (config) => {
    if (!config) return config

    if (!config.amount_mode) {
        config.amount_mode = "percent"
    }

    // trend_add.amount_amount
    if (config.trend_add && config.trend_add.amount_amount == null) {
        config.trend_add.amount_amount = 10.0
    }

    // grid.buy_amount / sell_amount
    if (config.grid) {
        if (config.grid.buy_amount == null) {
            config.grid.buy_amount = 10.0
        }
        if (config.grid.sell_amount == null) {
            config.grid.sell_amount = 10.0
        }
    }

    // 新增：tp.reduce_amount / target_wallet_amount
    if (config.tp) {
        if (config.tp.reduce_amount == null) {
            config.tp.reduce_amount = 10.0
        }
        if (config.tp.target_wallet_amount == null) {
            config.tp.target_wallet_amount = 50.0
        }
    }

    // 新增：loss_tp.target_wallet_amount
    if (config.loss_tp) {
        if (config.loss_tp.target_wallet_amount == null) {
            config.loss_tp.target_wallet_amount = 50.0
        }
    }

    // 时间止损兜底
    if (config.sl) {
        if (!config.sl.time_stop) {
            config.sl.time_stop = {
                enable: false,
                hours: 24.0,
                profit_threshold: -5.0,
                mode: "percent"
            }
        }
        if (config.sl.time_stop.enable == null) {
            config.sl.time_stop.enable = false
        }
        if (config.sl.time_stop.hours == null) {
            config.sl.time_stop.hours = 24.0
        }
        if (config.sl.time_stop.profit_threshold == null) {
            config.sl.time_stop.profit_threshold = -5.0
        }
        if (!config.sl.time_stop.mode) {
            config.sl.time_stop.mode = "percent"
        }
    }

    // loss_tp.close_all
    if (config.loss_tp && config.loss_tp.close_all == null) {
        config.loss_tp.close_all = false
    }

    // 新增：trend_add.kdj_reduce.reduce_amount
    if (config.trend_add && config.trend_add.kdj_reduce) {
        if (config.trend_add.kdj_reduce.reduce_amount == null) {
            config.trend_add.kdj_reduce.reduce_amount = 10.0
        }
    }

    // 单交易对最大持仓限制兜底
    if (!config.pair_max_position) {
        config.pair_max_position = { enable: false, percent: 30 }
    }
    if (config.pair_max_position.enable == null) {
        config.pair_max_position.enable = false
    }
    if (config.pair_max_position.percent == null) {
        config.pair_max_position.percent = 30
    }

    // HTF 趋势过滤兜底
    if (!config.htf_trend_filter) {
        config.htf_trend_filter = {
            enable: false,
            timeframe: "4h",
            protect_entry: false,
            protect_dca: true,
            protect_grid: true,
            protect_rebuy: true,
            protect_trend: false
        }
    }
    if (config.htf_trend_filter.enable == null) config.htf_trend_filter.enable = false
    if (!config.htf_trend_filter.timeframe) config.htf_trend_filter.timeframe = "4h"
    if (config.htf_trend_filter.protect_entry == null) config.htf_trend_filter.protect_entry = false
    if (config.htf_trend_filter.protect_dca == null) config.htf_trend_filter.protect_dca = true
    if (config.htf_trend_filter.protect_grid == null) config.htf_trend_filter.protect_grid = true
    if (config.htf_trend_filter.protect_rebuy == null) config.htf_trend_filter.protect_rebuy = true
    if (config.htf_trend_filter.protect_trend == null) config.htf_trend_filter.protect_trend = false

    // timeframe 兜底
    if (!config.timeframe) {
        config.timeframe = "30m"
    }
    return config
}

const normalizeEntry = (config) => {
    if (!config) return config
    if (!config.entry) return config
    if (!config.entry.condition) {
        config.entry.condition = "and"
    }

    // 新增：Pump 保护兜底
    if (!config.entry.pump_protect) {
        config.entry.pump_protect = { enable: false }
    }
    if (config.entry.pump_protect.enable == null) {
        config.entry.pump_protect.enable = false
    }

    return config
}

const loadConfig = async () => {
    const res = await axios.get(`${API}/strategy/`)

    longConfig.value = normalizeEntry(
        normalizeAmountMode(
            normalizeDca(
                mergeConfig(defaultLongConfig(), res.data.long)
            )
        )
    )

    shortConfig.value = normalizeEntry(
        normalizeAmountMode(
            normalizeDca(
                mergeConfig(defaultShortConfig(), res.data.short)
            )
        )
    )

    savedLongConfig.value = JSON.parse(
        JSON.stringify(longConfig.value)
    )

    savedShortConfig.value = JSON.parse(
        JSON.stringify(shortConfig.value)
    )
}

    /**
     * 判断当前 config 与已保存快照是否有差异
     */
    const hasChanges = (side, config) => {
        const saved = side === "long"
            ? savedLongConfig.value
            : savedShortConfig.value

        if (!saved) return true

        return JSON.stringify(config) !== JSON.stringify(saved)
    }

    const saveConfig = async (side, config) => {

        // 开仓信号校验（保留原逻辑）
        if (
            !config.entry.rsi.enable &&
            !config.entry.macd.enable &&
            !config.entry.bb.enable
        ) {
            ElMessage.error("开仓信号不能为空")
            return { changed: false, error: "entry_empty" }
        }

        // 无改动：不提交、不重载
        if (!hasChanges(side, config)) {
            return { changed: false }
        }

        const res = await axios.post(
            `${API}/strategy/`,
            {
                side,
                config,
                ...config          // ← 同时平铺一份，兼容后端读顶层字段
            }
)

        // 保存成功后更新快照
        if (side === "long") {
            savedLongConfig.value = JSON.parse(JSON.stringify(config))
        }

        if (side === "short") {
            savedShortConfig.value = JSON.parse(JSON.stringify(config))
        }

        return { changed: true, data: res.data }
    }

    return {
        longConfig,
        shortConfig,

        savedLongConfig,
        savedShortConfig,

        longTradeInfo,
        shortTradeInfo,

        loadConfig,
        saveConfig,
        hasChanges
    }
}