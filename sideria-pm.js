/**
 * Sideria Process Manager (sideria-pm) v2.0 Universal
 * 希德莉亚进程管理器 - 通用版
 * 
 * 用法:
 *   node sideria-pm.js setup            - 首次配置向导
 *   node sideria-pm.js start            - 启动所有服务（默认兼容旧 PM，不清残留）
 *   node sideria-pm.js start --clean    - 启动前清理残留进程（新 PM 强清模式）
 *   node sideria-pm.js stop             - 停止所有服务
 *   node sideria-pm.js restart          - 重启所有服务
 *   node sideria-pm.js status           - 查看服务状态
 *   node sideria-pm.js start <name>      - 启动单个服务
 *   node sideria-pm.js stop <name>       - 停止单个服务
 *   node sideria-pm.js restart <name>    - 重启单个服务
 *   node sideria-pm.js logs <name>       - 查看服务日志（最后30行）
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');
const net = require('net');

// === 配置 ===
const PM_PORT = Number(process.env.SIDERIA_PM_PORT || 29997);
const PM_LOCK_PORT = Number(process.env.SIDERIA_PM_LOCK_PORT || 29996);
const LOG_DIR = path.join(__dirname, 'pm-logs');
const STATE_FILE = path.join(__dirname, '.sideria-pm-state.json');
const HEARTBEAT_FILE = path.join(__dirname, '.pm-heartbeat');
const CONFIG_FILE = path.join(__dirname, 'services.json');
const TEMPLATE_FILE = path.join(__dirname, 'services.template.json');

// 自杀防护：保护的 PID
const PM_PID = process.pid;
const PM_PPID = process.ppid;
const PROTECTED_PIDS = new Set([PM_PID, PM_PPID]);

// 心跳和状态持久化定时器
let heartbeatTimer = null;
let stateSaveTimer = null;
let healthCheckTimer = null;  // 健康检查定时器

// 输出管道状态（用于处理 EPIPE）
let stdoutBroken = false;
let stderrBroken = false;
let handlingUncaughtException = false;
let epipeNoticeLogged = false;

if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

function isBrokenPipeError(err) {
  if (!err) return false;
  if (typeof err === 'object') {
    if (err.code === 'EPIPE' || err.code === 'ERR_STREAM_DESTROYED') return true;
    return /broken pipe/i.test(err.message || '');
  }
  return /EPIPE|broken pipe/i.test(String(err));
}

function normalizeLogMessage(msg) {
  if (msg === null || msg === undefined) return '';
  if (msg instanceof Error) return msg.stack || msg.message || String(msg);
  if (typeof msg === 'string') return msg;
  try {
    return JSON.stringify(msg);
  } catch (e) {
    return String(msg);
  }
}

function safeWriteToStream(stream, line) {
  if (!stream || stream.destroyed || !stream.writable) return false;
  try {
    stream.write(line + '\n');
    return true;
  } catch (err) {
    if (isBrokenPipeError(err)) {
      if (stream === process.stdout) stdoutBroken = true;
      if (stream === process.stderr) stderrBroken = true;
    }
    return false;
  }
}

function appendManagerLog(line) {
  try {
    const logFile = path.join(LOG_DIR, `pm-${new Date().toISOString().slice(0, 10)}.log`);
    fs.appendFileSync(logFile, line + '\n');
  } catch (e) {}
}

if (process.stdout) {
  process.stdout.on('error', (err) => {
    if (isBrokenPipeError(err)) stdoutBroken = true;
  });
}

if (process.stderr) {
  process.stderr.on('error', (err) => {
    if (isBrokenPipeError(err)) stderrBroken = true;
  });
}

// === 加载服务配置 ===
function loadServicesConfig() {
  // 如果没有配置文件，提示运行配置向导
  if (!fs.existsSync(CONFIG_FILE)) {
    console.log('\n⚠️  未找到服务配置文件！');
    console.log('请先运行配置向导: node sideria-pm.js setup\n');
    process.exit(1);
  }
  
  try {
    const configData = fs.readFileSync(CONFIG_FILE, 'utf-8');
    const config = JSON.parse(configData);
    
    // 转换配置格式为内部格式
    const services = {};
    for (const [name, svc] of Object.entries(config.services)) {
      if (!svc.enabled) continue; // 跳过禁用的服务
      
      services[name] = {
        name: svc.name,
        cmd: svc.cmd,
        args: svc.args || [],
        cwd: svc.cwd,
        env: svc.env || undefined,
        healthCheck: svc.healthCheck || null,
        preStart: svc.preStart || null,
        autoStart: svc.autoStart !== false,
        autoRestart: svc.autoRestart !== false,
        maxRestarts: svc.maxRestarts || 10,
        restartDelayMs: svc.restartDelayMs || 5000,
        restartBackoffMax: svc.restartBackoffMax || 60000,
        startupOrder: svc.startupOrder || 99,
        startupDelay: svc.startupDelay || 0,
        dependsOn: svc.dependsOn || [],
        cleanupPorts: Array.isArray(svc.cleanupPorts) ? svc.cleanupPorts : [],
      };
    }
    
    return services;
  } catch (e) {
    console.error(`✗ 加载配置失败: ${e.message}`);
    console.error('请检查 services.json 格式是否正确');
    process.exit(1);
  }
}

// 服务定义 (从配置文件加载，或使用默认配置)
let SERVICES = {};

// === 进程状态 ===
const processes = {};  // name -> { proc, status, restarts, lastStart, lastExit, exitCode }

function log(msg, level = 'INFO') {
  const ts = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  const line = `[${ts}] [${level}] ${normalizeLogMessage(msg)}`;

  if (!stdoutBroken) {
    const ok = safeWriteToStream(process.stdout, line);
    if (!ok) stdoutBroken = true;
  }

  appendManagerLog(line);

  if (stdoutBroken && !epipeNoticeLogged) {
    epipeNoticeLogged = true;
    const notice = `[${ts}] [WARN] 检测到 stdout 管道断开(EPIPE)，后续仅写入日志文件`;
    appendManagerLog(notice);
    if (!stderrBroken) safeWriteToStream(process.stderr, notice);
  }
}

function getServiceLog(name, lines = 30) {
  const logFile = path.join(LOG_DIR, `${name}.log`);
  if (!fs.existsSync(logFile)) return '(无日志)';
  const content = fs.readFileSync(logFile, 'utf-8');
  const allLines = content.split('\n');
  return allLines.slice(-lines).join('\n');
}

// === 自杀防护 ===
function checkSuicideAttempt(pid) {
  if (PROTECTED_PIDS.has(pid)) {
    log(`🛡️ 自杀防护触发！拒绝终止 PM 自身进程 (PID: ${pid})`, 'ERROR');
    return true;
  }
  return false;
}

// === 心跳和状态持久化 ===
function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    try {
      fs.writeFileSync(HEARTBEAT_FILE, Date.now().toString());
    } catch (e) {
      log(`心跳写入失败: ${e.message}`, 'WARN');
    }
  }, 5000);
  log('💓 心跳监控已启动 (5秒间隔)', 'INFO');
}

function startStatePersistence() {
  stateSaveTimer = setInterval(() => {
    try {
      const state = {};
      for (const [name, proc] of Object.entries(processes)) {
        state[name] = {
          status: proc.status,
          pid: proc.pid,
          restarts: proc.restarts,
          lastStart: proc.lastStart,
          lastExit: proc.lastExit,
          exitCode: proc.exitCode,
          maxRestartReachedAt: proc.maxRestartReachedAt,
        };
      }
      fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
    } catch (e) {
      log(`状态持久化失败: ${e.message}`, 'WARN');
    }
  }, 30000);
  log('💾 状态持久化已启动 (30秒间隔)', 'INFO');
}

// === 健康检查和自动恢复 ===
function startHealthCheckMonitor() {
  healthCheckTimer = setInterval(async () => {
    for (const [name, svc] of Object.entries(SERVICES)) {
      // 跳过未启用自动重启的服务
      if (!svc.autoRestart) continue;
      
      const state = processes[name];
      
      // 对于未运行服务，补充“达到最大重启次数后的冷却恢复”逻辑
      if (!state || state.stopping) continue;
      if (state.status !== 'running') {
        if (state.status === 'stopped' && state.restarts >= svc.maxRestarts) {
          const cooldownMs = svc.restartBackoffMax || 60000;
          const reachedAt = state.maxRestartReachedAt || state.lastExit || 0;
          const elapsed = reachedAt ? (Date.now() - reachedAt) : cooldownMs;
          if (elapsed >= cooldownMs) {
            log(`♻️ ${svc.name} 达到最大重启次数后冷却完成，尝试自动恢复`, 'WARN');
            state.restarts = 0;
            state.maxRestartReachedAt = null;
            startService(name);
          }
        }
        continue;
      }
      
      // 检查进程是否真的还活着（僵尸进程检测）
      if (state.proc && state.pid && !isProcessAlive(state.pid)) {
        log(`💀 ${svc.name} 僵尸进程检测: PID ${state.pid} 已不存在`, 'WARN');
        state.status = 'stopped';
        state.pid = null;
        state.restarts = 0;  // 重置计数
        log(`🔄 立即重启 ${svc.name}...`, 'INFO');
        startService(name);
        continue;
      }
      
      // 如果有健康检查，执行健康检查
      if (svc.healthCheck) {
        const health = await checkHealth(name);
        
        // 如果健康检查失败，尝试恢复
        if (health.status === 'unhealthy') {
          const uptime = state.lastStart ? Math.round((Date.now() - state.lastStart) / 1000) : 0;
          log(`⚠️ ${svc.name} 健康检查失败 (运行时间: ${uptime}s)`, 'WARN');
          
          // 检查进程是否真的还活着
          if (state.proc && !state.proc.killed && isProcessAlive(state.proc.pid)) {
            log(`🔄 ${svc.name} 进程存在但不健康，强制重启...`, 'WARN');
            
            // 强制重启不健康的服务
            state.stopping = true;
            if (state.restartTimer) clearTimeout(state.restartTimer);
            
            state.proc.once('exit', () => {
              state.stopping = false;
              // 重置重启计数，因为这是健康检查触发的重启
              state.restarts = 0;
              setTimeout(() => startService(name), 2000);
            });
            
            try {
              process.kill(state.proc.pid, 'SIGKILL');
            } catch (e) {
              log(`终止不健康服务失败: ${e.message}`, 'ERROR');
            }
          } else {
            // 进程已经死了但状态没更新，直接重启
            log(`🔄 ${svc.name} 进程已死亡，立即重启...`, 'WARN');
            state.status = 'stopped';
            state.pid = null;
            state.restarts = 0;  // 重置计数
            startService(name);
          }
        }
      }
    }
  }, 30000);  // 每30秒检查一次
  log('🏥 健康检查监控已启动 (30秒间隔)', 'INFO');
}

// === 进程管理 ===
function isProcessAlive(pid) {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return false; }
}

function startService(name, options = {}) {
  const svc = SERVICES[name];
  if (!svc) { log(`未知服务: ${name}`, 'ERROR'); return false; }

  const visited = options.visited instanceof Set ? options.visited : new Set();
  if (visited.has(name)) {
    log(`检测到依赖循环，已跳过: ${name}`, 'ERROR');
    return false;
  }
  visited.add(name);

  if (processes[name]?.proc && !processes[name].proc.killed && isProcessAlive(processes[name].proc.pid)) {
    log(`${svc.name} 已在运行 (PID: ${processes[name].proc.pid})`);
    return true;
  }

  const dependencies = Array.isArray(svc.dependsOn) ? svc.dependsOn : [];
  for (const depName of dependencies) {
    if (!SERVICES[depName]) {
      log(`${svc.name} 依赖服务不存在或未启用: ${depName}`, 'ERROR');
      return false;
    }
    const depState = processes[depName];
    const depRunning = depState?.proc && !depState.proc.killed && isProcessAlive(depState.proc.pid);
    if (!depRunning) {
      log(`${svc.name} 依赖 ${depName} 未运行，先启动依赖`, 'INFO');
      const ok = startService(depName, { visited: new Set(visited) });
      if (!ok) {
        log(`${svc.name} 依赖 ${depName} 启动失败，已取消本次启动`, 'WARN');
        return false;
      }
    }
  }
  
  // 如果内存中记录了进程但实际已死亡，清理状态
  if (processes[name]?.proc && !isProcessAlive(processes[name].proc.pid)) {
    log(`${svc.name} 僵尸进程检测: PID ${processes[name].proc.pid} 已不存在，清理状态`, 'WARN');
    processes[name].status = 'stopped';
    processes[name].pid = null;
  }

  // Gateway 特殊处理：先停掉计划任务和残留进程
  if (name === 'gateway') {
    try {
      execSync('schtasks /End /TN "OpenClaw Gateway" 2>nul', { timeout: 5000 });
      log('已停止 Gateway 计划任务');
    } catch (e) {} // 任务不存在或已停止，忽略
    try {
      const result = execSync('netstat -ano | findstr :18789 | findstr LISTENING', { encoding: 'utf-8', timeout: 5000 });
      const pid = result.trim().split(/\s+/).pop();
      if (pid && pid !== '0') {
        execSync(`taskkill /PID ${pid} /T /F`, { timeout: 5000 });
        log(`已清理 Gateway 残留进程 (PID: ${pid})`);
      }
    } catch (e) {}
  }

  // Bridge 特殊处理：清理锁端口残留进程
  if (name === 'bridge') {
    try {
      const result = execSync('netstat -ano | findstr :29999 | findstr LISTENING', { encoding: 'utf-8', timeout: 5000 });
      const pid = result.trim().split(/\s+/).pop();
      if (pid && pid !== '0' && !checkSuicideAttempt(parseInt(pid))) {
        execSync(`taskkill /PID ${pid} /T /F`, { timeout: 5000 });
        log(`已清理 Bridge 残留进程 (PID: ${pid})`);
      }
    } catch (e) {} // 端口未被占用，正常
  }

  const logFile = path.join(LOG_DIR, `${name}.log`);

  // 使用服务配置中的环境变量（如果有）
  const spawnEnv = svc.env 
    ? { ...process.env, ...svc.env }
    : undefined;

  const proc = spawn(svc.cmd, svc.args, {
    cwd: svc.cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    detached: false,
    shell: true,  // 添加 shell 模式以支持 .cmd 文件
    ...(spawnEnv && { env: spawnEnv }),
  });

  // 实时监听输出
  if (name === 'napcat') {
    const handleOutput = (data) => {
      const text = data.toString();
      try { fs.appendFileSync(logFile, text); } catch(e){}
      
      if (text.includes('token=')) {
        const match = text.match(/(http:\/\/127\.0\.0\.1:\d+\/(web\/index\.html|webui)\?token=[a-zA-Z0-9]+)/);
        if (match) {
          const url = match[1];
          log(`\n🔔 [NapCat Login] 请访问以下地址登录 QQ:\n👉 ${url}\n`, 'IMPORTANT');
          try { fs.writeFileSync(path.join(__dirname, 'napcat-login.txt'), url); } catch(e){}
          require('child_process').exec(`start "" "${url}"`);
        }
      }
    };
    proc.stdout.on('data', handleOutput);
    proc.stderr.on('data', handleOutput);
  } else {
    // 其他进程只需要 stdout 导向日志文件
    proc.stdout.pipe(fs.createWriteStream(logFile, { flags: 'a' }));
    // stderr 也记录一下，防止报错漏掉
    proc.stderr.pipe(fs.createWriteStream(logFile, { flags: 'a' }));
  }

  const state = processes[name] || { restarts: 0 };
  state.proc = proc;
  state.status = 'running';
  state.lastStart = Date.now();
  state.pid = proc.pid;
  processes[name] = state;

  log(`✓ ${svc.name} 已启动 (PID: ${proc.pid})`);

  proc.on('exit', (code, signal) => {
    state.status = 'stopped';
    state.lastExit = Date.now();
    state.exitCode = code;
    state.pid = null;
    
    const uptime = state.lastExit - state.lastStart;
    log(`✗ ${svc.name} 退出 (code=${code}, signal=${signal}, uptime=${Math.round(uptime/1000)}s)`);
    
    // 如果运行超过60秒，重置重启计数
    if (uptime > 60000) state.restarts = 0;

    if (svc.autoRestart && state.restarts < svc.maxRestarts && !state.stopping) {
      state.restarts++;
      const delay = Math.min(svc.restartDelayMs * Math.pow(1.5, state.restarts - 1), svc.restartBackoffMax || 60000);
      log(`↻ ${svc.name} 将在 ${Math.round(delay/1000)}s 后重启 (第 ${state.restarts} 次)`, 'INFO');
      state.restartTimer = setTimeout(() => startService(name), delay);
    } else if (svc.autoRestart && state.restarts >= svc.maxRestarts && !state.stopping) {
      state.maxRestartReachedAt = Date.now();
      log(`⚠️ ${svc.name} 已达到最大重启次数 (${svc.maxRestarts})，进入冷却后由健康检查自动恢复`, 'WARN');
    }
  });

  proc.on('error', (err) => {
    log(`${svc.name} 进程错误: ${err.message}`, 'ERROR');
  });

  return true;
}

function stopService(name) {
  const state = processes[name];
  if (!state?.proc || state.proc.killed) {
    log(`${SERVICES[name]?.name || name} 未在运行`);
    return;
  }

  // 自杀防护检查
  if (checkSuicideAttempt(state.proc.pid)) {
    log('操作被拒绝：不能终止 PM 自身', 'ERROR');
    return;
  }

  state.stopping = true;
  if (state.restartTimer) clearTimeout(state.restartTimer);
  
  log(`⏹ 正在停止 ${SERVICES[name].name} (PID: ${state.pid})...`);
  
  try {
    // Windows: 使用 taskkill /T 杀掉整个进程树
    execSync(`taskkill /PID ${state.proc.pid} /T /F`, { timeout: 10000 });
    log(`✓ 已终止 ${SERVICES[name].name} 进程树`);
  } catch (e) {
    // taskkill 失败时 fallback 到 process.kill
    try {
      process.kill(state.proc.pid, 'SIGKILL');
      log(`⚠ taskkill 失败，已 fallback 强制终止 ${SERVICES[name].name}`);
    } catch (e2) {
      log(`停止失败: ${e2.message}`, 'ERROR');
    }
  }
}

function restartService(name) {
  const state = processes[name];
  // 核心逻辑优化：如果进程本就不在运行，直接启动，不走等待逻辑
  if (state?.proc && !state.proc.killed && state.status === 'running') {
    log(`正在重启服务: ${name}`);
    state.stopping = true;
    if (state.restartTimer) clearTimeout(state.restartTimer);
    
    // 超时保险：如果 5 秒后还没触发 exit，强行启动
    const forceStartTimer = setTimeout(() => {
      if (state.stopping) {
        log(`重启超时保险触发: ${name}`, 'WARN');
        state.stopping = false;
        startService(name);
      }
    }, 5000);

    state.proc.once('exit', () => {
      clearTimeout(forceStartTimer);
      state.stopping = false;
      state.restarts = 0;
      setTimeout(() => startService(name), 1000);
    });
    
    try { process.kill(state.proc.pid, 'SIGKILL'); } catch (e) {}
  } else {
    log(`服务未运行，直接尝试启动: ${name}`);
    if (state) { state.stopping = false; state.restarts = 0; }
    startService(name);
  }
}

async function checkHealth(name) {
  const svc = SERVICES[name];
  if (!svc?.healthCheck) return { status: 'no-check' };
  
  if (svc.healthCheck.type === 'http') {
    return new Promise((resolve) => {
      const req = http.get(svc.healthCheck.url, { timeout: 5000 }, (res) => {
        resolve({ status: res.statusCode === 200 ? 'healthy' : 'unhealthy', code: res.statusCode });
      });
      req.on('error', () => resolve({ status: 'unhealthy', error: 'unreachable' }));
      req.on('timeout', () => { req.destroy(); resolve({ status: 'unhealthy', error: 'timeout' }); });
    });
  }
  return { status: 'unknown' };
}

async function getStatus() {
  const result = {};
  for (const [name, svc] of Object.entries(SERVICES)) {
    const state = processes[name] || {};
    const health = await checkHealth(name);
    result[name] = {
      name: svc.name,
      status: state.status || 'not-started',
      pid: state.pid || null,
      uptime: state.lastStart && state.status === 'running' ? Math.round((Date.now() - state.lastStart) / 1000) : 0,
      restarts: state.restarts || 0,
      health: health.status,
      lastExit: state.lastExit ? new Date(state.lastExit).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : null,
      exitCode: state.exitCode ?? null,
    };
  }
  return result;
}

// === HTTP 控制接口 ===
function startControlServer() {
  const server = http.createServer(async (req, res) => {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    
    const url = new URL(req.url, 'http://localhost');
    const action = url.pathname.slice(1);  // /status -> status
    const target = url.searchParams.get('name');
    
    try {
      switch (action) {
        case 'status': {
          res.end(JSON.stringify(await getStatus(), null, 2));
          break;
        }
        case 'start': {
          if (target) { startService(target); }
          else { Object.keys(SERVICES).forEach(startService); }
          res.end(JSON.stringify({ ok: true, action: 'start', target: target || 'all' }));
          break;
        }
        case 'stop': {
          if (target) { stopService(target); }
          else { Object.keys(SERVICES).forEach(stopService); }
          res.end(JSON.stringify({ ok: true, action: 'stop', target: target || 'all' }));
          break;
        }
        case 'restart': {
          if (target) { restartService(target); }
          else { Object.keys(SERVICES).forEach(restartService); }
          res.end(JSON.stringify({ ok: true, action: 'restart', target: target || 'all' }));
          break;
        }
        case 'logs': {
          const lines = parseInt(url.searchParams.get('lines') || '30');
          res.end(getServiceLog(target || 'bridge', lines));
          break;
        }
        case 'health': {
          res.end(JSON.stringify({ status: 'ok', pm: 'sideria-pm v1.0' }));
          break;
        }
        case 'enable': {
          if (!target) {
            res.writeHead(400);
            res.end(JSON.stringify({ error: 'missing service name' }));
            break;
          }
          const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
          if (!config.services[target]) {
            res.writeHead(404);
            res.end(JSON.stringify({ error: 'service not found' }));
            break;
          }
          
          // 更新配置文件
          config.services[target].enabled = true;
          fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
          
          // 立即将服务添加到 SERVICES 对象
          const svc = config.services[target];
          SERVICES[target] = {
            name: svc.name,
            cmd: svc.cmd,
            args: svc.args || [],
            cwd: svc.cwd,
            env: svc.env || undefined,
            healthCheck: svc.healthCheck || null,
            preStart: svc.preStart || null,
            autoStart: svc.autoStart !== false,
            autoRestart: svc.autoRestart !== false,
            maxRestarts: svc.maxRestarts || 10,
            restartDelayMs: svc.restartDelayMs || 5000,
            restartBackoffMax: svc.restartBackoffMax || 60000,
            startupOrder: svc.startupOrder || 99,
            startupDelay: svc.startupDelay || 0,
            dependsOn: svc.dependsOn || [],
            cleanupPorts: Array.isArray(svc.cleanupPorts) ? svc.cleanupPorts : [],
          };
          
          // 初始化进程状态
          if (!processes[target]) {
            processes[target] = {
              proc: null,
              status: 'stopped',
              restarts: 0,
              lastStart: null,
              lastExit: null,
              exitCode: null,
            };
          }
          
          log(`服务 ${target} 已启用并加载到运行时`);
          res.end(JSON.stringify({ ok: true, action: 'enable', target, note: 'service loaded, use /start to run' }));
          break;
        }
        case 'disable': {
          if (!target) {
            res.writeHead(400);
            res.end(JSON.stringify({ error: 'missing service name' }));
            break;
          }
          const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
          if (!config.services[target]) {
            res.writeHead(404);
            res.end(JSON.stringify({ error: 'service not found' }));
            break;
          }
          
          // 先停止服务
          if (SERVICES[target]) {
            stopService(target);
          }
          
          // 更新配置文件
          config.services[target].enabled = false;
          fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
          
          // 从 SERVICES 对象中移除
          delete SERVICES[target];
          
          log(`服务 ${target} 已禁用并从运行时移除`);
          res.end(JSON.stringify({ ok: true, action: 'disable', target }));
          break;
        }
        default:
          res.writeHead(404);
          res.end(JSON.stringify({ error: 'unknown action', available: ['status','start','stop','restart','logs','health','enable','disable'] }));
      }
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: err.message }));
    }
  });
  
  server.listen(PM_PORT, '127.0.0.1', () => {
    log(`控制接口已启动: http://127.0.0.1:${PM_PORT}/`);
    log(`  GET /status           - 查看状态`);
    log(`  GET /start            - 启动全部`);
    log(`  GET /start?name=xxx   - 启动单个`);
    log(`  GET /stop             - 停止全部`);
    log(`  GET /restart          - 重启全部`);
    log(`  GET /logs?name=xxx    - 查看日志`);
    log(`  GET /enable?name=xxx  - 启用服务（需重启PM）`);
    log(`  GET /disable?name=xxx - 禁用服务`);
  });
}

// === CLI 入口 ===
async function main() {
  const argv = process.argv.slice(2);
  const action = argv[0] || 'start';
  const actionArgs = argv.slice(1);
  const cleanMode = actionArgs.includes('--clean') || actionArgs.includes('-c');
  const target = actionArgs.find((arg) => !arg.startsWith('-'));
  
  // 处理 setup 命令
  if (action === 'setup') {
    console.log('\n🔧 启动配置向导...\n');
    const { spawn } = require('child_process');
    const wizard = spawn(process.execPath, [path.join(__dirname, 'setup-wizard.js')], {
      stdio: 'inherit'
    });
    wizard.on('exit', (code) => process.exit(code));
    return;
  }
  
  // 加载服务配置 (除了 setup 命令外都需要)
  SERVICES = loadServicesConfig();
  
  // 如果不是 daemon 模式，通过 HTTP 发送命令
  if (action === 'status' || action === 'logs' || action === 'enable' || action === 'disable') {
    // 尝试连接已运行的 PM
    try {
      const url = target 
        ? `http://127.0.0.1:${PM_PORT}/${action}?name=${target}`
        : `http://127.0.0.1:${PM_PORT}/${action}`;
      const res = await fetch(url);
      const text = await res.text();
      
      if (action === 'enable' || action === 'disable') {
        const data = JSON.parse(text);
        if (action === 'enable') {
          console.log(`\n✅ 服务 ${target} 已启用并加载`);
          console.log('   💡 现在可以直接启动: node sideria-pm.js start ' + target + '\n');
        } else {
          console.log(`\n🛑 服务 ${target} 已禁用并停止\n`);
        }
        return;
      }
      
      if (action === 'status') {
        const data = JSON.parse(text);
        console.log('\n╔════════════════════════════════════════════════════════════════╗');
        console.log('║       🐉 希德莉亚进程管理器 v2.0 Universal                   ║');
        console.log('║          Sideria Process Manager                              ║');
        console.log('╚════════════════════════════════════════════════════════════════╝\n');
        
        // 统计信息
        const total = Object.keys(data).length;
        const running = Object.values(data).filter(s => s.status === 'running').length;
        const healthy = Object.values(data).filter(s => s.health === 'healthy').length;
        
        console.log(`📊 总览: ${running}/${total} 运行中  |  ${healthy} 健康  |  ${total - running} 已停止\n`);
        console.log('─'.repeat(64) + '\n');
        
        for (const [name, info] of Object.entries(data)) {
          const statusIcon = info.status === 'running' ? '🟢' : '🔴';
          const healthIcon = info.health === 'healthy' ? '💚' : info.health === 'no-check' ? '⚪' : '💔';
          
          // 格式化运行时间
          let uptimeStr = '-';
          if (info.uptime > 0) {
            const hours = Math.floor(info.uptime / 3600);
            const mins = Math.floor((info.uptime % 3600) / 60);
            const secs = info.uptime % 60;
            if (hours > 0) uptimeStr = `${hours}h ${mins}m ${secs}s`;
            else if (mins > 0) uptimeStr = `${mins}m ${secs}s`;
            else uptimeStr = `${secs}s`;
          }
          
          console.log(`${statusIcon} ${info.name}`);
          console.log(`   状态: ${info.status === 'running' ? '运行中' : '已停止'}  |  健康: ${healthIcon}  |  PID: ${info.pid || '-'}`);
          console.log(`   运行时间: ${uptimeStr}  |  重启次数: ${info.restarts}`);
          if (info.lastExit) {
            console.log(`   上次退出: ${info.lastExit} (退出码: ${info.exitCode})`);
          }
          console.log('');
        }
        
        console.log('─'.repeat(64));
        console.log('💡 提示: 使用 "node sideria-pm.js start <服务名>" 启动单个服务');
        console.log('        使用 "node sideria-pm.js logs <服务名>" 查看日志');
        console.log('─'.repeat(64) + '\n');
      } else {
        console.log(text);
      }
      return;
    } catch (e) {
      if (action === 'status') {
        console.log('🔴 Sideria PM 未运行。使用 "node sideria-pm.js start" 启动。');
        return;
      }
    }
  }

  // 尝试向已运行的 PM 发送命令
  if (['stop', 'restart'].includes(action)) {
    try {
      const url = target
        ? `http://127.0.0.1:${PM_PORT}/${action}?name=${target}`
        : `http://127.0.0.1:${PM_PORT}/${action}`;
      const res = await fetch(url);
      const data = await res.json();
      
      if (action === 'stop') {
        console.log('\n🛑 停止命令已发送');
        console.log(`   目标: ${target || '所有服务'}`);
      } else if (action === 'restart') {
        console.log('\n🔄 重启命令已发送');
        console.log(`   目标: ${target || '所有服务'}`);
      }
      console.log('   响应:', JSON.stringify(data));
      console.log('');
      return;
    } catch (e) {
      if (action === 'stop') {
        console.log('PM 未运行，无需停止。');
        return;
      }
      // restart 时如果 PM 没运行，走 start 流程
    }
  }

  if (action === 'start' || action === 'restart') {
    // 检查 PM 是否已在运行
    try {
      const res = await fetch(`http://127.0.0.1:${PM_PORT}/health`);
      if (res.ok) {
        if (target) {
          // 启动单个服务
          const r = await fetch(`http://127.0.0.1:${PM_PORT}/start?name=${target}`);
          console.log(`✓ 已通知 PM 启动 ${target}`);
        } else {
          console.log('🐉 Sideria PM 已在运行。使用 "status" 查看状态。');
        }
        return;
      }
    } catch (e) {
      // PM 未运行，继续启动
    }

    // 锁检查
    const lockServer = net.createServer();
    lockServer.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        console.log('⚠ PM 锁端口被占用，可能已有实例运行。');
        process.exit(1);
      }
    });
    lockServer.listen(PM_LOCK_PORT, '127.0.0.1', () => {
      console.log('\n╔════════════════════════════════════════════════════════════════╗');
      console.log('║       🐉 希德莉亚进程管理器 v2.0 Universal                   ║');
      console.log('║          Sideria Process Manager                              ║');
      console.log('╚════════════════════════════════════════════════════════════════╝\n');
      
      log('🚀 正在启动进程管理器...');
      if (cleanMode) {
        log('🧹 清理模式: 将先清理残留进程');
      } else {
        log('🛡️ 兼容模式: 保留现有进程');
      }
      
      log('');
      log('📋 增强功能:');
      log('   ✅ 自杀防护 - 防止误杀 PM 自身');
      log('   ✅ 心跳监控 - 每 5 秒更新状态');
      log('   ✅ 状态持久化 - 每 30 秒保存快照');
      log('   ✅ 全局异常捕获 - 防止崩溃');
      log('   ✅ Live2D 手动启动 - 节省资源');
      log('');

      // 启动心跳和状态持久化
      startHeartbeat();
      startStatePersistence();
      startHealthCheckMonitor();  // 启动健康检查监控

      const bootServices = () => {
        startControlServer();
        
        log('');
        log('🔧 开始启动服务...');
        log('─'.repeat(64));

        // 启动所有服务
        if (target) {
          log(`📦 启动单个服务: ${target}`);
          startService(target);
        } else {
          // 按 startupOrder 排序服务（全量启动时默认跳过 live2d 与 gcli2api/反代）
          const EXCLUDED_FROM_BULK_START = new Set(['live2d', 'gcli2api']);
          const sortedServices = Object.entries(SERVICES)
            .filter(([name, svc]) => svc.autoStart !== false && !EXCLUDED_FROM_BULK_START.has(name))
            .sort(([, a], [, b]) => (a.startupOrder || 99) - (b.startupOrder || 99));
          
          log('📦 按配置顺序启动所有服务（已排除 live2d、gcli2api）:');
          sortedServices.forEach(([name, svc], index) => {
            const emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][index] || '▪️';
            log(`   ${emoji}  ${svc.name}`);
          });
          
          // 列出手动启动的服务 + 全量启动默认排除的服务
          const manualServices = Object.entries(SERVICES)
            .filter(([name, svc]) => svc.autoStart === false || EXCLUDED_FROM_BULK_START.has(name));
          if (manualServices.length > 0) {
            manualServices.forEach(([name, svc]) => {
              const reason = EXCLUDED_FROM_BULK_START.has(name) ? '全量启动默认跳过' : '手动启动';
              log(`   ⚪ ${svc.name} (${reason})`);
            });
          }
          log('');
          
          // 按顺序启动服务
          sortedServices.forEach(([name, svc]) => {
            const delay = svc.startupDelay || 0;
            if (delay === 0) {
              startService(name);
            } else {
              setTimeout(() => startService(name), delay);
            }
          });
          
          // 启动完成提示
          const maxDelay = Math.max(...sortedServices.map(([, svc]) => svc.startupDelay || 0));
          setTimeout(() => {
            log('');
            log('─'.repeat(64));
            log('✅ 所有服务已调度启动！');
            log('');
            log('💡 提示:');
            log('   • 查看状态: node sideria-pm.js status');
            log('   • 查看日志: node sideria-pm.js logs <服务名>');
            if (manualServices.length > 0) {
              manualServices.forEach(([name, svc]) => {
                log(`   • 启动 ${svc.name}: node sideria-pm.js start ${name}`);
              });
            }
            log('   • HTTP API: http://127.0.0.1:29997/status');
            log('   • 重新配置: node sideria-pm.js setup');
            log('─'.repeat(64));
            log('');
          }, maxDelay + 2000);
        }
      };

      if (cleanMode) {
        killExistingProcesses().then(bootServices);
      } else {
        bootServices();
      }
    });
  }
}

async function killExistingProcesses() {
  // 清理可能残留的进程
  try {
    // 停止 Gateway 计划任务
    try {
      execSync('schtasks /End /TN "OpenClaw Gateway" 2>nul', { timeout: 5000 });
      log('已停止 Gateway 计划任务');
    } catch (e) {}

    // 强制清理 QQ/NapCat 残留
    try {
      execSync('taskkill /F /IM NapCatWinBootMain.exe /T 2>nul', { timeout: 5000 });
      log('已清理残留 NapCat 进程');
    } catch (e) {}

    // 按端口清理残留进程（内置端口 + 配置中的健康检查端口 + cleanupPorts）
    const managedPorts = new Map([
      [18789, 'gateway'],
      [29998, 'bridge (health)'],
      [29999, 'bridge (lock)'],
      [8188, 'comfyui'],
      [9880, 'gpt_sovits'],
      [5000, 'vector_server'],
    ]);

    for (const [svcName, svc] of Object.entries(SERVICES)) {
      if (svc?.healthCheck?.type === 'http' && typeof svc.healthCheck.url === 'string') {
        try {
          const p = Number(new URL(svc.healthCheck.url).port);
          if (Number.isInteger(p) && p > 0) managedPorts.set(p, svcName);
        } catch (e) {}
      }
      if (Array.isArray(svc.cleanupPorts)) {
        for (const p of svc.cleanupPorts) {
          const port = Number(p);
          if (Number.isInteger(port) && port > 0) managedPorts.set(port, `${svcName} (cleanupPorts)`);
        }
      }
    }

    for (const [port, svcName] of managedPorts.entries()) {
      try {
        const result = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf-8', timeout: 5000 });
        const lines = result.trim().split('\n');
        const pids = new Set();
        for (const line of lines) {
          const pid = line.trim().split(/\s+/).pop();
          if (pid && pid !== '0') pids.add(pid);
        }
        for (const pid of pids) {
          try {
            execSync(`taskkill /PID ${pid} /T /F`, { timeout: 5000 });
            log(`已清理残留 ${svcName} 进程 (PID: ${pid})`);
          } catch (e) {}
        }
      } catch (e) {} // 端口没被占用，正常
    }

    // 检查 memory-recorder 进程
    try {
      const result = execSync('wmic process where "CommandLine like \'%memory-recorder%\'" get ProcessId /format:list', { encoding: 'utf-8', timeout: 5000 });
      const pids = result.match(/ProcessId=(\d+)/g);
      if (pids) {
        for (const match of pids) {
          const pid = match.split('=')[1];
          try { execSync(`taskkill /PID ${pid} /F`, { timeout: 5000 }); } catch (e) {}
        }
        log(`已清理残留 recorder 进程`);
      }
    } catch (e) {}

    // 清理 Electron (Live2D) 残留
    try {
      execSync('taskkill /F /IM electron.exe /T 2>nul', { timeout: 5000 });
      log('已清理残留 Electron/Live2D 进程');
    } catch (e) {}

    // 等待端口释放
    await new Promise(r => setTimeout(r, 1500));
  } catch (e) {
    log(`清理残留进程时异常: ${e.message}`, 'WARN');
  }
}

// 优雅退出
process.on('SIGINT', () => {
  log('收到 SIGINT，正在停止所有服务...');
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  if (stateSaveTimer) clearInterval(stateSaveTimer);
  if (healthCheckTimer) clearInterval(healthCheckTimer);
  Object.keys(SERVICES).forEach(stopService);
  setTimeout(() => process.exit(0), 5000);
});

process.on('SIGTERM', () => {
  log('收到 SIGTERM，正在停止所有服务...');
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  if (stateSaveTimer) clearInterval(stateSaveTimer);
  if (healthCheckTimer) clearInterval(healthCheckTimer);
  Object.keys(SERVICES).forEach(stopService);
  setTimeout(() => process.exit(0), 5000);
});

// 全局异常捕获
process.on('uncaughtException', (err) => {
  if (handlingUncaughtException) return;
  handlingUncaughtException = true;

  try {
    if (isBrokenPipeError(err)) {
      stdoutBroken = true;
      const ts = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
      const notice = `[${ts}] [WARN] 捕获到 EPIPE（输出管道断开），已切换为仅文件日志模式`;
      appendManagerLog(notice);
      if (!stderrBroken) safeWriteToStream(process.stderr, notice);
      return;
    }

    log(`未捕获异常: ${err.message}`, 'ERROR');
    if (err?.stack) log(err.stack, 'ERROR');
    // 非 EPIPE 异常：记录后继续运行
  } finally {
    handlingUncaughtException = false;
  }
});

process.on('unhandledRejection', (reason) => {
  if (isBrokenPipeError(reason)) {
    stdoutBroken = true;
    const ts = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
    const notice = `[${ts}] [WARN] Promise 拒绝包含 EPIPE，已切换为仅文件日志模式`;
    appendManagerLog(notice);
    if (!stderrBroken) safeWriteToStream(process.stderr, notice);
    return;
  }

  log(`未处理的 Promise 拒绝: ${normalizeLogMessage(reason)}`, 'ERROR');
  if (reason instanceof Error && reason.stack) {
    log(reason.stack, 'ERROR');
  }
});

main().catch(err => {
  if (isBrokenPipeError(err)) {
    stdoutBroken = true;
    const ts = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
    const notice = `[${ts}] [WARN] 主流程捕获到 EPIPE，保持运行并记录到日志文件`;
    appendManagerLog(notice);
    if (!stderrBroken) safeWriteToStream(process.stderr, notice);
    return;
  }

  const message = `PM 异常: ${normalizeLogMessage(err)}`;
  appendManagerLog(`[${new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}] [ERROR] ${message}`);
  if (!stderrBroken) safeWriteToStream(process.stderr, message);
  process.exit(1);
});
