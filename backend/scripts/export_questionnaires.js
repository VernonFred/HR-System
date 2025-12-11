/**
 * 将现有 questionnaires.js 转为 JSON 输出（stdout）。
 * 依赖：Node.js，可用作 Python 种子脚本的数据源。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const jsPath = path.resolve(__dirname, '../../questionnaires.js');
const content = fs.readFileSync(jsPath, 'utf8');

const sandbox = { console, globalThis: {} };
vm.createContext(sandbox);

// 把 QUESTIONNAIRE_DATA 挂到 globalThis 便于读取
vm.runInContext(`${content}\n;globalThis.__QL_DATA = QUESTIONNAIRE_DATA;`, sandbox);

const data = sandbox.globalThis.__QL_DATA;
if (!data) {
  throw new Error('QUESTIONNAIRE_DATA not found after evaluating questionnaires.js');
}

// 输出 JSON（缩进 2 便于调试；管道消费可用 --compact）
const compact = process.argv.includes('--compact');
const json = JSON.stringify(data, null, compact ? 0 : 2);
process.stdout.write(json);
