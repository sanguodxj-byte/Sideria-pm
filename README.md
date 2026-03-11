<div align="center">

# 🐉 Sideria PM Pro v3.0
**The AI-Driven Universal Process Manager**

一个专为复杂多节点生态（如 AI 生态、长进程矩阵）打造的现代进程守护神。
彻底告别传统 CMD 弹窗与 VBS 脱管，用数据同步与模糊启发式检索治理你的服务。

</div>

---

## ✨ 核心进化点 (v3.0)

相比于上一代的传统进程管家，v3.0 迎来了智能化质变：

- 🧠 **AI 启发式寻路雷达**
  - 不再死板对比绝对路径！即使您将几十 GB 的 AI 整合包移动到全新的驱动器或者修改了外部文件夹，首次配置向导也能依靠特征权重打分算法（`findBestCandidate`）自动穿梭于数十个同名 `main.py` 之间，精准找回真正的模型业务中枢。惩罚深层依赖、屏蔽虚拟环境陷阱。
- 🌳 **原生深度进程统治系统**
  - 旧时代的 VBS / wscript.exe 包装经常会导致子进程“脱管”（PM 自身显示还在，但底层服务停不掉或者疯狂复生）。v3.0 全面接管深度 Shell 生命树（原生的递归 `taskkill /T`），强力降服所有顽固网关架构。
- ⚡ **毫秒级双频 GUI 配置同步**
  - 对于 GUI 界面参数，由单纯的“点击保存”演进为 `FocusOut` + `KeyRelease` 双活字典绑定引擎。你在界面上的每一次敲击都在与底层 `openclaw.json` / `services.json` 无缝呼吸同步。
- 🤖 **Agentic Autonomy (AI 代理智能托管)**
  - **这不仅是一个给人类使用的工具！** Sideria PM Pro 是专门为 AI Agent (如 Antigravity / OpenClaw) 打造的底层锚点。只要主网关 (`openclaw`) 保持运行，AI 代理就能通过 HTTP API 接管宿主的全部进程启停、故障恢复与日志诊断，形成完美的闭环自愈系统。
- 🛡️ **内生自卫协议**
  - 自动规避 `taskkill` 对自身环境的主进程自残行为，确保持久生命力。
- 🌐 **双活 HTTP API 控制矩阵**
  - 单点状态透显（29997 面板通信）、全局互斥单实例锁（29996）、网关联动全接管。

---

## 🚀 快速接管 (双端支持)

Sideria PM Pro v3.0 为您提供了优雅的**全景化图形界面 (GUI)**，告别繁琐的命令行输码：

### 1. 启动图形化视界 (GUI 面板)

您不需要输入任何复杂指令，直接双击运行以下任一启动程序：

- 🌟 **如果你下载的是整合打包版**：直击双击运行 `Sideria-PM.exe`。
- 🐍 **如果您在源码环境**：双击运行 `Sideria-PM.bat` 或在终端执行 `python sideria-pm-gui.py`。



### 2. 在界面中接管一切

在启动的 Sideria 配置窗体中：
1. **自动探查配置**：只需在面板中触发环境配置或保存项，底层智能向导将自动捕捉并生成 `services.json` 文件。
2. **可视化服务控制**：通过主界面侧边栏，或通过核心配置页直接联动网关环境。
3. **输入即存 (Data Binding)**：所有在输入框敲击的信息都会被**毫秒级切片存储**，无需再担心忘点保存导致服务加载失败。

---

## 💻 极客 CLI 指令大典 (面向服务器无头环境)

图形化界面虽然优雅，但在远程 Linux / 纯终端环境里，底层引擎依然像外科手术刀般精准。您随时可以降级回终端调用：

```bash
# === 初装拓荒 ===
node sideria-pm.js setup

# === 唤醒与杀戮 ===
node sideria-pm.js start         # 引爆所有服务矩阵
node sideria-pm.js start --clean # 清理旧残留并启动

# === 独立控制节点 ===
node sideria-pm.js start comfyui
node sideria-pm.js stop gateway
node sideria-pm.js restart feibi-node

# === 溯源查询 ===
node sideria-pm.js status        # 查看全局健康热力图
node sideria-pm.js logs gateway  # 实时抽取指定长度崩溃流
```

---

## 📡 RESTful 云控 API (Agent 代理的最佳温床)

PM 内置低频数据监听守护，除了本地 Shell 控制，默认在 `127.0.0.1:29997` 开放全面控制权。**这是 AI Agent 进行系统自愈的核心锚点：**

```bash
curl http://127.0.0.1:29997/status                     # AI 查询宿主心跳图
curl http://127.0.0.1:29997/start?name=gcli2api        # AI 靶向拉起瘫痪节点
curl http://127.0.0.1:29997/restart                    # AI 触发全局热重载
curl http://127.0.0.1:29997/logs?name=comfyui&lines=50 # AI 抽取崩溃堆栈进行自主诊断
```

---

## ⚙️ 底层配置模型 (`services.json`)

系统的一切行为逻辑高度解耦于该文件。您可以用编辑器精调配置向导抓取出的结构。

### 服务基础结构示例：

```json
{
  "services": {
    "gateway": {
      "name": "OpenClaw Gateway Core",
      "enabled": true,
      "cmd": "openclaw",
      "args": ["gateway"],
      "cwd": "D:\\openclaw",
      "env": {
        "PYTHONUTF8": "1"
      },
      "healthCheck": {
        "type": "http",
        "url": "http://127.0.0.1:8080/health"
      },
      "startupOrder": 1,
      "autoRestart": true,
      "maxRestarts": 10,
      "restartDelayMs": 5000,
      "restartBackoffMax": 60000
    }
  }
}
```

### 控制学参数释义

- **多级递进退避 (Backoff Restart)**
  - 若子程序由于缺库导致疯狂闪退爆破，系统采用**指数退避重启制**（5s → 7.5s → 11.25s ... 峰值 60s），不仅能挽回短暂崩溃，还阻止了死循环无尽耗损CPU，60秒平稳后计数归零。
- **阶梯式顺序链路启动流 (`startupOrder`)**
  - 对抗服务依赖争抢：网关 -> 缓存 -> API。设置数值由低到高逐级拉起进程。
- **深层环境变量 (`env`)**
  - 有效处理 Windows 本地编码（如注入强行改变的 `UTF-8`）防止某些 AI 的 Console 拉起异常。

---

## 📁 核心解剖学

```text
sideria-pm-repo/
├── sideria-pm.js           # 主干控制引擎 (守护、监听、生命判定)
├── setup-wizard.js         # AI 探路兵 (负责初装与路径纠偏打分)
├── sideria-pm-gui.py       # TK 交互数据体 (负责 JSON 热绑与可视化管理)
├── services.json           # 最终控制配平表
├── services.template.json  # 厂标规范表单骨架
├── pm-logs/                # 按日轮转记录的控制面板活动史与所有子域标准流错误日志
└── .sideria-pm-state.json  # 记录上一次崩溃或中断时刻的 PM 自身数据片段
```

---

*OpenClaw System Component · Optimized distribution ready.*
