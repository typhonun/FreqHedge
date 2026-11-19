# backend/app/services/grid_scanner.py
import ccxt
import pandas as pd
import numpy as np
import time
import threading
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GridScanner:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.timeframe = '4h'
        self.limit = 90
        self._cache_lock = threading.Lock()
        self._range_cache = {}
        # 股指代币、ETF、股票代币黑名单（只交易传统加密货币）
        self._stock_blacklist = {
            'AAOI', 'TQQQ', 'SQQQ', 'SOXS', 'KORU', 'SPY', 'QQQ', 'NVDA',
            'TSLA', 'AAPL', 'MSFT', 'SKHYNIX', 'AMD', 'INTC', 'GOOGL',
            'META', 'AMZN', 'NFLX', 'COIN', 'MSTR', 'BABA', 'JD',
            'PDD', 'BIDU', 'NIO', 'XPEV', 'LI', 'BTCC', 'ETHU',
            'SOLV', 'BCHN'
        }

    def _calculate_hurst(self, price_series):
        try:
            lags = range(2, min(20, len(price_series) // 2))
            tau = [np.std(np.subtract(price_series[lag:], price_series[:-lag])) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0]
        except Exception:
            return 0.5

    def _calculate_adx(self, df, period=14):
        try:
            high, low, close = df['high'], df['low'], df['close']
            plus_dm, minus_dm = high.diff(), low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
            atr = tr.rolling(period).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
            minus_di = abs(100 * (minus_dm.ewm(alpha=1 / period).mean() / atr))
            dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            return dx.rolling(period).mean().iloc[-1]
        except Exception:
            return 50.0

    def _calculate_rsi(self, df, period=14):
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs)).iloc[-1]
        except Exception:
            return 50.0

    def _select_candidates(self, pool, target_count, direction):
        """智能挑选器：优先挑极佳的，如果不够强制用后备池补齐"""
        if target_count <= 0:
            return []

        selected = []
        used_symbols = set()

        # 定义梯队阈值 (Z-Score, RSI)
        if direction == 'LONG':
            tiers = [(-1.2, 40), (-0.8, 45), (-0.4, 50)]
        else:
            tiers = [(1.2, 60), (0.8, 55), (0.4, 50)]

        # 1. 按梯队寻找理想标的
        for z_thresh, rsi_thresh in tiers:
            if len(selected) >= target_count:
                break
            for c in pool:
                if c['symbol'] in used_symbols:
                    continue
                is_match = False
                if direction == 'LONG':
                    if c['z_score'] < z_thresh and c['rsi'] < rsi_thresh: is_match = True
                else:
                    if c['z_score'] > z_thresh and c['rsi'] > rsi_thresh: is_match = True

                if is_match:
                    c_copy = c.copy()
                    c_copy['score'] = round(c['base_score'] + min(30, abs(c['z_score']) * 10), 2)
                    c_copy['direction'] = direction
                    c_copy['is_fallback'] = False
                    selected.append(c_copy)
                    used_symbols.add(c['symbol'])
                    if len(selected) >= target_count:
                        break

        # 2. 如果数量还不够，启动【强制兜底补位】
        if len(selected) < target_count:
            # 从剩下的池子里，按照基础分排序
            remaining = [c for c in pool if c['symbol'] not in used_symbols]
            # 如果是做多，Z-Score 越小（超卖）优先级越高；如果是做空，Z-Score 越大优先级越高
            if direction == 'LONG':
                remaining.sort(key=lambda x: x['z_score'])  # Z最小排前面
            else:
                remaining.sort(key=lambda x: x['z_score'], reverse=True)  # Z最大排前面

            for c in remaining:
                if len(selected) >= target_count:
                    break
                c_copy = c.copy()
                c_copy['score'] = round(c['base_score'] + min(30, abs(c['z_score']) * 10), 2)
                c_copy['direction'] = direction
                c_copy['is_fallback'] = True  # ★ 标记为补位
                selected.append(c_copy)
                used_symbols.add(c['symbol'])

        # 根据分数重排序，让最高分的显示在最前面
        selected.sort(key=lambda x: x['score'], reverse=True)
        return selected

    def scan(self, target_long=3, target_short=0, top_n=100):
        # 1. 加载交易所完整市场数据
        markets = self.exchange.load_markets()
        tickers = self.exchange.fetch_tickers()

        usdt_futures = []
        for s, market in markets.items():
            # ★ 核心精准过滤条件：
            # ① 必须是 USDT 永续合约（linear 线性合约，结算货币为 USDT）
            if market.get('linear') is not True or market.get('quote') != 'USDT':
                continue

            # ② 必须处于激活状态 (active)
            if not market.get('active', True):
                continue

            # ③ 过滤掉非传统加密货币分类（如 ETF、股票映射、指数类标签）
            # 检查 info 字段或交易所原生分类中是否包含 traditional/stock/etf 属性
            info = market.get('info', {})
            category = str(info.get('category', '')).lower()
            if 'etf' in category or 'stock' in category or 'index' in category:
                continue

            # ④ 额外双保险：排除常见的美股/指数基础币种白名单（防止交易所未打标签）
            base_currency = market.get('base', '').upper()
            if base_currency in self._stock_blacklist:
                continue

            # ⑤ 必须在 tickers 中有成交量数据
            t = tickers.get(s)
            if not t or not t.get('quoteVolume'):
                continue

            usdt_futures.append({
                'symbol': s,
                'volume': t['quoteVolume']
            })

        # 按 24 小时成交量从大到小排序，取前 top_n 个主流币
        usdt_futures.sort(key=lambda x: x['volume'], reverse=True)
        symbols = [item['symbol'] for item in usdt_futures[:top_n]]

        valid_pool = []
        for symbol in symbols:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.limit)
                if len(ohlcv) < 50: continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                closes = df['close'].values
                price = closes[-1]

                tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift()),
                                abs(df['low'] - df['close'].shift())], axis=1).max(axis=1)
                atr_pct = (tr.rolling(14).mean().iloc[-1] / price) * 100

                hurst = self._calculate_hurst(closes)
                adx = self._calculate_adx(df)

                if atr_pct < 3.0 or hurst > 0.5 or adx > 25:
                    continue

                z_score = (price - np.mean(closes)) / np.std(closes) if np.std(closes) > 0 else 0
                rsi = self._calculate_rsi(df)

                base_score = min(30, atr_pct * 3) + (0.5 - hurst) * 80 + max(0, (25 - adx) * 1.5)

                valid_pool.append({
                    'symbol': symbol,
                    'price': price,
                    'base_score': base_score,
                    'atr_pct': round(atr_pct, 2),
                    'hurst': round(hurst, 3),
                    'adx': round(adx, 2),
                    'z_score': round(z_score, 2),
                    'rsi': round(rsi, 2)
                })
                time.sleep(self.exchange.rateLimit / 1000)
            except Exception:
                continue

        final_longs = self._select_candidates(valid_pool, target_long, 'LONG')
        final_shorts = self._select_candidates(valid_pool, target_short, 'SHORT')

        return {"longs": final_longs, "shorts": final_shorts}

    def select_best_pair(self, direction='LONG', exclude_pairs=None):
        """
        动态白名单模式：根据方向选择得分最高的单个交易对
        排除已有的持仓交易对
        """
        if exclude_pairs is None:
            exclude_pairs = []

        # 获取候选池（扫描 100 个币）
        result = self.scan(target_long=10, target_short=10, top_n=100)

        candidates = result['longs'] if direction == 'LONG' else result['shorts']

        # 排除已有的交易对
        exclude_set = set(exclude_pairs)
        filtered = [c for c in candidates if c['symbol'] not in exclude_set]

        if not filtered:
            return None

        # 返回得分最高的
        best = filtered[0]
        return {
            'name': best['symbol'],
            'direction': direction,
            'score': best['score'],
            'price': best['price'],
            'z_score': best['z_score'],
            'rsi': best['rsi']
        }

    # ★ 加入重试机制：遇到网络或限频错误，等待并重试 3 次
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.RateLimitExceeded))
    )
    def _fetch_ohlcv_with_retry(self, symbol, timeframe, limit):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    def get_range(self, symbol: str, days: int = 30) -> dict:
        symbol = str(symbol)
        if days not in (7, 30, 90):
            days = 30

        cache_key = f"{symbol}_{days}"
        now = time.time()

        # 读取缓存（加锁）
        with self._cache_lock:
            if cache_key in self._range_cache:
                cached_time, cached_data = self._range_cache[cache_key]
                if now - cached_time < 300:
                    res = cached_data.copy()
                    res['source'] = 'cache'
                    return res

        result = {
            'pair': symbol, 'days': days,
            'high': 0.0, 'low': 0.0,
            'lower': 0.0, 'upper': 0.0,
            'source': 'ccxt', 'error': None
        }

        try:
            ohlcv = self._fetch_ohlcv_with_retry(symbol, '1d', limit=days + 5)
            if not ohlcv:
                raise ValueError("日线数据为空")

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = df.dropna(subset=['high', 'low'])
            recent = df.tail(days)

            if recent.empty:
                raise ValueError("有效日线数据为空")

            raw_high = float(recent['high'].max())
            raw_low = float(recent['low'].min())

            if raw_high <= 0 or raw_low <= 0 or raw_high <= raw_low:
                raise ValueError(f"极值异常 high={raw_high} low={raw_low}")

            result.update({
                'high': raw_high, 'low': raw_low,
                'lower': round(raw_low * 0.99, 8),
                'upper': round(raw_high * 1.01, 8)
            })

            # 写入缓存（加锁）
            with self._cache_lock:
                self._range_cache[cache_key] = (now, result.copy())
            return result

        except Exception as e:
            result['error'] = str(e)
            result['source'] = 'fallback'
            try:
                # 降级处理也加入重试
                ticker = self._fetch_ticker_with_retry(symbol)
                price = float(ticker.get('last') or 0)
                if price > 0:
                    result.update({
                        'high': price, 'low': price,
                        'lower': round(price * 0.9, 8),
                        'upper': round(price * 1.1, 8)
                    })
            except Exception as e2:
                result['error'] = f"{e} | fallback失败: {e2}"
            return result

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _fetch_ticker_with_retry(self, symbol):
        return self.exchange.fetch_ticker(symbol)

    def get_all_ranges(self, symbols: list, days: int = 30) -> dict:
        return {s: self.get_range(s, days) for s in symbols}