/**
 * Sideria PM v1.x to v2.0 Migration Tool
 * 从 v1.x 迁移到 v2.0 的工具
 */

const fs = require('fs');
const path = require('path');

const CONFIG_FILE = path.join(__dirname, 'services.json');
const TEMPLATE_FILE = path.join(__dirname, 'services.template.json');
const OLD_PM_FILE = path.join(__dirname, 'sideria-pm.js.v1.backup');

function log(msg, level = 'INFO') {
  const colors = {
    INFO: '\x1b[36m',
    SUCCESS: '\x1b[32m',
    WARN: '\x1b[33m',
    ERROR: '\x1b[31m',
    RESET: '\x1b[0m'
  };
  console.log(`${colors[level] || ''}${msg}${colors.RESET}`);
}

function banner() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║       🔄 Sideria PM 迁移工具                                 ║');
  console.log('║          v1.x → v2.0 Universal                                ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');
}

function extractServicesFromOldPM() {
  // 尝试从旧版本的 sideria-pm.js 中提取服务配置
  // 这是一个简化版本，假设用户已经有模板文件
  
  if (!fs.existsSync(TEMPLATE_FILE)) {
    log('✗ 未找到模板文件 services.template.json', 'ERROR');
    log('请确保 services.template.json 存在', 'ERROR');
    return null;
  }
  
  try {
    const template = fs.readFileSync(TEMPLATE_FILE, 'utf-8');
    return JSON.parse(template);
  } catch (e) {
    log(`✗ 读取模板失败: ${e.message}`, 'ERROR');
    return null;
  }
}

async function main() {
  banner();
  
  log('此工具将帮助你从 Sideria PM v1.x 迁移到 v2.0', 'INFO');
  log('', 'INFO');
  
  // 检查是否已有配置文件
  if (fs.existsSync(CONFIG_FILE)) {
    log('⚠ 检测到已有配置文件 services.json', 'WARN');
    log('如果继续，将会覆盖现有配置', 'WARN');
    log('', 'INFO');
    
    const readline = require('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    const answer = await new Promise((resolve) => {
      rl.question('是否继续? (y/N): ', resolve);
    });
    rl.close();
    
    if (answer.toLowerCase() !== 'y') {
      log('迁移已取消', 'INFO');
      return;
    }
    
    // 备份现有配置
    const backup = `${CONFIG_FILE}.backup.${Date.now()}`;
    fs.copyFileSync(CONFIG_FILE, backup);
    log(`✓ 已备份现有配置到: ${backup}`, 'SUCCESS');
  }
  
  // 从模板生成配置
  log('', 'INFO');
  log('正在从模板生成配置...', 'INFO');
  
  const config = extractServicesFromOldPM();
  if (!config) {
    log('✗ 迁移失败', 'ERROR');
    return;
  }
  
  // 保存配置
  try {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8');
    log(`✓ 配置已生成: ${CONFIG_FILE}`, 'SUCCESS');
  } catch (e) {
    log(`✗ 保存配置失败: ${e.message}`, 'ERROR');
    return;
  }
  
  log('', 'INFO');
  log('━━━ 迁移完成 ━━━', 'SUCCESS');
  log('', 'INFO');
  log('下一步:', 'INFO');
  log('  1. 检查并编辑 services.json，确保路径正确', 'INFO');
  log('  2. 或运行配置向导重新配置: node sideria-pm.js setup', 'INFO');
  log('  3. 启动服务: node sideria-pm.js start', 'INFO');
  log('', 'INFO');
  log('💡 提示:', 'INFO');
  log('  - 模板中的路径可能需要根据你的实际环境调整', 'INFO');
  log('  - 可以禁用不需要的服务（设置 enabled: false）', 'INFO');
  log('  - 详细文档请查看 README.md', 'INFO');
  log('', 'INFO');
}

main().catch(err => {
  log(`✗ 迁移异常: ${err.message}`, 'ERROR');
  process.exit(1);
});
