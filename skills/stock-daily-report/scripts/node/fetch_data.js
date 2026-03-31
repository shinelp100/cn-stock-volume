#!/usr/bin/env node
/**
 * fetch_data.js - 数据获取入口
 * 整合所有数据源，返回 JSON 格式的完整数据
 */

const path = require('path');

// 添加 scripts 目录到路径
const scriptDir = path.dirname(__dirname);
const nodeDir = path.join(scriptDir, 'node');

// 确保可以找到 browser_client
let browserClient;
try {
  browserClient = require(nodeDir + '/browser_client.js');
} catch (e) {
  console.error('无法加载 browser_client:', e.message);
  process.exit(1);
}

/**
 * 获取完整数据
 */
async function getFullData() {
  const data = {
    timestamp: new Date().toISOString(),
    sentiment: null,
    gainers: null,
    topics: []
  };
  
  try {
    // 获取浏览器数据
    console.error('获取浏览器数据...');
    const browserData = await browserClient.fetchAllBrowserData();
    data.sentiment = browserData.sentiment;
    data.gainers = browserData.gainers;
  } catch (e) {
    console.error('浏览器数据获取失败:', e.message);
  }
  
  return data;
}

// 解析命令行参数
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
Usage: node fetch_data.js [options]

Options:
  --sentiment    Only fetch sentiment data
  --gainers      Only fetch gainers data
  --all          Fetch all data (default)
  --help, -h     Show this help

Output: JSON format
  `);
  process.exit(0);
}

// 根据参数决定获取什么数据
if (args.includes('--sentiment')) {
  browserClient.fetchSentimentData()
    .then(data => console.log(JSON.stringify(data, null, 2)))
    .catch(err => { console.error(err.message); process.exit(1); });
} else if (args.includes('--gainers')) {
  browserClient.fetchTopGainers()
    .then(data => console.log(JSON.stringify(data, null, 2)))
    .catch(err => { console.error(err.message); process.exit(1); });
} else {
  // 默认获取全部数据
  getFullData()
    .then(data => console.log(JSON.stringify(data, null, 2)))
    .catch(err => { console.error(err.message); process.exit(1); });
}
