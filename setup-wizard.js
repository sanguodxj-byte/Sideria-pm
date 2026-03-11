/**
 * Sideria PM Setup Wizard
 * 首次配置引导向导
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const CONFIG_FILE = path.join(__dirname, 'services.json');
const TEMPLATE_FILE = path.join(__dirname, 'services.template.json');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

function log(msg, level = 'INFO') {
  const colors = {
    INFO: '\x1b[36m',    // Cyan
    SUCCESS: '\x1b[32m', // Green
    WARN: '\x1b[33m',    // Yellow
    ERROR: '\x1b[31m',   // Red
    RESET: '\x1b[0m'
  };
  console.log(`${colors[level] || ''}${msg}${colors.RESET}`);
}

function banner() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║       🐉 Sideria PM - 首次配置向导                           ║');
  console.log('║          Setup Wizard v1.0                                    ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');
}

/**
 * 在指定目录及其子目录中搜索文件
 * @param {string} rootDir - 根目录
 * @param {string} fileName - 文件名（支持通配符）
 * @param {number} maxDepth - 最大搜索深度
 * @returns {string[]} 找到的文件路径数组
 */
function searchFiles(rootDir, fileName, maxDepth = 3) {
  const results = [];

  function search(dir, depth) {
    if (depth > maxDepth) return;

    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
          // 跳过常见的无关目录
          const skipDirs = ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'];
          if (!skipDirs.includes(entry.name)) {
            search(fullPath, depth + 1);
          }
        } else if (entry.isFile()) {
          // 简单的通配符匹配
          const pattern = fileName.replace(/\*/g, '.*').replace(/\?/g, '.');
          const regex = new RegExp(`^${pattern}$`, 'i');
          if (regex.test(entry.name)) {
            results.push(fullPath);
          }
        }
      }
    } catch (e) {
      // 忽略权限错误等
    }
  }

  search(rootDir, 0);
  return results;
}

/**
 * 智能检测可执行文件路径
 * @param {string} rootDir - 项目根目录
 * @param {string} type - 文件类型 (python, node, electron, exe)
 * @param {string} hint - 提示信息（如服务名）
 * @returns {string[]} 候选路径数组
 */
function smartDetectExecutable(rootDir, type, hint = '') {
  const candidates = [];

  switch (type) {
    case 'python':
      // 1. 在根目录查找虚拟环境
      const venvPaths = [
        path.join(rootDir, 'venv', 'Scripts', 'python.exe'),
        path.join(rootDir, '.venv', 'Scripts', 'python.exe'),
        path.join(rootDir, 'runtime', 'python.exe'),
      ];
      candidates.push(...venvPaths.filter(p => fs.existsSync(p)));

      // 2. 在子目录中搜索 python.exe
      const foundPython = searchFiles(rootDir, 'python.exe', 2);
      candidates.push(...foundPython);

      // 3. 系统 Python
      const systemPython = [
        'C:\\Python39\\python.exe',
        'C:\\Python310\\python.exe',
        'C:\\Python311\\python.exe',
        'C:\\Python312\\python.exe',
      ];
      candidates.push(...systemPython.filter(p => fs.existsSync(p)));
      break;

    case 'node':
      candidates.push('node'); // 系统 PATH 中的 node
      break;

    case 'electron':
      // 在根目录查找 electron
      const electronPaths = searchFiles(rootDir, 'electron.exe', 3);
      candidates.push(...electronPaths);
      break;

    case 'exe':
      // 根据 hint 搜索特定的 exe
      if (hint) {
        const exePaths = searchFiles(rootDir, `*${hint}*.exe`, 2);
        candidates.push(...exePaths);
      }
      break;
  }

  // 去重
  return [...new Set(candidates)];
}

/**
 * 智能检测主脚本路径
 * @param {string} rootDir - 项目根目录
 * @param {string} scriptName - 脚本名称或模式
 * @returns {string[]} 候选路径数组
 */
function smartDetectScript(rootDir, scriptName) {
  const candidates = [];

  // 1. 直接在根目录查找
  const rootScript = path.join(rootDir, scriptName);
  if (fs.existsSync(rootScript)) {
    candidates.push(rootScript);
  }

  // 2. 在常见目录中查找
  const commonDirs = ['src', 'lib', 'app', 'server', 'api'];
  for (const dir of commonDirs) {
    const scriptPath = path.join(rootDir, dir, scriptName);
    if (fs.existsSync(scriptPath)) {
      candidates.push(scriptPath);
    }
  }

  // 3. 递归搜索（限制深度）
  const foundScripts = searchFiles(rootDir, scriptName, 2);
  candidates.push(...foundScripts);

  // 去重
  return [...new Set(candidates)];
}

async function detectPath(candidates, description) {
  log(`\n🔍 正在检测 ${description}...`, 'INFO');

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      log(`✓ 找到: ${candidate}`, 'SUCCESS');
      return candidate;
    }
  }

  log(`✗ 未找到 ${description}`, 'WARN');
  return null;
}

/**
 * 为主脚本候选项进行智能模糊打分，选出最可能的业务脚本
 */
function findBestCandidate(candidates, serviceName, templateCwd, targetPathHint = '') {
  if (!candidates || candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0];

  let bestMatch = null;
  let highestScore = -Infinity;

  const keywords = [
    serviceName.toLowerCase(),
    path.basename(templateCwd || '').toLowerCase()
  ].filter(Boolean);

  for (const candidate of candidates) {
    let score = 0;
    const lowerPath = candidate.toLowerCase();

    // 1. 特征词大幅加分
    for (const kw of keywords) {
      if (lowerPath.includes(kw)) score += 10;
    }

    // 2. 原始路径线索加分
    if (targetPathHint && lowerPath.includes(targetPathHint.toLowerCase())) {
      score += 5;
    }

    // 3. 严厉惩罚常见的无关包或虚拟环境目录
    if (lowerPath.includes('node_modules') || lowerPath.includes('site-packages') || lowerPath.includes('.venv')) {
      score -= 20;
    }

    // 4. 层级深度惩罚 (越深的路径说明越大概率是子依赖而不是根业务)
    const depth = candidate.split(path.sep).length;
    score -= (depth * 0.5);

    if (score > highestScore) {
      highestScore = score;
      bestMatch = candidate;
    }
  }

  return bestMatch;
}

/**
 * 智能检测服务的可执行文件和脚本
 * @param {string} name - 服务标识名
 * @param {string} service - 服务配置对象
 * @param {string} rootDir - 项目根目录
 * @returns {object} 检测结果 { cmd, mainScript, cwd }
 */
async function smartDetectService(name, service, rootDir) {
  const result = { cmd: null, mainScript: null, cwd: null };

  // 1. 检测可执行文件
  if (service.cmd.includes('python.exe')) {
    // Python 应用
    const pythonCandidates = smartDetectExecutable(rootDir, 'python');

    // 优先选择与 cwd 相关的 Python
    if (service.cwd) {
      const cwdPython = pythonCandidates.find(p => p.includes(path.basename(service.cwd)));
      result.cmd = cwdPython || (pythonCandidates.length > 0 ? pythonCandidates[0] : service.cmd);
    } else {
      result.cmd = pythonCandidates.length > 0 ? pythonCandidates[0] : service.cmd;
    }

    // 检测主脚本
    if (service.args && service.args.length > 0) {
      const scriptArg = service.args[0];
      const scriptName = path.basename(scriptArg);
      const scriptCandidates = smartDetectScript(rootDir, scriptName);

      const scriptDirHint = (scriptArg.includes('/') || scriptArg.includes('\\'))
        ? path.dirname(scriptArg).replace(/\.\./g, '').replace(/^[\\\/]+/, '')
        : '';

      const bestMatch = findBestCandidate(scriptCandidates, name, service.cwd, scriptDirHint);

      if (bestMatch) {
        result.mainScript = bestMatch;
        result.cwd = path.dirname(bestMatch);
      }
    }
  } else if (service.cmd.includes('electron.exe')) {
    // Electron 应用
    const electronCandidates = smartDetectExecutable(rootDir, 'electron');

    // 优先选择与 cwd 相关的 Electron
    if (service.cwd) {
      const cwdElectron = electronCandidates.find(p => p.includes(service.cwd));
      result.cmd = cwdElectron || (electronCandidates.length > 0 ? electronCandidates[0] : service.cmd);
    } else {
      result.cmd = electronCandidates.length > 0 ? electronCandidates[0] : service.cmd;
    }

    if (result.cmd && fs.existsSync(result.cmd)) {
      // electron.exe 在 node_modules/electron/dist/，项目根目录在上三级
      result.cwd = path.dirname(path.dirname(path.dirname(result.cmd)));
    }
  } else if (service.cmd === 'node') {
    // Node.js 应用
    result.cmd = 'node';

    // 检测主脚本
    if (service.args && service.args.length > 0) {
      const scriptArg = service.args[0];
      const scriptName = path.basename(scriptArg);
      const scriptCandidates = smartDetectScript(rootDir, scriptName);

      const scriptDirHint = (scriptArg.includes('/') || scriptArg.includes('\\'))
        ? path.dirname(scriptArg).replace(/\.\./g, '').replace(/^[\\\/]+/, '')
        : '';

      const bestMatch = findBestCandidate(scriptCandidates, name, service.cwd, scriptDirHint);

      if (bestMatch) {
        result.mainScript = bestMatch;
        result.cwd = path.dirname(bestMatch);
      }
    }
  } else if (service.cmd.includes('.exe')) {
    // 其他可执行文件
    const exeName = path.basename(service.cmd);
    const exeCandidates = searchFiles(rootDir, exeName, 3);

    // 优先选择与原始路径匹配的
    let bestMatch = null;
    if (service.cmd.includes('\\')) {
      const cmdDir = path.dirname(service.cmd);
      bestMatch = exeCandidates.find(p => p.includes(cmdDir));
    }
    if (!bestMatch && exeCandidates.length > 0) {
      bestMatch = exeCandidates[0];
    }

    result.cmd = bestMatch || service.cmd;
    if (result.cmd && fs.existsSync(result.cmd)) {
      result.cwd = path.dirname(result.cmd);
    }
  }

  // 2. 如果没有检测到工作目录，使用配置中的
  if (!result.cwd && service.cwd) {
    result.cwd = service.cwd;
  }

  return result;
}

async function promptPath(detected, description, required = true) {
  if (detected) {
    const answer = await question(`使用检测到的路径? (Y/n): `);
    if (answer.toLowerCase() !== 'n') {
      return detected;
    }
  }

  while (true) {
    const answer = await question(`请输入 ${description} 的路径 ${required ? '' : '(留空跳过)'}: `);

    if (!answer && !required) {
      return null;
    }

    if (!answer && required) {
      log(`⚠️  路径为空，将禁用该服务`, 'WARN');
      return null; // 返回 null 表示禁用服务
    }

    if (answer && fs.existsSync(answer)) {
      log(`✓ 路径有效`, 'SUCCESS');
      return answer;
    }

    log(`✗ 路径不存在，请重新输入`, 'ERROR');
  }
}

async function setupService(name, service, config, rootDir) {
  log(`\n━━━ 检测服务: ${service.name} ━━━`, 'INFO');

  // 智能检测服务路径
  log(`\n🤖 正在智能检测服务路径...`, 'INFO');
  const detected = await smartDetectService(name, service, rootDir);

  // 特殊处理 Gateway - 使用全局命令
  if (name === 'gateway') {
    // 检查 openclaw 命令是否可用
    const { execSync } = require('child_process');
    try {
      execSync('openclaw --version', { stdio: 'pipe', timeout: 5000 });
      log(`✓ 检测到 OpenClaw Gateway (全局命令)`, 'SUCCESS');
      service.cmd = 'openclaw';
      service.args = ['gateway'];
      service.cwd = rootDir;
      service.enabled = true;
      log(`✓ ${service.name} 配置完成`, 'SUCCESS');
      return;
    } catch (e) {
      log(`✗ 未检测到 OpenClaw Gateway`, 'ERROR');
      log(`请确保已安装: npm install -g @qingchencloud/openclaw-zh`, 'WARN');
      const manualConfig = await question(`是否手动配置 Gateway? (y/N): `);
      if (manualConfig.toLowerCase() !== 'y') {
        service.enabled = false;
        log(`⊘ Gateway 未配置，已禁用`, 'WARN');
        return;
      }
      // 继续手动配置流程
    }
  }

  // 显示检测结果
  let autoConfigured = true;

  if (detected.cmd && (fs.existsSync(detected.cmd) || detected.cmd === 'node')) {
    log(`✓ 检测到可执行文件: ${detected.cmd}`, 'SUCCESS');
    service.cmd = detected.cmd;
  } else {
    log(`✗ 未检测到可执行文件`, 'WARN');
    autoConfigured = false;
  }

  if (detected.mainScript && fs.existsSync(detected.mainScript)) {
    log(`✓ 检测到主脚本: ${detected.mainScript}`, 'SUCCESS');
    const relativePath = path.relative(detected.cwd || service.cwd, detected.mainScript);
    service.args[0] = relativePath || detected.mainScript;
  } else if (service.args && service.args.length > 0 && (service.args[0].includes('.py') || service.args[0].includes('.js'))) {
    log(`✗ 未检测到主脚本`, 'WARN');
    autoConfigured = false;
  }

  if (detected.cwd && fs.existsSync(detected.cwd)) {
    log(`✓ 检测到工作目录: ${detected.cwd}`, 'SUCCESS');
    service.cwd = detected.cwd;
  } else {
    log(`✗ 未检测到工作目录`, 'WARN');
    autoConfigured = false;
  }

  // 如果完全自动配置成功，直接启用
  if (autoConfigured) {
    service.enabled = true;
    log(`✓ ${service.name} 自动配置完成并启用`, 'SUCCESS');
    return;
  }

  // 否则询问用户是否手动配置
  log(`\n⚠ 无法完全自动检测 ${service.name}`, 'WARN');
  const manualConfig = await question(`是否手动配置此服务? (y/N): `);

  if (manualConfig.toLowerCase() !== 'y') {
    service.enabled = false;
    log(`⊘ 已跳过 ${service.name}`, 'WARN');
    return;
  }

  service.enabled = true;

  // 配置可执行文件
  if (service.cmd !== 'node') {
    const useDetected = detected.cmd && fs.existsSync(detected.cmd);
    if (useDetected) {
      const answer = await question(`使用检测到的可执行文件? (Y/n): `);
      if (answer.toLowerCase() !== 'n') {
        service.cmd = detected.cmd;
      } else {
        const manualCmd = await promptPath(null, '可执行文件路径', true);
        if (!manualCmd) {
          service.enabled = false;
          log(`⊘ 未配置可执行文件，已禁用 ${service.name}`, 'WARN');
          return;
        }
        service.cmd = manualCmd;
      }
    } else {
      const manualCmd = await promptPath(service.cmd, '可执行文件路径', true);
      if (!manualCmd) {
        service.enabled = false;
        log(`⊘ 未配置可执行文件，已禁用 ${service.name}`, 'WARN');
        return;
      }
      service.cmd = manualCmd;
    }
  }

  // 配置工作目录
  const useCwd = detected.cwd && fs.existsSync(detected.cwd);
  if (useCwd) {
    const answer = await question(`使用检测到的工作目录? (Y/n): `);
    if (answer.toLowerCase() !== 'n') {
      service.cwd = detected.cwd;
    } else {
      const manualCwd = await promptPath(null, '工作目录', true);
      if (!manualCwd) {
        service.enabled = false;
        log(`⊘ 未配置工作目录，已禁用 ${service.name}`, 'WARN');
        return;
      }
      service.cwd = manualCwd;
    }
  } else {
    const manualCwd = await promptPath(service.cwd, '工作目录', true);
    if (!manualCwd) {
      service.enabled = false;
      log(`⊘ 未配置工作目录，已禁用 ${service.name}`, 'WARN');
      return;
    }
    service.cwd = manualCwd;
  }

  // 配置主脚本
  if (service.args && service.args.length > 0) {
    const mainScript = service.args[0];
    if (mainScript.includes('.py') || mainScript.includes('.js')) {
      const useScript = detected.mainScript && fs.existsSync(detected.mainScript);

      if (useScript) {
        const answer = await question(`使用检测到的主脚本? (Y/n): `);
        if (answer.toLowerCase() !== 'n') {
          // 转换为相对路径（相对于工作目录）
          const relativePath = path.relative(service.cwd, detected.mainScript);
          service.args[0] = relativePath || detected.mainScript;
        } else {
          const scriptPath = path.isAbsolute(mainScript)
            ? mainScript
            : path.join(service.cwd, mainScript);

          if (!fs.existsSync(scriptPath)) {
            log(`⚠ 主脚本不存在: ${scriptPath}`, 'WARN');
            const newScript = await question(`请输入正确的脚本路径 (相对于工作目录，留空禁用): `);
            if (!newScript) {
              service.enabled = false;
              log(`⊘ 未配置主脚本，已禁用 ${service.name}`, 'WARN');
              return;
            }
            service.args[0] = newScript;
          }
        }
      } else {
        const scriptPath = path.isAbsolute(mainScript)
          ? mainScript
          : path.join(service.cwd, mainScript);

        if (!fs.existsSync(scriptPath)) {
          log(`⚠ 主脚本不存在: ${scriptPath}`, 'WARN');
          const newScript = await question(`请输入正确的脚本路径 (相对于工作目录，留空禁用): `);
          if (!newScript) {
            service.enabled = false;
            log(`⊘ 未配置主脚本，已禁用 ${service.name}`, 'WARN');
            return;
          }
          service.args[0] = newScript;
        }
      }
    }
  }

  // 健康检查配置
  if (service.healthCheck) {
    const configHealth = await question(`配置健康检查? (y/N): `);
    if (configHealth.toLowerCase() === 'y') {
      const url = await question(`健康检查 URL [${service.healthCheck.url}]: `);
      if (url) service.healthCheck.url = url;
    }
  }

  log(`✓ ${service.name} 配置完成`, 'SUCCESS');
}

async function main() {
  banner();

  // 检查是否已有配置
  if (fs.existsSync(CONFIG_FILE)) {
    log('⚠ 检测到已有配置文件', 'WARN');
    const answer = await question('是否重新配置? (y/N): ');
    if (answer.toLowerCase() !== 'y') {
      log('配置向导已取消', 'INFO');
      rl.close();
      return;
    }

    // 备份旧配置
    const backup = `${CONFIG_FILE}.backup.${Date.now()}`;
    fs.copyFileSync(CONFIG_FILE, backup);
    log(`已备份旧配置到: ${backup}`, 'INFO');
  }

  // 加载模板
  let config;
  try {
    const template = fs.readFileSync(TEMPLATE_FILE, 'utf-8');
    config = JSON.parse(template);
  } catch (e) {
    log(`✗ 无法加载模板文件: ${e.message}`, 'ERROR');
    rl.close();
    return;
  }

  log('\n开始配置向导...', 'INFO');
  log('提示: 按 Ctrl+C 可随时退出\n', 'WARN');

  // 全局配置
  log('━━━ 全局配置 ━━━', 'INFO');
  const workspaceRoot = await question(`工作区根目录 [${path.dirname(__dirname)}]: `);
  const rootDir = workspaceRoot || path.dirname(__dirname);

  if (workspaceRoot) {
    // 更新所有相对路径
    for (const [name, service] of Object.entries(config.services)) {
      if (service.cwd && !path.isAbsolute(service.cwd)) {
        service.cwd = path.join(workspaceRoot, service.cwd);
      }
    }
  }

  log(`\n📁 工作区根目录: ${rootDir}`, 'INFO');
  log(`🔍 将在此目录及子目录中自动搜索文件`, 'INFO');

  // 配置每个服务
  log('\n━━━ 自动检测服务 ━━━', 'INFO');
  log('正在自动检测并配置所有服务...\n', 'INFO');

  for (const [name, service] of Object.entries(config.services)) {
    await setupService(name, service, config, rootDir);
  }

  // 显示配置汇总
  log('\n━━━ 配置汇总 ━━━', 'INFO');
  const enabledServices = Object.values(config.services).filter(s => s.enabled);
  const disabledServices = Object.values(config.services).filter(s => !s.enabled);

  log(`\n✓ 已启用 ${enabledServices.length} 个服务:`, 'SUCCESS');
  enabledServices.forEach(s => log(`  • ${s.name}`, 'INFO'));

  if (disabledServices.length > 0) {
    log(`\n⊘ 已禁用 ${disabledServices.length} 个服务:`, 'WARN');
    disabledServices.forEach(s => log(`  • ${s.name}`, 'WARN'));
  }

  // 保存配置
  log('\n━━━ 保存配置 ━━━', 'INFO');
  const preview = JSON.stringify(config, null, 2);

  const confirm = await question('\n查看完整配置? (y/N): ');
  if (confirm.toLowerCase() === 'y') {
    console.log('\n' + preview + '\n');
  }

  const save = await question('保存配置? (Y/n): ');
  if (save.toLowerCase() === 'n') {
    log('配置未保存', 'WARN');
    rl.close();
    return;
  }

  try {
    fs.writeFileSync(CONFIG_FILE, preview, 'utf-8');
    log(`\n✓ 配置已保存到: ${CONFIG_FILE}`, 'SUCCESS');

    log('\n━━━ 配置完成 ━━━', 'SUCCESS');
    log('\n下一步:', 'INFO');
    log('  1. 运行 "node sideria-pm.js start" 启动所有服务', 'INFO');
    log('  2. 运行 "node sideria-pm.js status" 查看状态', 'INFO');
    log('  3. 如需修改配置，编辑 services.json 或重新运行此向导\n', 'INFO');
  } catch (e) {
    log(`✗ 保存失败: ${e.message}`, 'ERROR');
  }

  rl.close();
}

// 优雅退出
process.on('SIGINT', () => {
  log('\n\n配置向导已取消', 'WARN');
  rl.close();
  process.exit(0);
});

main().catch(err => {
  log(`✗ 向导异常: ${err.message}`, 'ERROR');
  rl.close();
  process.exit(1);
});
