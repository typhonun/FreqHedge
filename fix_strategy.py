import re

with open(r'E:\code\python_code\DcaTp\freqtrade\user_data\strategies\DcaTpLong.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add enable check for trend_add
old_pattern = r'def trend_add\(self, trade: Trade, last: dict, margin: float, collateral: float, current_time: datetime\):'
new_text = r'def trend_add(self, trade: Trade, last: dict, margin: float, collateral: float, current_time: datetime):\n        trend_add_cfg = self.config.get("trend_add", {})\n        if not bool(trend_add_cfg.get("enable", True)):\n            return None\n        \n        max_count = int(trend_add_cfg.get("max_count", 3))\n        levels = trend_add_cfg.get("levels", [])'
content = re.sub(old_pattern, new_text, content)

# Add enable check for tp_reduce
old_pattern = r'def tp_reduce\(self, trade: Trade, last: dict, current_profit: float, margin: float, current_rate: float,\s+current_time: datetime\):'
new_text = r'def tp_reduce(self, trade: Trade, last: dict, current_profit: float, margin: float, current_rate: float,\n                  current_time: datetime):\n        tp_cfg = self.config.get("tp", {})\n        if not bool(tp_cfg.get("enable", True)):\n            return None'
content = re.sub(old_pattern, new_text, content)

# Add enable check for profit_rebuy
old_pattern = r'def profit_rebuy\(self, trade: Trade, last: dict, collateral: float\):'
new_text = r'def profit_rebuy(self, trade: Trade, last: dict, collateral: float):\n        tp_cfg = self.config.get("tp", {})\n        if not bool(tp_cfg.get("rebuy_enable", True)):\n            return None'
content = re.sub(old_pattern, new_text, content)

# Add enable check for grid_single
old_pattern = r'def grid_single\(self, trade: Trade, last: dict, current_time: datetime, current_rate: float,\s+margin: float = None\):'
new_text = r'def grid_single(self, trade: Trade, last: dict, current_time: datetime, current_rate: float,\n                    margin: float = None):\n        grid_cfg = self.config.get("grid", {})\n        if not bool(grid_cfg.get("enable", True)):\n            return None'
content = re.sub(old_pattern, new_text, content)

# Replace hardcoded reduce_percent in tp_reduce
content = re.sub(
    r'sell_amt = -0\.30 \* margin  # 浮盈止盈减仓数量',
    r'tp_cfg = self.config.get("tp", {})\n        reduce_percent = float(tp_cfg.get("reduce_percent", 30)) / 100.0\n        sell_amt = -reduce_percent * margin  # 浮盈止盈减仓数量',
    content
)

# Replace hardcoded target_wallet_percent in profit_rebuy
content = re.sub(
    r'target_value = collateral \* 0\.05',
    r'tp_cfg = self.config.get("tp", {})\n        target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5)) / 100.0\n        target_value = collateral * target_wallet_percent',
    content
)

# Replace hardcoded target_wallet_percent in tp_reduce (浮亏止盈)
content = re.sub(
    r'collateral_total = self\._collateral_total\(\)\s+target_usdt = float\(collateral_total\) \* 0\.05  # 浮亏止盈减仓数量',
    r'collateral_total = self._collateral_total()\n            tp_cfg = self.config.get("tp", {})\n            target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5)) / 100.0\n            target_usdt = float(collateral_total) * target_wallet_percent  # 浮亏止盈减仓数量',
    content
)

# Replace hardcoded amount in trend_add
content = re.sub(
    r'amt = collateral \* 0\.02  # 趋势加仓数量',
    r'trend_add_cfg = self.config.get("trend_add", {})\n            levels = trend_add_cfg.get("levels", [])\n            if level < len(levels):\n                level_cfg = levels[level]\n                amount_percent = float(level_cfg.get("amount", 0.5)) / 100.0\n            else:\n                amount_percent = 0.02\n            amt = collateral * amount_percent  # 趋势加仓数量',
    content
)

# Replace hardcoded DCA threshold
content = re.sub(
    r'threshold = avg_entry \* \(1 - 0\.01 - 0\.02 \* u\)  # dca 价格阈值',
    r'dca_cfg = cfg.get("dca", {})\n            levels = dca_cfg.get("levels", [])\n            if u < len(levels):\n                level_cfg = levels[u]\n                drawdown = float(level_cfg.get("drawdown", -3)) / 100.0\n                threshold = avg_entry * (1 + drawdown)\n            else:\n                threshold = avg_entry * (1 - 0.01 - 0.02 * u)  # dca 价格阈值',
    content
)

# Replace hardcoded DCA conditions
content = re.sub(
    r'cond_j_lt_0 = \(last_j is not None and last_j < 0\)\s+cond_rsi_lt_20 = \(last_rsi is not None and last_rsi < 20\)\s+cond_j_lt_20_and_rsi_lt_35 = \(last_j is not None and last_j < 20 and last_rsi is not None and last_rsi < 35\)',
    r'dca_cfg = cfg.get("dca", {})\n            levels = dca_cfg.get("levels", [])\n            condition_type = dca_cfg.get("condition", "or")\n            \n            if u < len(levels):\n                level_cfg = levels[u]\n                rsi_limit = int(level_cfg.get("rsi_limit", 25))\n                j_limit = int(level_cfg.get("j_limit", 10))\n            else:\n                rsi_limit = 25\n                j_limit = 10\n            \n            cond_j_lt_limit = (last_j is not None and last_j < j_limit)\n            cond_rsi_lt_limit = (last_rsi is not None and last_rsi < rsi_limit)\n            \n            if condition_type == "or":\n                triggered_cond = None\n                if cond_j_lt_limit:\n                    triggered_cond = f"J<{j_limit}"\n                elif cond_rsi_lt_limit:\n                    triggered_cond = f"RSI<{rsi_limit}"\n            else:\n                triggered_cond = None\n                if cond_j_lt_limit and cond_rsi_lt_limit:\n                    triggered_cond = f"J<{j_limit} & RSI<{rsi_limit}"',
    content
)

# Replace hardcoded DCA amount
content = re.sub(
    r'# 动态 DCA 加仓数量\s+dca_pct = min\(0\.01 \+ 0\.002 \* u, 0\.02\)\s+buy_amt = collateral \* dca_pct',
    r'# 动态 DCA 加仓数量\n            dca_cfg = cfg.get("dca", {})\n            levels = dca_cfg.get("levels", [])\n            if u < len(levels):\n                level_cfg = levels[u]\n                amount_percent = float(level_cfg.get("amount", 1)) / 100.0\n            else:\n                amount_percent = min(0.01 + 0.002 * u, 0.02)\n            dca_pct = amount_percent\n            buy_amt = collateral * dca_pct',
    content
)

# Replace hardcoded grid cooldown
content = re.sub(
    r'if \(current_time - last_dt\)\.total_seconds\(\) < 30 \* 60:  # 网格cd（30 分钟）',
    r'grid_cfg = self.config.get("grid", {})\n            cooldown_minutes = int(grid_cfg.get("cooldown_minutes", 30))\n            if (current_time - last_dt).total_seconds() < cooldown_minutes * 60:  # 网格cd',
    content
)

# Replace hardcoded grid_upper calculation
content = re.sub(
    r"grid_upper = anchor \* \(1 \+ float\(grid_cfg\.get\('grid\.init_upper', 0\.02\)\)\)  # 使用配置文件中的 init_upper 值",
    r'init_upper = float(grid_cfg.get("init_upper", 2))\n        grid_upper = anchor * (1 + init_upper / 100)  # 使用配置文件中的 init_upper 值',
    content
)

# Replace hardcoded grid_sell_frac
content = re.sub(
    r'grid_sell_frac = 0\.02',
    r'grid_cfg = self.config.get("grid", {})\n            grid_sell_frac = float(grid_cfg.get("reduce_percent", 2)) / 100.0',
    content
)

# Add trend_add condition check
content = re.sub(
    r'if level == 0 and u == 0 and \(not reset_needed\) and price is not None and is_bullish_trend:',
    r'if level == 0 and u == 0 and (not reset_needed) and price is not None and is_bullish_trend:\n            if level < len(levels):\n                level_cfg = levels[level]\n                profit_threshold = float(level_cfg.get("profit", 2)) / 100.0\n                rsi_threshold = int(level_cfg.get("rsi", 60))\n                current_profit = (price - avg_price) / avg_price if avg_price > 0 else 0\n                current_rsi = last.get("rsi", 50)\n                if current_profit < profit_threshold or current_rsi < rsi_threshold:\n                    logger.debug(f"[{trade.pair}] 趋势加仓条件未满足: profit={current_profit*100:.2f}% < {profit_threshold*100:.2f}%, rsi={current_rsi} < {rsi_threshold}")\n                    return None',
    content
)

with open(r'E:\code\python_code\DcaTp\freqtrade\user_data\strategies\DcaTpLong.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Strategy file updated successfully')
