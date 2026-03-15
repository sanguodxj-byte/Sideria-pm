# Sideria PM v2.0 Universal

希德莉亚进程管理器 - 通用版

一个轻量级、可配置的 Windows 进程管理器，专为管理多个长期运行的服务而设计。

## ✨ 特性

- 🎯 **配置驱动** - 通过 JSON 配置文件管理所有服务
- 🔧 **首次配置向导** - 交互式引导配置，自动检测路径
- 🤖 **智能路径检测** - 在根目录及子目录中自动搜索可执行文件和脚本
- 🔄 **自动重启** - 服务崩溃时自动重启，支持退避策略
- 💓 **健康检查** - HTTP 健康检查，实时监控服务状态
- 📊 **状态监控** - 实时查看所有服务的运行状态和健康度
- 📝 **日志管理** - 每个服务独立日志，支持查看和轮转
- 🛡️ **自杀防护** - 防止误杀 PM 自身进程
- 🌐 **HTTP API** - RESTful API 控制和查询服务
- 🔒 **单实例锁** - 防止多个 PM 实例冲突

## 🚀 快速开始

### 1. 首次配置

```bash
node sideria-pm.js setup
```

配置向导会引导你：
- 设置工作区根目录
- 🤖 自动在根目录及子目录中搜索可执行文件
- 🤖 自动检测 Python 虚拟环境、Electron、Node.js 脚本
- 检测并配置各服务的可执行文件路径
- 设置工作目录
- 配置健康检查 URL
- 选择启用/禁用服务

### 智能检测功能

配置向导会自动搜索：
- **Python 应用**: 虚拟环境中的 python.exe、系统 Python
- **Node.js 应用**: 项目中的 .js 脚本文件
- **Electron 应用**: node_modules 中的 electron.exe
- **其他可执行文件**: 根据服务名称智能搜索

搜索范围：
- 工作区根目录
- 子目录（最多 3 层深度）
- 自动跳过 node_modules、.git 等无关目录

### 2. 启动所有服务

```bash
node sideria-pm.js start
```

或使用清理模式（先清理残留进程）：

```bash
node sideria-pm.js start --clean
```

### 3. 查看状态

```bash
node sideria-pm.js status
```

输出示例：
```
╔════════════════════════════════════════════════════════════════╗
║       🐉 希德莉亚进程管理器 v2.0 Universal                   ║
║          Sideria Process Manager                              ║
╚════════════════════════════════════════════════════════════════╝

📊 总览: 7/8 运行中  |  5 健康  |  1 已停止

🟢 OpenClaw Gateway (核心网关)
   状态: 运行中  |  健康: 💚  |  PID: 12345
   运行时间: 2h 15m 30s  |  重启次数: 0

🟢 ComfyUI (绘梦引擎)
   状态: 运行中  |  健康: 💚  |  PID: 12346
   运行时间: 2h 10m 15s  |  重启次数: 0
```

## 📖 命令参考

### 基本命令

```bash
# 首次配置向导
node sideria-pm.js setup

# 启动所有服务
node sideria-pm.js start

# 启动所有服务（清理模式）
node sideria-pm.js start --clean

# 停止所有服务
node sideria-pm.js stop

# 重启所有服务
node sideria-pm.js restart

# 查看服务状态
node sideria-pm.js status
```

### 单个服务操作

```bash
# 启动单个服务
node sideria-pm.js start <服务名>

# 停止单个服务
node sideria-pm.js stop <服务名>

# 重启单个服务
node sideria-pm.js restart <服务名>

# 查看服务日志（最后30行）
node sideria-pm.js logs <服务名>
```

### HTTP API

PM 启动后会在 `http://127.0.0.1:29997` 提供 HTTP API：

```bash
# 查看状态
curl http://127.0.0.1:29997/status

# 启动所有服务
curl http://127.0.0.1:29997/start

# 启动单个服务
curl http://127.0.0.1:29997/start?name=comfyui

# 停止所有服务
curl http://127.0.0.1:29997/stop

# 重启所有服务
curl http://127.0.0.1:29997/restart

# 查看日志
curl http://127.0.0.1:29997/logs?name=comfyui&lines=50

# 健康检查
curl http://127.0.0.1:29997/health
```

## ⚙️ 配置文件

### services.json

服务配置文件，由配置向导生成，也可以手动编辑。

```json
{
  "services": {
    "my_service": {
      "name": "My Service (显示名称)",
      "enabled": true,
      "cmd": "C:\\path\\to\\executable.exe",
      "args": ["arg1", "arg2"],
      "cwd": "C:\\path\\to\\workdir",
      "env": {
        "ENV_VAR": "value"
      },
      "healthCheck": {
        "type": "http",
        "url": "http://127.0.0.1:8080/health"
      },
      "autoStart": true,
      "autoRestart": true,
      "maxRestarts": 10,
      "restartDelayMs": 5000,
      "restartBackoffMax": 60000,
      "startupOrder": 1,
      "startupDelay": 0,
      "dependsOn": ["other_service"]
    }
  }
}
```

### 配置字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 服务显示名称 |
| `enabled` | boolean | ✅ | 是否启用此服务 |
| `cmd` | string | ✅ | 可执行文件路径 |
| `args` | array | ❌ | 命令行参数 |
| `cwd` | string | ✅ | 工作目录 |
| `env` | object | ❌ | 环境变量 |
| `healthCheck` | object | ❌ | 健康检查配置 |
| `autoStart` | boolean | ❌ | 是否自动启动（默认 true） |
| `autoRestart` | boolean | ❌ | 是否自动重启（默认 true） |
| `maxRestarts` | number | ❌ | 最大重启次数（默认 10） |
| `restartDelayMs` | number | ❌ | 重启延迟（毫秒，默认 5000） |
| `restartBackoffMax` | number | ❌ | 最大退避时间（毫秒，默认 60000） |
| `startupOrder` | number | ❌ | 启动顺序（数字越小越早，默认 99） |
| `startupDelay` | number | ❌ | 启动延迟（毫秒，默认 0） |
| `dependsOn` | array | ❌ | 依赖的服务（仅文档用途） |

### 健康检查配置

```json
{
  "healthCheck": {
    "type": "http",
    "url": "http://127.0.0.1:8080/health"
  }
}
```

目前仅支持 HTTP 健康检查。如果服务返回 200 状态码，则认为健康。

## 🔧 高级功能

### 启动顺序控制

通过 `startupOrder` 和 `startupDelay` 控制服务启动顺序：

```json
{
  "gateway": {
    "startupOrder": 1,
    "startupDelay": 0
  },
  "database": {
    "startupOrder": 2,
    "startupDelay": 3000
  },
  "api": {
    "startupOrder": 3,
    "startupDelay": 6000
  }
}
```

### 自动重启策略

服务崩溃时会自动重启，支持指数退避：

- 第 1 次重启：延迟 5 秒
- 第 2 次重启：延迟 7.5 秒
- 第 3 次重启：延迟 11.25 秒
- ...
- 最大延迟：60 秒

如果服务运行超过 60 秒后崩溃，重启计数会重置。

### 环境变量

某些服务需要特定的环境变量（如 ComfyUI 需要 UTF-8 编码）：

```json
{
  "comfyui": {
    "env": {
      "PYTHONIOENCODING": "utf-8",
      "PYTHONUTF8": "1"
    }
  }
}
```

### 手动启动服务

将 `autoStart` 设为 `false` 的服务不会自动启动：

```json
{
  "live2d": {
    "autoStart": false
  }
}
```

需要手动启动：

```bash
node sideria-pm.js start live2d
```

## 📁 文件结构

```
sideria-pm/
├── sideria-pm.js           # 主程序
├── setup-wizard.js         # 配置向导
├── services.json           # 服务配置（由向导生成）
├── services.template.json  # 配置模板
├── Sideria-PM.bat          # Windows 启动脚本
├── pm-logs/                # 日志目录
│   ├── pm-2026-03-02.log   # PM 主日志
│   ├── gateway.log         # 各服务日志
│   ├── comfyui.log
│   └── ...
├── .sideria-pm-state.json  # 状态持久化
└── .pm-heartbeat           # 心跳文件
```

## 🛡️ 安全特性

### 自杀防护

PM 会保护自己的进程 ID，防止误杀：

```javascript
// ❌ 这会被拒绝
taskkill /PID <PM的PID> /F

// ✅ 正确的停止方式
node sideria-pm.js stop
```

### 单实例锁

PM 使用端口锁（29996）确保只有一个实例运行。

## 🐛 故障排查

### PM 无法启动

1. 检查端口 29997 和 29996 是否被占用
2. 查看 `pm-logs/pm-YYYY-MM-DD.log` 日志

### 服务无法启动

1. 检查 `services.json` 中的路径是否正确
2. 查看服务日志：`node sideria-pm.js logs <服务名>`
3. 手动运行命令测试：`cd <cwd> && <cmd> <args>`

### 配置文件损坏

配置向导会自动备份旧配置：

```bash
# 恢复备份
copy services.json.backup.<timestamp> services.json

# 或重新运行配置向导
node sideria-pm.js setup
```

## 📝 日志

### PM 主日志

位于 `pm-logs/pm-YYYY-MM-DD.log`，记录 PM 自身的操作。

### 服务日志

每个服务有独立的日志文件：`pm-logs/<服务名>.log`

查看日志：

```bash
# 查看最后 30 行
node sideria-pm.js logs <服务名>

# 通过 HTTP API 查看更多行
curl http://127.0.0.1:29997/logs?name=<服务名>&lines=100
```

## 🔄 迁移指南

### 从 v1.x 迁移到 v2.0

1. 备份旧的 `sideria-pm.js`
2. 替换为新版本
3. 运行配置向导：`node sideria-pm.js setup`
4. 根据旧配置填写服务信息
5. 测试启动：`node sideria-pm.js start`

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系

如有问题，请提交 Issue。
