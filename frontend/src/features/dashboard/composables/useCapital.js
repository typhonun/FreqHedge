import axios from "axios"
import { ref } from "vue"

const API = "http://localhost:9000"

// ★ 后端 API max_usage 是百分数（90），前端内部统一用小数（0.9）
const _apiToLocal = (v) => {
    const n = Number(v)
    if (!isFinite(n) || n <= 0) return 0.9
    return n / 100
}

export function useCapital() {

    const longConfig = ref({})
    const shortConfig = ref({})

    const longWhitelist = ref("")
    const longBlacklist = ref("")

    const shortWhitelist = ref("")
    const shortBlacklist = ref("")

    const longSnapshot = ref(null)
    const shortSnapshot = ref(null)

    const _normalizeList = (text) =>
        String(text || "")
            .split("\n")
            .map(s => s.trim())
            .filter(Boolean)

    const _buildSnapshot = (config, whitelist, blacklist) => {
        return JSON.stringify({
            dry_run_wallet: config.dry_run_wallet ?? null,
            stake_amount: config.stake_amount ?? null,
            max_open_trades: config.max_open_trades ?? null,
            max_usage: config.max_usage ?? null,
            leverage: config.leverage ?? null,
            imbalance_long_enable: config.imbalance_long_enable ?? null,
            imbalance_long_count: config.imbalance_long_count ?? null,
            imbalance_short_enable: config.imbalance_short_enable ?? null,
            imbalance_short_count: config.imbalance_short_count ?? null,
            pair_whitelist: _normalizeList(whitelist),
            pair_blacklist: _normalizeList(blacklist),
        })
    }

    const loadConfig = async () => {
        const res = await axios.get(`${API}/control/config`)

        const longData = res.data.long || {}
        const shortData = res.data.short || {}

        longConfig.value = {
            dry_run_wallet: longData.dry_run_wallet,
            stake_amount: longData.stake_amount,
            max_open_trades: longData.max_open_trades,
            max_usage: _apiToLocal(longData.max_usage),   // ★ 90 → 0.9
            leverage: longData.leverage ?? 1,

            imbalance_long_enable: longData.imbalance_long_enable ?? false,
            imbalance_long_count: longData.imbalance_long_count ?? 2,
        }

        shortConfig.value = {
            dry_run_wallet: shortData.dry_run_wallet,
            stake_amount: shortData.stake_amount,
            max_open_trades: shortData.max_open_trades,
            max_usage: _apiToLocal(shortData.max_usage),  // ★ 90 → 0.9
            leverage: shortData.leverage ?? 1,

            imbalance_short_enable: shortData.imbalance_short_enable ?? false,
            imbalance_short_count: shortData.imbalance_short_count ?? 2,
        }

        longWhitelist.value = (longData.pair_whitelist || []).join("\n")
        longBlacklist.value = (longData.pair_blacklist || []).join("\n")

        shortWhitelist.value = (shortData.pair_whitelist || []).join("\n")
        shortBlacklist.value = (shortData.pair_blacklist || []).join("\n")

        longSnapshot.value = _buildSnapshot(
            longConfig.value,
            longWhitelist.value,
            longBlacklist.value
        )
        shortSnapshot.value = _buildSnapshot(
            shortConfig.value,
            shortWhitelist.value,
            shortBlacklist.value
        )
    }

    const hasChanges = (side) => {
        const isLong = side === "long"
        const config = isLong ? longConfig.value : shortConfig.value
        const whitelist = isLong ? longWhitelist.value : shortWhitelist.value
        const blacklist = isLong ? longBlacklist.value : shortBlacklist.value
        const snapshot = isLong ? longSnapshot.value : shortSnapshot.value

        if (!snapshot) return true

        return _buildSnapshot(config, whitelist, blacklist) !== snapshot
    }

    // ★ 开仓金额上限（保证金口径，不乘杠杆）
    const maxStakeAmount = (side) => {
        const isLong = side === "long"
        const config = isLong ? longConfig.value : shortConfig.value
        const wallet = Number(config.dry_run_wallet ?? 0)
        const usage = Number(config.max_usage ?? 0)   // 已是小数
        if (!isFinite(wallet) || !isFinite(usage)) return 0
        return wallet * usage
    }

    // ★ 资金约束校验
    const validateCapital = (side) => {
        const isLong = side === "long"
        const config = isLong ? longConfig.value : shortConfig.value

        const wallet = Number(config.dry_run_wallet ?? 0)
        const usage = Number(config.max_usage ?? 0)
        const stake = Number(config.stake_amount ?? 0)

        if (!isFinite(wallet) || wallet <= 0) {
            return { ok: false, message: "初始资金必须大于 0" }
        }
        if (!isFinite(usage) || usage <= 0 || usage > 1) {
            return { ok: false, message: "资金利用率必须在 0.01 ~ 1.00 之间" }
        }

        const maxStake = wallet * usage

        if (!isFinite(stake) || stake <= 0) {
            return { ok: false, message: "开仓金额必须大于 0" }
        }
        if (stake > maxStake) {
            return {
                ok: false,
                message: `开仓金额 ${stake} USDT 超过上限 ${maxStake.toFixed(2)} USDT（初始资金 × 资金利用率）`
            }
        }

        return { ok: true }
    }

    const saveConfig = async (side) => {
        const isLong = side === "long"

        const v = validateCapital(side)
        if (!v.ok) {
            return { changed: false, error: v.message }
        }

        if (!hasChanges(side)) {
            return { changed: false }
        }

        const config = isLong ? longConfig.value : shortConfig.value

        const imbalance = isLong
            ? {
                imbalance_long_enable: config.imbalance_long_enable,
                imbalance_long_count: config.imbalance_long_count,
            }
            : {
                imbalance_short_enable: config.imbalance_short_enable,
                imbalance_short_count: config.imbalance_short_count,
            }

        const payload = {
            side,
            ...config,
            ...imbalance,

            // ★ 前端小数 0.9 → 后端百分数 90
            max_usage: config.max_usage * 100,

            pair_whitelist: (isLong ? longWhitelist.value : shortWhitelist.value)
                .split("\n").filter(Boolean),

            pair_blacklist: (isLong ? longBlacklist.value : shortBlacklist.value)
                .split("\n").filter(Boolean)
        }

        const res = await axios.post(`${API}/control/config`, payload)

        if (isLong) {
            longSnapshot.value = _buildSnapshot(
                longConfig.value,
                longWhitelist.value,
                longBlacklist.value
            )
        } else {
            shortSnapshot.value = _buildSnapshot(
                shortConfig.value,
                shortWhitelist.value,
                shortBlacklist.value
            )
        }

        return { changed: true, data: res.data }
    }

    return {
        longConfig,
        shortConfig,
        longWhitelist,
        longBlacklist,
        shortWhitelist,
        shortBlacklist,
        loadConfig,
        saveConfig,
        hasChanges,
        maxStakeAmount,
        validateCapital,
    }
}