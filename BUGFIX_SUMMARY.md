# 删除数据库功能修复总结

## 问题描述
1. 点击删除数据库时，虽然进程已杀死，但数据库文件没有被清理
2. 没有办法分别清理多头或空头的数据库

## 解决方案

### 1. 改进 `delete_trade()` 后端方法
- **添加 side 参数**：支持 "long"（多头）、"short"（空头）、"both"（全部）
- **智能进程停止**：根据 side 参数只停止对应的进程
- **基于端口检查**：使用 netstat 检查端口，更准确地判断进程是否退出
- **重试机制**：文件删除失败时最多重试 5 次，间隔 0.5 秒
  - 区分处理 `PermissionError`（权限错误）
  - 自动跳过已删除的文件
- **增加等待时间**：
  - 进程确认等待：15 秒（最多 15 次，每次 1 秒）
  - SQLite 文件句柄释放等待：3 秒
- **灵活的日志清理**：只有删除全部时才清理 logs

### 2. 数据库文件管理
```python
db_map = {
    "long": [
        "tradesv3_long.sqlite",
        "tradesv3_long.sqlite-shm",    # SQLite共享内存文件
        "tradesv3_long.sqlite-wal",    # SQLite预写日志文件
    ],
    "short": [
        "tradesv3_short.sqlite",
        "tradesv3_short.sqlite-shm",
        "tradesv3_short.sqlite-wal",
    ]
}
```

### 3. API 改进
- `/delete_trade` 端点现在接受 JSON 参数：`{ "side": "long|short|both" }`

### 4. 前端改进
- **拆分按钮**：将单个 "删除数据库" 改为两个按钮
  - "🗑 清理多头" - 删除多头数据库
  - "🗑 清理空头" - 删除空头数据库
- **智能提示**：根据操作类型显示对应的确认信息
- **CSS 调整**：使用 flex 布局确保按钮正常显示

## 修改文件
1. `backend/app/services/freqtrade_service.py`
   - `delete_trade()` 方法

2. `backend/app/api/control.py`
   - `delete_trade()` 路由

3. `frontend/src/composables/useRunControl.js`
   - `deleteTrade()` 函数
   - `confirmDeleteTrade()` 函数

4. `frontend/src/components/RunControl.vue`
   - 修改按钮结构
   - 添加 CSS 样式

## 工作流程
1. 用户点击 "清理多头" 或 "清理空头" 按钮
2. 显示对应的风险提示
3. 前端发送 POST 请求到 `/delete_trade`，包含 `{ "side": "long|short" }`
4. 后端：
   - 停止对应的 freqtrade 进程
   - 等待端口释放（基于 netstat 检查）
   - 等待 SQLite 文件句柄释放
   - 尝试删除对应的数据库文件（最多重试 5 次）
5. 返回删除结果给前端
6. 显示成功或失败的消息

## 测试步骤
1. 启动机器人
2. 进行一些交易（生成数据库文件）
3. 点击 "清理多头" 按钮
4. 查看后端日志，验证：
   - 多头进程被成功杀死
   - SQLite 文件被删除
   - 返回正确的删除统计信息
5. 重复步骤 3-4，点击 "清理空头" 按钮
6. 验证空头数据库被正确删除

