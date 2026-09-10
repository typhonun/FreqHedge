# 删除数据库功能实现详解

## 关键改进点

### 1. SQLite 文件占用问题的解决方案

**问题根源**：
- SQLite 使用 WAL（Write-Ahead Logging）机制，会生成 `.sqlite-shm` 和 `.sqlite-wal` 文件
- 即使主进程退出，这些文件仍可能被操作系统或其他进程占用
- 需要给文件句柄充分的释放时间

**解决方案**：
```python
# 1. 确保进程彻底退出
for i in range(15):
    long_alive = FreqtradeService.check_port(8011)
    short_alive = FreqtradeService.check_port(8012)
    if conditions_met:
        break
    time.sleep(1)

# 2. 等待 SQLite 释放文件句柄
time.sleep(3)

# 3. 尝试多次删除，处理延迟释放
for attempt in range(5):
    try:
        file_path.unlink()
        break
    except PermissionError:
        time.sleep(0.5)
```

### 2. 基于端口的进程检查

使用 `netstat` 命令根据端口检查进程是否真正退出：
```python
@staticmethod
def check_port(port):
    result = subprocess.run(
        ["cmd", "/c", f"netstat -ano | findstr :{port}"],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())
```

这种方法比 `process.poll()` 更可靠，因为：
- 不依赖 Python 的 process 对象状态
- 直接检查操作系统的网络连接
- 即使原始 process 对象丢失也能检查

### 3. 参数化数据库删除

支持分别删除多头/空头/全部数据库：
```python
db_map = {
    "long": [
        "tradesv3_long.sqlite",
        "tradesv3_long.sqlite-shm",
        "tradesv3_long.sqlite-wal",
    ],
    "short": [
        "tradesv3_short.sqlite",
        "tradesv3_short.sqlite-shm",
        "tradesv3_short.sqlite-wal",
    ]
}

if side == "both":
    db_files = db_map["long"] + db_map["short"]
else:
    db_files = db_map.get(side, [])
```

### 4. 异常处理优化

区分不同的异常类型，采用不同的处理策略：
```python
for attempt in range(5):
    try:
        file_path.unlink()
        result["database"].append(filename)
        deleted = True
        break
    except PermissionError as e:
        # 权限错误 → 重试
        time.sleep(0.5)
    except FileNotFoundError:
        # 文件已删除 → 跳过
        deleted = True
        break
    except Exception as e:
        # 其他错误 → 重试
        time.sleep(0.5)
```

### 5. 前端 UI 改进

从单个 "删除数据库" 按钮改为两个按钮：
- "🗑 清理多头" - 只删除多头数据库
- "🗑 清理空头" - 只删除空头数据库

优点：
- 用户可以只清理某一侧的数据，更灵活
- 减少误操作风险
- 清晰的意图表达

## API 调用示例

### 删除多头数据库
```javascript
await axios.post('http://localhost:9000/control/delete_trade', {
  side: 'long'
})
```

### 删除空头数据库
```javascript
await axios.post('http://localhost:9000/control/delete_trade', {
  side: 'short'
})
```

### 删除全部数据库
```javascript
await axios.post('http://localhost:9000/control/delete_trade', {
  side: 'both'
})
```

## 返回响应格式

```json
{
  "success": true,
  "message": "已清理long数据库和日志",
  "detail": {
    "database": [
      "tradesv3_long.sqlite",
      "tradesv3_long.sqlite-shm",
      "tradesv3_long.sqlite-wal"
    ],
    "logs": []
  }
}
```

## 性能考虑

- **等待时间优化**：总等待时间约 18 秒（15 秒进程检查 + 3 秒 SQLite 释放）
- **重试机制**：最多 5 次重试，每次间隔 0.5 秒，最多额外 2.5 秒
- **总最坏情况**：约 20.5 秒

## 日志输出示例

```
========================
DELETE TRADE START: long
[1] LONG:False SHORT:True
[2] LONG:False SHORT:False
LONG freqtrade已退出
已删除数据库: tradesv3_long.sqlite
已删除数据库: tradesv3_long.sqlite-shm
已删除数据库: tradesv3_long.sqlite-wal
DELETE RESULT: {'success': True, 'message': '已清理long数据库和日志', 'detail': {...}}
```

## 后续改进方向

1. **异步处理**：考虑将删除操作改为后台任务，前端定期查询状态
2. **进度反馈**：实时反馈删除进度
3. **数据库恢复**：考虑实现软删除或备份机制
4. **错误恢复**：自动化恢复失败的删除操作
