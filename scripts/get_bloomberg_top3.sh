#!/bin/bash
#===============================================
# get_bloomberg_top3.sh
# 获取 Bloomberg 热度最高的 3 篇文章
#
# ⚠️ 依赖说明:
#   - opencli bloomberg (必装): 获取文章标题和摘要
#   - Browser Bridge 扩展 (可选): 获取完整文章内容
#
# 安装 Browser Bridge:
#   1. 下载: github.com/jackwener/opencli/releases
#   2. 打开 chrome://extensions
#   3. 启用开发者模式
#   4. 加载解压的扩展
#===============================================

python3 << 'EOF'
import json
import subprocess
import os
from datetime import datetime

# 颜色定义
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
NC = '\033[0m'

# 输出目录
output_dir = os.path.expanduser("~/bloomberg_top3")
os.makedirs(output_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report_file = os.path.join(output_dir, f"bloomberg_report_{timestamp}.md")

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.returncode

def get_article_content(link):
    """获取文章内容，需要 Browser Bridge 扩展"""
    output, code = run_cmd(["opencli", "bloomberg", "news", link])
    if code != 0:
        return None
    return output if output.strip() else None

print(f"{BLUE}{'='*60}{NC}")
print(f"{BLUE}  Bloomberg 热度 Top 3 文章获取工具{NC}")
print(f"{BLUE}{'='*60}{NC}")
print()

# Step 1: 获取主页热度榜单
print(f"{YELLOW}📡 Step 1: 获取 Bloomberg 主页热度榜单...{NC}")

json_output, code = run_cmd(["opencli", "bloomberg", "main", "--limit", "10", "--format", "json"])
if code != 0:
    print(f"{RED}❌ 获取失败: {json_output}{NC}")
    exit(1)

articles = json.loads(json_output)
top3 = articles[:3]

# 创建报告
with open(report_file, "w", encoding="utf-8") as f:
    f.write(f"# Bloomberg 热度 Top 3 报告\n\n")
    f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"> 数据来源: Bloomberg 首页 RSS\n\n")
    f.write("---\n\n")
    f.write("## 📊 热度排行榜\n\n")
    f.write("| 排名 | 标题 | 摘要 |\n")
    f.write("|------|------|------|\n")

print(f"\n{GREEN}📰 获取到 {len(top3)} 篇热门文章：{NC}\n")

for i, article in enumerate(top3, 1):
    title = article['title']
    link = article['link']
    summary = article['summary'][:100] + "..." if len(article['summary']) > 100 else article['summary']
    
    print(f"{YELLOW}{'─'*60}{NC}")
    print(f"{GREEN}【第 {i} 名】{NC}")
    print(f"{BLUE}📌 标题: {title}{NC}")
    print(f"🔗 链接: {link}")
    print(f"📝 摘要: {summary}")
    print()
    
    # 写入报告
    with open(report_file, "a", encoding="utf-8") as f:
        f.write(f"| {i} | {title} | {summary} |\n")

with open(report_file, "a", encoding="utf-8") as f:
    f.write("\n---\n\n")

# Step 2: 尝试获取全文（需要 Browser Bridge）
print(f"{YELLOW}📰 Step 2: 尝试获取文章全文...{NC}\n")

browser_bridge_ok = True
for i, article in enumerate(top3, 1):
    title = article['title']
    link = article['link']
    
    content = get_article_content(link)
    
    with open(report_file, "a", encoding="utf-8") as f:
        f.write(f"## 【第 {i} 名】{title}\n\n")
        f.write(f"**链接**: {link}\n\n")
        
        if content:
            f.write(f"**内容**:\n\n{content}\n\n")
            print(f"{GREEN}✅ 第 {i} 篇全文获取成功 ({len(content)} 字符){NC}")
        else:
            if browser_bridge_ok:
                print(f"{YELLOW}⚠️ 第 {i} 篇全文获取失败（需要 Browser Bridge 扩展）{NC}")
                browser_bridge_ok = False
            else:
                print(f"{RED}❌ 第 {i} 篇全文获取失败{NC}")
            f.write("**内容**: （需要安装 Browser Bridge 扩展获取全文）\n\n")
    
    print()

# 完成
print(f"{GREEN}{'='*60}{NC}")
print(f"{GREEN}  ✅ 完成！{NC}")
print(f"{GREEN}{'='*60}{NC}")
print()
print(f"{GREEN}📁 报告已保存至:{NC}")
print(f"{CYAN}   {report_file}{NC}")
print()

# Browser Bridge 提示
if not browser_bridge_ok:
    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}  💡 提示：获取全文需要安装 Browser Bridge 扩展{NC}")
    print(f"{YELLOW}{'='*60}{NC}")
    print()
    print(f"  安装步骤:")
    print(f"  1. 下载: {CYAN}github.com/jackwener/opencli/releases{NC}")
    print(f"  2. 打开: {CYAN}chrome://extensions{NC}")
    print(f"  3. 启用开发者模式")
    print(f"  4. 加载解压的扩展")
    print()

# 使用说明
print(f"{BLUE}{'='*60}{NC}")
print(f"{BLUE}  使用方法{NC}")
print(f"{BLUE}{'='*60}{NC}")
print()
print(f"  {GREEN}./get_bloomberg_top3.sh{NC}                  # 运行脚本")
print(f"  opencli bloomberg main --limit 3 --format json  # 获取 Top 3 JSON")
print(f"  opencli bloomberg main --limit 3 --format md    # 获取 Top 3 Markdown")
print(f"  opencli bloomberg main --limit 3 --format table # 获取 Top 3 表格")
print()

EOF
