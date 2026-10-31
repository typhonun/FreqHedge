<div align="center">

# FreqHedge

用 Web 界面管理多个 Freqtrade 机器人，支持 DCA、网格、回测、监控和统一风控。

</div>

---

## 快速开始

### 0. 准备环境

- Python **3.11 或 3.12**（不支持 3.13/3.14）
- Node.js 18+ 和 pnpm
- Git

Python 3.11/3.12 有项目依赖所需的预编译包，避免 NumPy、aiohttp、TA-Lib 等依赖在本机源码编译。

### 1. 判断是否已安装 Freqtrade

在项目虚拟环境之外打开终端，执行：

```powershell
freqtrade --version
```

- 能输出版本号：按**情况 A**操作。
- 提示找不到命令：按**情况 B**操作。

### 情况 A：已安装 Freqtrade

```powershell
git clone https://github.com/typhonun/DcaTpManager
cd DcaTpManager

py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r freqtrade\requirements.txt

cd frontend
pnpm install
```

### 情况 B：尚未安装 Freqtrade

先退出已有虚拟环境，在终端中执行：

```powershell
deactivate
python -m pip install --user pipx
python -m pipx ensurepath
```

重开终端后安装最新版 Freqtrade（不要安装已经失效的 `2024.10`）：

```powershell
pipx install freqtrade
freqtrade --version
```

然后安装项目：

```powershell
git clone https://github.com/typhonun/DcaTpManager
cd DcaTpManager

py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r freqtrade\requirements.txt

cd frontend
pnpm install
```

`freqtrade\requirements.txt` 只安装 FreqHedge 后端依赖，不重复安装 Freqtrade，
因此不会再次触发旧版 `pandas-ta`、NumPy 和 ccxt 的冲突。

### 2. 启动服务

后端和前端分别使用两个终端窗口。

**终端一：后端**

```powershell
cd DcaTpManager
venv\Scripts\activate
cd backend
python -m uvicorn app.main:app --reload --port 9000
```

**终端二：前端**

```powershell
cd DcaTpManager\frontend
pnpm dev
```

打开 <http://localhost:5173>。

### macOS / Linux

将 Windows 的虚拟环境命令替换为：

```bash
python3.12 -m venv venv
source venv/bin/activate
```

路径分隔符使用 `/`；其余安装和启动命令相同。

### 常见问题

- `cl`/`gcc` 或 NumPy、aiohttp 编译失败：确认使用 Python 3.11/3.12，不要使用 3.13/3.14。
- `freqtrade` 找不到：重新打开终端，确认 `freqtrade --version` 能执行。
- `ERR_PNPM_IGNORED_BUILDS`：在 `frontend` 目录执行 `pnpm approve-builds`，选择 `esbuild`，再执行 `pnpm install`。
- 页面白屏或 `CandlestickSeries` 导入失败：删除 `frontend\node_modules` 后重新执行 `pnpm install`；项目固定使用 `lightweight-charts` 5.2.0。

## 项目结构

```text
DcaTpManager/
├── backend/                 # FastAPI 管理服务
├── frontend/                # Vue Web 控制台
└── freqtrade/
    └── user_data/           # 策略、配置、机器人数据和日志
```

> FreqHedge 仅用于软件工程实践、量化研究和学习交流，不保证收益，也不构成投资建议。
