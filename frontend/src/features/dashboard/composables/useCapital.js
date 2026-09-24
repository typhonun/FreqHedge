import axios from "axios"
import { ref } from "vue"

const API = "http://localhost:9000"

export function useCapital() {

    const longConfig = ref({})
    const shortConfig = ref({})

    const longWhitelist = ref("")
    const longBlacklist = ref("")

    const shortWhitelist = ref("")
    const shortBlacklist = ref("")

    // 加载时的原始快照，用于判断是否有改动
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
            max_usage: longData.max_usage,
            leverage: longData.leverage ?? 10,

            imbalance_long_enable: longData.imbalance_long_enable ?? false,
            imbalance_long_count: longData.imbalance_long_count ?? 2,
        }

        shortConfig.value = {
            dry_run_wallet: shortData.dry_run_wallet,
            stake_amount: shortData.stake_amount,
            max_open_trades: shortData.max_open_trades,
            max_usage: shortData.max_usage,
            leverage: shortData.leverage ?? 10,

            imbalance_short_enable: shortData.imbalance_short_enable ?? false,
            imbalance_short_count: shortData.imbalance_short_count ?? 2,
        }

        longWhitelist.value = (longData.pair_whitelist || []).join("\n")
        longBlacklist.value = (longData.pair_blacklist || []).join("\n")

        shortWhitelist.value = (shortData.pair_whitelist || []).join("\n")
        shortBlacklist.value = (shortData.pair_blacklist || []).join("\n")

        // 记录快照
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

    /**
     * 判断当前是否有改动
     * @returns {boolean}
     */
    const hasChanges = (side) => {
        const isLong = side === "long"
        const config = isLong ? longConfig.value : shortConfig.value
        const whitelist = isLong ? longWhitelist.value : shortWhitelist.value
        const blacklist = isLong ? longBlacklist.value : shortBlacklist.value
        const snapshot = isLong ? longSnapshot.value : shortSnapshot.value

        if (!snapshot) return true  // 没快照，强制走保存

        return _buildSnapshot(config, whitelist, blacklist) !== snapshot
    }

    const saveConfig = async (side) => {
        const isLong = side === "long"

        // 无改动直接返回
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

            pair_whitelist: (isLong ? longWhitelist.value : shortWhitelist.value)
                .split("\n").filter(Boolean),

            pair_blacklist: (isLong ? longBlacklist.value : shortBlacklist.value)
                .split("\n").filter(Boolean)
        }

        const res = await axios.post(`${API}/control/config`, payload)

        // 保存成功后刷新快照，避免重复提交
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
        hasChanges
    }
}