# freqtrade/user_data/strategies/GridScanner.py
import ccxt
import pandas as pd
import numpy as np
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 参数配置
# ==========================================
TOP_N_BY_VOLUME = 100  # 只选 24h 成交额前 100 的币
TIMEFRAME = '4h'  # 观察周期（4小时线更适合网格）
LIMIT = 90  # 拉取过去 90 根 K 线
MIN_ATR_PCT = 3.0  # 波动率门槛 (ATR / Price > 3%)
HURST_THRESHOLD = 0.5  # 均值回归门槛 (Hurst < 0.5 为震荡)
ADX_THRESHOLD = 25  # 趋势强度门槛 (ADX < 25 为无趋势)

# ★ 新增：目标挑选数量
TARGET_LONG_COUNT = 3  # 最终想要挑选几个做多
TARGET_SHORT_COUNT = 3  # 最终想要挑选几个做空

# 终端颜色代码
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

# 初始化交易所 (Binance 合约)
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})


# ==========================================
# 2. 数学指标计算函数
# ==========================================
def calculate_hurst(price_series):
    try:
        lags = range(2, min(20, len(price_series) // 2))
        tau = [np.std(np.subtract(price_series[lag:], price_series[:-lag])) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0]
    except Exception:
        return 0.5


def calculate_adx(df, period=14):
    try:
        high = df['high']
        low = df['low']
        close = df['close']
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
        minus_di = abs(100 * (minus_dm.ewm(alpha=1 / period).mean() / atr))
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(period).mean()
        return adx.iloc[-1]
    except Exception:
        return 50.0


def calculate_rsi(df, period=14):
    try:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
    except Exception:
        return 50.0


# ==========================================
# 3. 核心逻辑
# ==========================================
def fetch_top_symbols():
    print(f"{CYAN}正在获取市场行情，筛选成交额前 {TOP_N_BY_VOLUME} 的币种...{RESET}")
    exchange.load_markets()
    tickers = exchange.fetch_tickers()
    usdt_futures = []
    for symbol, ticker in tickers.items():
        if symbol.endswith(':USDT') and ticker['quoteVolume']:
            usdt_futures.append({
                'symbol': symbol,
                'volume': ticker['quoteVolume'],
                'price': ticker['last']
            })
    usdt_futures.sort(key=lambda x: x['volume'], reverse=True)
    return [item['symbol'] for item in usdt_futures[:TOP_N_BY_VOLUME]]


def analyze_symbol(symbol):
    """对单个币种进行多因子分析 (不再直接输出方向，而是返回所有指标和基础得分)"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=LIMIT)
        if len(ohlcv) < 50: return None

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        closes = df['close'].values
        current_price = closes[-1]

        # 1. 波动率
        tr = np.maximum(df['high'] - df['low'],
                        np.maximum(abs(df['high'] - df['close'].shift()),
                                   abs(df['low'] - df['close'].shift())))
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / current_price) * 100

        # 2. 震荡稳定性
        hurst = calculate_hurst(closes)
        adx = calculate_adx(df)

        # 3. 相对位置
        mean_price = np.mean(closes)
        std_price = np.std(closes)
        z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
        rsi = calculate_rsi(df)

        # 基础过滤：波动太小，或者趋势太强（不适合网格）的币直接丢弃
        if atr_pct < MIN_ATR_PCT: return None
        if hurst > HURST_THRESHOLD: return None
        if adx > ADX_THRESHOLD: return None

        # 计算震荡和波动的“基础得分”
        base_score = 0
        base_score += min(30, atr_pct * 3)  # 波动得分 (0-30)
        base_score += (HURST_THRESHOLD - hurst) * 80  # 稳定性得分
        base_score += max(0, (ADX_THRESHOLD - adx) * 1.5)  # 无趋势得分

        return {
            'symbol': symbol,
            'price': current_price,
            'base_score': round(base_score, 2),
            'atr_pct': round(atr_pct, 2),
            'hurst': round(hurst, 3),
            'adx': round(adx, 2),
            'z_score': round(z_score, 2),
            'rsi': round(rsi, 2)
        }
    except Exception:
        return None


def select_candidates(pool, target_count, direction):
    """
    智能挑选器：优先挑绝对位置符合的，如果不够，自动放宽条件补齐
    """
    selected = []
    used_symbols = set()

    # 根据不同方向定义不同的阈值层级
    if direction == 'LONG':
        # 做多层级：(Z-score阈值, RSI阈值, 分数权重)
        tiers = [
            (-1.2, 40, 30),  # 第一梯队：极佳超卖
            (-0.8, 45, 20),  # 第二梯队：轻微超卖
            (-0.4, 50, 10),  # 第三梯队：接近均值，勉强能进
            (-9.9, 99, 0)  # 第四梯队：不要命的补位（所有震荡币）
        ]
    else:
        # 做空层级：(Z-score阈值, RSI阈值, 分数权重)
        tiers = [
            (1.2, 60, 30),
            (0.8, 55, 20),
            (0.4, 50, 10),
            (99, 0, 0)
        ]

    for z_thresh, rsi_thresh, weight in tiers:
        if len(selected) >= target_count:
            break

        # 遍历池子找符合条件的
        tier_candidates = []
        for c in pool:
            if c['symbol'] in used_symbols:
                continue

            is_match = False
            if direction == 'LONG':
                if c['z_score'] < z_thresh and c['rsi'] < rsi_thresh:
                    is_match = True
            else:
                if c['z_score'] > z_thresh and c['rsi'] > rsi_thresh:
                    is_match = True

            if is_match:
                # 计算最终得分 = 基础分 + 偏离度得分
                final_score = c['base_score'] + min(30, abs(c['z_score']) * 10 * (1 if weight > 0 else 0))
                c_copy = c.copy()
                c_copy['score'] = round(final_score, 2)
                c_copy['direction'] = direction
                # 如果选了低配版，打个星号标注
                c_copy['is_fallback'] = (weight < 30)
                tier_candidates.append(c_copy)

        # 将此梯队按分数降序排
        tier_candidates.sort(key=lambda x: x['score'], reverse=True)

        # 取所需数量
        need = target_count - len(selected)
        selected.extend(tier_candidates[:need])
        for item in selected:
            used_symbols.add(item['symbol'])

    return selected


def main():
    start_time = time.time()
    symbols = fetch_top_symbols()
    print(f"开始分析 {len(symbols)} 个币种的多因子数据...")

    all_valid_pool = []

    for i, symbol in enumerate(symbols):
        print(f"\r进度: {i + 1}/{len(symbols)} | 正在计算: {symbol.ljust(20)}", end="", flush=True)
        result = analyze_symbol(symbol)
        if result:
            all_valid_pool.append(result)
        time.sleep(exchange.rateLimit / 1000)

    print("\n\n" + "=" * 80)
    print(f"{CYAN}           网格多因子选币雷达 (目标: {TARGET_LONG_COUNT}多 / {TARGET_SHORT_COUNT}空) {RESET}")
    print("=" * 80)

    # ★ 执行智能挑选
    final_longs = select_candidates(all_valid_pool, TARGET_LONG_COUNT, 'LONG')
    final_shorts = select_candidates(all_valid_pool, TARGET_SHORT_COUNT, 'SHORT')

    # 打印做多推荐
    print(f"\n{GREEN}【做多推荐】 (共 {len(final_longs)} 个){RESET}")
    print("-" * 80)
    print(
        f"{'币种':<15} | {'评分':<5} | {'波动率':<8} | {'Hurst':<6} | {'ADX':<6} | {'Z-Score':<8} | {'RSI':<6} | {'状态'}")
    print("-" * 80)
    for c in final_longs:
        status = f"{YELLOW}补位{RESET}" if c['is_fallback'] else f"{GREEN}极佳{RESET}"
        print(
            f"{c['symbol']:<15} | {c['score']:<5} | {c['atr_pct']:<6}% | {c['hurst']:<6} | {c['adx']:<6} | {c['z_score']:<8} | {c['rsi']:<6} | {status}")

    # 打印做空推荐
    print(f"\n{RED}【做空推荐】 (共 {len(final_shorts)} 个){RESET}")
    print("-" * 80)
    print(
        f"{'币种':<15} | {'评分':<5} | {'波动率':<8} | {'Hurst':<6} | {'ADX':<6} | {'Z-Score':<8} | {'RSI':<6} | {'状态'}")
    print("-" * 80)
    for c in final_shorts:
        status = f"{YELLOW}补位{RESET}" if c['is_fallback'] else f"{RED}极佳{RESET}"
        print(
            f"{c['symbol']:<15} | {c['score']:<5} | {c['atr_pct']:<6}% | {c['hurst']:<6} | {c['adx']:<6} | {c['z_score']:<8} | {c['rsi']:<6} | {status}")

    print(f"\n{YELLOW}筛选完成，共耗时 {round(time.time() - start_time, 1)} 秒。{RESET}")
    print("=" * 80)


if __name__ == "__main__":
    main()