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
- 🛡️ **内生自卫协议**
  - 自动规避 `taskkill` 对自身环境的主进程自残行为，确保持久生命力。
- 🌐 **双活 HTTP API 控制矩阵**
  - 单点状态透显（29997 面板通信）、全局互斥单实例锁（29996）、网关联动全接管。

---

## 🚀 快速接管

### 1. 自动感应配置 (新环境自动部署)

首次进入新环境，只需运行一次：

```bash
node sideria-pm.js setup
```

**发生了什么？** 猎犬算法启动：
- 自动捕捉宿主工作流根节点。
- 对 Python 应用：穿透到各业务层虚拟环境抓取对应 `.exe`。
- 对 Node/Electron 应用：智能过滤 `node_modules` 回溯主启动节点。
- 最终汇聚生成健壮的 `services.json`，且能适应未来的位移。

### 2. 引爆所有服务矩阵

```bash
node sideria-pm.js start
```

遇到旧配置残留或卡死？使用暴力重洗模式：

```bash
node sideria-pm.js start --clean
```

### 3. 数据可视化 (状态与仪表盘)

```bash
node sideria-pm.js status
```

*面板将在控制台中实时反馈以下维度的健康切片：*
*• 运行时长、• 保活重启统计、• 实时 PID 跟踪、• HTTP 服务级健康探针返回 (`200 OK=💚`)*

---

## 📖 控制指令大典

Sideria PM Pro 是极其模块化的。除总体把控外，您也可如同操控 Docker 容器般单独启停控制域：

```bash
# 重启所有系统群
node sideria-pm.js restart

# 控制单个独立节点 (如 Gateway 或 某些 Worker)
node sideria-pm.js start comfyui
node sideria-pm.js stop gateway
node sideria-pm.js restart feibi-node

# 溯源查询: 实时调取目标节点崩溃或输出底库 (支持自动最后N行剪切)
node sideria-pm.js logs gateway
```

---

## 📡 RESTful 云控 API 

PM 内置低频数据监听守护，除了本地 Shell 控制，默认在 `127.0.0.1:29997` 开放全面控制权给外部 Web 界面或第三方应用请求控制：

```bash
curl http://127.0.0.1:29997/status                     # 查询心跳图
curl http://127.0.0.1:29997/start?name=gcli2api        # 靶向启动
curl http://127.0.0.1:29997/restart                    # 全局热重载
curl http://127.0.0.1:29997/logs?name=comfyui&lines=50 # 抽取指定长度崩溃流
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
