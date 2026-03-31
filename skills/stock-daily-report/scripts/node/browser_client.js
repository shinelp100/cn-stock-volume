#!/usr/bin/env node
/**
 * browser_client.js - 浏览器自动化客户端
 * 使用 Playwright 获取股票数据
 * 支持同花顺问财和东方财富
 */

const { chromium } = require('playwright');

// 同花顺问财
const WENCAI_BASE_URL = 'https://www.iwencai.com/unifiedwap/result';
// 东方财富
const EASTMONEY_URL = 'https://quote.eastmoney.com/center/gridlist.html#concept_board';

/**
 * 获取涨跌家数数据（尝试多个数据源）
 */
async function fetchSentimentData() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // 方式1: 尝试同花顺
    console.error('正在获取涨跌家数数据（方式1: 同花顺）...');
    try {
      const url = `${WENCAI_BASE_URL}?w=${encodeURIComponent('涨跌家数')}&querytype=stock`;
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
      
      const content = await page.textContent('body');
      
      // 检查是否有数据
      if (content && content.length > 100 && !content.includes('请登录')) {
        const result = parseSentimentFromContent(content);
        if (result.up > 0 || result.down > 0) {
          await browser.close();
          return result;
        }
      }
    } catch (e) {
      console.error('同花顺获取失败:', e.message);
    }
    
    // 方式2: 尝试东方财富实时数据
    console.error('正在获取涨跌家数数据（方式2: 东方财富）...');
    try {
      await page.goto('https://quote.eastmoney.com/center/gridlist.html#hs_a_board', 
                     { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);
      
      const content = await page.textContent('body');
      const result = parseSentimentFromEastMoney(content);
      
      if (result.up > 0 || result.down > 0) {
        await browser.close();
        return result;
      }
    } catch (e) {
      console.error('东方财富获取失败:', e.message);
    }
    
    await browser.close();
    return { up: 0, down: 0, ratio_str: '（数据获取失败）' };
  } catch (error) {
    console.error('获取涨跌家数最终失败:', error.message);
    if (browser) {
      try { await browser.close(); } catch (e) {}
    }
    return { up: 0, down: 0, ratio_str: '（数据获取失败）' };
  }
}

/**
 * 从东方财富页面解析涨跌家数
 */
function parseSentimentFromEastMoney(content) {
  // 东方财富页面可能有不同格式
  const upMatch = content.match(/上涨[:\s]*(\d+)/i) || content.match(/涨\s*(\d+)家/);
  const downMatch = content.match(/下跌[:\s]*(\d+)/i) || content.match(/跌\s*(\d+)家/);
  
  const up = upMatch ? parseInt(upMatch[1]) : 0;
  const down = downMatch ? parseInt(downMatch[1]) : 0;
  
  let ratio_str = '（数据获取中）';
  if (up > 0 && down > 0) {
    ratio_str = `${up}(涨) : ${down}(跌) ≈ 1 : ${(down / up).toFixed(1)}`;
  }
  
  return { up, down, limit_up: 0, limit_down: 0, ratio_str };
}

/**
 * 从页面内容解析涨跌家数
 */
function parseSentimentFromContent(content) {
  // 尝试匹配各种可能的格式
  const upMatch = content.match(/上涨[:\s]*(\d+)/i) || content.match(/涨\s*(\d+)/);
  const downMatch = content.match(/下跌[:\s]*(\d+)/i) || content.match(/跌\s*(\d+)/);
  const limitUpMatch = content.match(/涨停[:\s]*(\d+)/i);
  const limitDownMatch = content.match(/跌停[:\s]*(\d+)/i);
  
  const up = upMatch ? parseInt(upMatch[1]) : 0;
  const down = downMatch ? parseInt(downMatch[1]) : 0;
  const limit_up = limitUpMatch ? parseInt(limitUpMatch[1]) : 0;
  const limit_down = limitDownMatch ? parseInt(limitDownMatch[1]) : 0;
  
  let ratio_str = '（数据获取中）';
  if (up > 0 && down > 0) {
    ratio_str = `${up}(涨) : ${down}(跌) ≈ 1 : ${(down / up).toFixed(1)}`;
  }
  
  return {
    up,
    down,
    limit_up,
    limit_down,
    ratio_str
  };
}

/**
 * 获取近10日涨幅榜
 */
async function fetchTopGainers() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // 尝试多个查询词
    const queries = ['近10日涨幅排名', '10日涨幅排行', '近10日涨幅'];
    
    for (const query of queries) {
      console.error(`正在获取涨幅榜: ${query}...`);
      try {
        const url = `${WENCAI_BASE_URL}?w=${encodeURIComponent(query)}&querytype=stock`;
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(2500);
        
        const content = await page.textContent('body');
        
        // 检查是否有数据
        if (content && content.length > 500 && !content.includes('请登录') && !content.includes('验证')) {
          const result = parseGainersFromContent(content);
          if (result.stocks && result.stocks.length > 0) {
            await browser.close();
            return result;
          }
        }
      } catch (e) {
        console.error(`查询 ${query} 失败:`, e.message);
      }
    }
    
    await browser.close();
    return { stocks: [], main_board: null, gem_board: null, high_stocks: [] };
  } catch (error) {
    console.error('获取涨幅榜最终失败:', error.message);
    if (browser) {
      try { await browser.close(); } catch (e) {}
    }
    return { stocks: [], main_board: null, gem_board: null, high_stocks: [] };
  }
}

/**
 * 从页面内容解析涨幅榜
 */
function parseGainersFromContent(content) {
  const stocks = [];
  
  // 尝试匹配股票数据行
  // 格式可能多种多样，尝试多种模式
  const lines = content.split('\n');
  
  let rank = 0;
  const codePattern = /(\d{6})/;
  const namePattern = /[\u4e00-\u9fa5]{2,6}/;
  const pricePattern = /(\d+\.?\d*)/;
  const pctPattern = /(\d+\.?\d*)%/;
  
  for (const line of lines) {
    if (rank >= 20) break;
    
    const codeMatch = line.match(codePattern);
    if (!codeMatch) continue;
    
    const code = codeMatch[1];
    
    // 提取股价和涨幅
    const prices = line.match(pricePattern);
    const pcts = line.match(pctPattern);
    
    if (!prices || !pcts) continue;
    
    const price = parseFloat(prices[1]);
    const period_chg = parseFloat(pcts[1]);
    
    // 尝试提取股票名称
    const names = line.match(namePattern);
    const name = names ? names[0] : code;
    
    // 判断所属板块
    let board = 'other';
    if (code.startsWith('600') || code.startsWith('601') || code.startsWith('603')) {
      board = 'main';
    } else if (code.startsWith('300')) {
      board = 'gem';
    } else if (code.startsWith('000') || code.startsWith('001')) {
      board = 'main';
    }
    
    rank++;
    stocks.push({
      rank,
      code,
      name,
      price,
      period_chg,
      today_chg: 0,  // 简化处理
      board
    });
  }
  
  // 提取主板/创业板冠军
  let main_board = null;
  let gem_board = null;
  let high_stocks = [];
  
  for (const stock of stocks) {
    if (!main_board && stock.board === 'main') {
      main_board = stock;
    }
    if (!gem_board && stock.board === 'gem') {
      gem_board = stock;
    }
    if (stock.period_chg > 50) {
      high_stocks.push(stock);
    }
  }
  
  return {
    stocks,
    main_board,
    gem_board,
    high_stocks: high_stocks.slice(0, 5)
  };
}

/**
 * 主函数：获取所有浏览器数据
 */
async function fetchAllBrowserData() {
  console.error('开始浏览器自动化数据获取...');
  
  const sentiment = await fetchSentimentData();
  const gainers = await fetchTopGainers();
  
  return {
    sentiment,
    gainers
  };
}

// 导出模块
module.exports = {
  fetchSentimentData,
  fetchTopGainers,
  fetchAllBrowserData
};

// 如果直接运行
if (require.main === module) {
  fetchAllBrowserData()
    .then(data => {
      console.log(JSON.stringify(data, null, 2));
    })
    .catch(err => {
      console.error('Error:', err.message);
      process.exit(1);
    });
}
