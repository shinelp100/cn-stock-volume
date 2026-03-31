# Claude Code 源代码泄漏事件深度产研报告

> **报告时间：** 2026年4月1日  
> **研究框架：** Deep Research Framework（多源搜索 × 交叉验证 × 迭代分析）  
> **事件等级：** 高（产品级源码全量暴露）  
> **事件性质：** 意外泄漏（非攻击 / 非恶意）  
> **综合置信度：** 高（信息来源高度一致，多源交叉验证）

---

## 📋 Executive Summary

2026年3月31日，全球AI编程工具头部厂商 **Anthropic** 因其 npm 发布流程中的构建配置失误，意外将旗舰产品 **Claude Code v2.1.88** 的完整 TypeScript 源代码通过 source map 文件暴露于 npm registry，任何人下载该包即可还原全部原始代码。泄露规模达 **1,900 个文件、51.2 万行代码**，涵盖产品核心架构、40+ 内置工具、50+ 斜杠命令及大量**未发布实验性功能**。代码在数小时内被社区归档至 GitHub，引发全球开发者狂欢式分析。截至报告发出时，GitHub 镜像仓库已获约 **14,800 Stars、9,600 Forks**。Anthropic 随后紧急推送更新移除了 source map，但已泄露代码已永久留存于互联网。核心基座模型**未受影响**，用户数据安全。

> **⚠️ 特别说明：** 这是 2026 年 3 月以来 Anthropic 发生的**第二起**重大信息泄漏事件——3月27日才刚因 CMS 配置错误泄露了 Claude Mythos 模型信息（约 3,000 份未公开资产），管理漏洞值得高度关注。

---

## 1. 事件全貌

### 1.1 时间线

| 时间节点 | 事件 |
|---|---|
| **2026-03-31（北京时间）** | 区块链基础设施公司 Solayer 实习生 **Chaofan Shou**（FuzzLand）在检查 Claude Code npm 包时，发现 `cli.js.map` 包含完整的 `sourcesContent`，可直接还原 TypeScript 源码 |
| **2026-03-31 晚** | Chaofan Shou 在 X（原 Twitter）发帖披露，并附上 R2 存储桶的 `src.zip` 直链 |
| **2026-03-31 晚（数小时内）** | 热心网友将泄露代码归档至 GitHub（`sanbuphy/claude-code-source-code`），迅速传播 |
| **2026-03-31 深夜** | Anthropic 紧急推送 npm 更新，移除 source map 文件并删除早期版本包 |
| **2026-04-01** | GitHub 镜像持续传播，社区进入深度代码分析阶段 |

### 1.2 发现者背景

- **Chaofan Shou**：Web3 安全公司 **FuzzLand** 实习研究员 / 区块链基础设施公司 **Solayer** 实习生
- 发现方式：常规 npm 包安全审查（非针对性攻击）
- 发现过程：检查 npm 包内容 → 发现异常大的 `.map` 文件 → 发现内含完整源码 → 公开披露

### 1.3 技术根因

```
正常发布流程：
  源码 (.ts) → 构建压缩 (.js) + source map (.map) [仅开发用] → 发布 .js 至 npm [不含 .map]

此次错误流程：
  源码 (.ts) → 构建压缩 (.js) + source map (.map) → 错误地将 .map 也发布至 npm
```

Claude Code 的 npm 包（`@anthropic-ai/claude-code`）中包含一个 **59.8MB 的 `cli.js.map`** 文件，该文件不只是普通的符号映射（只映射行号和文件名），而是携带了完整的 **sourcesContent**（即原始 TypeScript 源码内容）。任何人都可以下载该 `.map` 文件，直接还原出 51.2 万行未混淆的原始代码。根本原因是 `.npmignore` 配置疏漏或构建工具（Webpack/Vite/esbuild）设置不当，未在生产构建阶段排除 source map。

---

## 2. 泄露内容全景解析

### 2.1 基本规模

| 指标 | 数值 |
|---|---|
| 泄露文件数 | 1,900 个 TypeScript 文件 |
| 代码总行数 | 512,000+ 行 |
| Source map 文件大小 | 59.8 MB（`cli.js.map`） |
| 内置工具数 | 40+ 个 |
| 斜杠命令数 | ~50 个 |
| 内部环境变量 | 120+ 个（未公开） |
| 编译时功能标志 | 35 个 |
| 内部 GitHub stars（截至报告时） | ~14,800 |
| Fork 数量 | ~9,600 |

### 2.2 核心架构曝光

泄露代码显示 Claude Code **远不止一个 API 封装层**，而是一套完整的生产级 AI Agent 系统：

| 核心模块 | 说明 |
|---|---|
| **QueryEngine.ts** | 核心推理引擎，约 46,000 行，负责思维链循环（Think-Act-Observe） |
| **权限控制工具** | 40+ 个权限管理工具，处理沙箱和操作限制 |
| **多智能体协调系统** | Coordinator + Bridge 模块，支持并行多代理工作 |
| **IDE 桥接功能** | 与 JetBrains、VS Code 等 IDE 的深度集成 |
| **持久化记忆机制** | 跨会话状态管理和上下文保持 |
| **UDS Inbox** | Unix Domain Socket  inbox，支持多 Claude 会话间互相通信 |
| **Daemon Mode** | 完整后台会话管理器（`claude ps/attach/kill` 等命令） |

### 2.3 未发布功能：重磅曝光

#### 🔮 KAIROS——永不下线的全能助手

这是此次泄露中最具战略价值的功能，被认为是 Anthropic 的"下一张王牌"。

- **定位：** 持久化常驻 AI 助手模式，对标《钢铁侠》中的"贾维斯"
- **功能特征：**
  - 7×24 小时持续监视、记录，主动对观察到的事物采取行动
  - 自定义系统提示词（custom system prompt）
  - 简化的"助手视图"（非程序员视角）
  - 定时检查、定时触发（scheduled check-in skills）
  - `claude assistant [sessionId]` 入口，可恢复并持续运行的会话
  - 支持 GitHub Webhooks 订阅（`KAIROS_GITHUB_WEBHOOKS`）
  - 支持 MCP（Model Context Protocol）channel notifications，可通过社交软件远程指挥
  - 支持 cron / scheduled tasks / remote control，形成完整的 agent 闭环
- **技术实现：** 维护每日追加日志文件，记录观察、决策和操作
- **现状：** 隐藏在 `PROACTIVE/KAIROS` 编译标志之后，外部构建版本**完全不可见**

> **产品影响分析：** Kairos 的架构设计揭示了 Anthropic 的战略方向——不只做"命令行编程助手"，而是打造一个接管整个操作系统入口的 AI Agent 系统。其工具编排、远程控制、定时触发的设计逻辑，将成为行业竞品的重要参考。

#### 🐾 BUDDY——终端电子宠物系统

一个完整的类 Tamagotchi（电子宠物）伴侣系统：

- **机制：** 确定性抽卡（random seed = `'friend-2026-401'`）
- **物种：** 18 种不同物种
- **稀有度系统：** 稀有度等级 + 闪光变种（Shiny Variants）
- **属性生成：** 程序化生成的属性统计
- **灵魂描述：** Claude 在首次"孵化"时撰写的"灵魂描述"
- **当前状态：** 代码完整但未对外发布

> **彩蛋线索：** 随机数种子包含 `401`，对应 4 月 1 日愚人节，代码标注"预告窗口"为 4 月 1-7 日，完整发布定在 2026 年 5 月——这暗示此次泄露可能是**愚人节营销**，但因规模过大，真实性存疑。

#### 💭 autoDream——学会"做梦"的 AI

后台记忆整合引擎，作为 fork 子代理运行：

- **功能：** 将近期学习内容整合为持久化、组织良好的记忆，使后续会话能快速定位上下文
- **触发机制（三重门控）：**
  1. 距上次"做梦" ≥ 24 小时
  2. 至少完成 5 次会话
  3. 获取整合锁（acquire consolidation lock）
- **本质：** 反思性记忆文件处理系统

#### 🌀 ULTRAPLAN——30 分钟云端深度规划

将复杂规划任务交给运行 Claude Opus 4.6 的远程云容器会话，给予最多 30 分钟的深度思考时间，用户在浏览器中批准结果后，通过 `__ULTRAPLAN_TELEPORT_LOCAL__` 标记将结果"传送"回本地终端。

#### 其他已泄露的内部功能

| 功能 | 说明 |
|---|---|
| `/teleport` | 远程传送文件/内容 |
| `/dream` | 触发记忆整合 |
| `/good-claude` | 内部测试命令 |
| `Coordinator Mode` | 多代理并行协调 |
| `Bridge Mode` | 通过 claude.ai 或手机远程控制本地 CLI |
| `Undercover Mode` | 防止 Anthropic 员工在开源仓库贡献时泄露内部信息 |

#### 🕵️ Undercover Mode（卧底模式）——最大讽刺

代码中专门设计了"卧底模式"，用于防止 Anthropic 员工在公开仓库提交代码时泄露内部信息。该模式激活时会注入系统提示，**明确禁止**在 commit 消息或 PR 描述中出现：

- 内部模型代号（Capybara、Tengu 等动物名）
- 未发布的模型版本号
- 内部工具名
- Slack 频道名
- "Claude Code"字样
- 甚至禁止**声称自己是 AI**

讽刺的是，Anthropic 的 source map 自己先泄露了——卧底模式的代码和盘托出，Undercover Mode 成了最大的"笑话"。

---

## 3. 社区反应与影响

### 3.1 GitHub 传播数据（截至2026-04-01）

| 指标 | 数值 |
|---|---|
| 镜像仓库 Stars | ~14,800（持续增长中） |
| Forks | ~9,600 |
| 相关仓库数 | 多个（中文学习版、社区分析版等） |

### 3.2 开发者社区分析

社区对泄露代码的初步分析结论高度一致：

> *"这应该是 Claude Code 官方不小心把 v2.1.88 的源码直接传到了 npm 包里，整体代码结构很成熟，整个 repo 分得很细。主流程包括 REPL 启动、QueryEngine、工具注册、Slash 命令、权限系统、任务系统，以及多层状态管理——非常典型的生产级 AI Agent Harness 设计。"*

开发者社区已开始从以下角度深度分析：
1. **工具系统设计**：40+ 工具的权限和注册机制
2. **多智能体架构**：Coordinator + Bridge 的协作模式
3. **记忆机制**：autoDream 和持久化状态管理
4. **安全模型**：Undercover Mode 和权限控制设计
5. **产品路线**：Kairos 等未发布功能透露的产品方向

### 3.3 竞品影响分析

泄露的架构设计不会直接被复制为竞品（模型能力是核心护城河），但以下影响是实质性的：

| 影响维度 | 具体表现 |
|---|---|
| **技术透明度提升** | 外界可清晰看到 Claude Code 的工具设计、权限模型、遥测埋点 |
| **竞争加速** | 竞品可更快理解 Claude Code 的能力边界，针对性优化 |
| **安全研究** | 安全社区可深度审计 Claude Code 的权限模型和沙箱机制 |
| **Agent 框架** | Kairos 的架构设计为整个 Agent 开发领域提供了参考蓝本 |
| **用户信任** | 企业客户可能重新评估对 Anthropic 产品安全性的信任度 |

---

## 4. Anthropic 的安全履历审视

### 4.1 2026年3月：Anthropic 的"黑色三月"

| 日期 | 事件 | 泄露内容 |
|---|---|---|
| **2026-03-26** | CMS 配置错误（首次） | Claude Mythos 模型信息 + ~3,000 份未公开资产 |
| **2026-03-31** | npm source map 泄漏（本次） | Claude Code 完整客户端源码 51.2 万行 |

**五天内两起重大泄漏**，暴露的不是技术边界的失误，而是**发布流程管理的基础卫生问题**。

### 4.2 历史安全事件

| 时间 | 事件 | 教训 |
|---|---|---|
| 2025年2月 | 早期版本 Claude Code 同样因 source map 问题泄露源码 | Anthropic 当时已修复，但未建立长效机制 |
| 2025年12月 | Claude Code 系统提示词被完整泄露 | 配置管理问题 |
| 2026年3月 | Claude Mythos 模型信息泄露 | CMS/资产配置问题 |
| 2026年3月31日 | Claude Code 源码再次因同样根因泄露（v2.1.88） | 复发，同一漏洞未彻底修复 |

> **核心问题：** Anthropic 在 2025年2月已遭遇过一次 source map 泄露，并进行了修复。但**构建流程未建立持续验证机制**，导致时隔一年后，同一类型的错误在更高版本上重现。这说明问题不在于"不知道有这个风险"，而在于**发布前的自动化检查机制缺失**。

### 4.3 企业客户的信任冲击

对于正在推广 Claude Code 企业版的 Anthropic 而言，这次泄露的深层影响在于**形象伤害**：

> *"你连核心客户端的 source map 都能带着源码一起发出去，那你内部的 release review、artifact audit、supply chain hygiene（供应链卫生）到底做得怎么样？"*
> *—— 凤凰网科技频道分析*

Anthropic 正在洽谈 IPO（2026年预期上市），**管理成熟度**和**流程控制能力**是资本市场的核心关注点。连续两起泄露事件将对估值产生负面影响。

---

## 5. 竞品对比：横向泄漏事件参照

| 事件 | 公司 | 泄露规模 | 根因 | 处置 |
|---|---|---|---|---|
| Claude Code 源码泄漏（2026-03-31） | Anthropic | 51.2万行，1,900文件 | npm source map | 已移除，但代码永久留存 |
| Axios npm 被植入RAT木马（2026-03-31） | Axios | 包被恶意篡改 | npm 账户被入侵 | 包已下架（8,300万次/周下载） |
| 2025年 Claude Code source map 泄露 | Anthropic | 早期版本源码 | 同上 | 已修复但未建立长效机制 |
| Cursor IDE 源码疑似泄露（2024年） | Anthropic/Cursor | 部分内部版本 | 未确认 | 未证实 |

> **行业警示：** 同日发生的 Axios npm 被植入木马事件，证明了 npm 供应链安全的脆弱性——无论是**恶意攻击**（Axios）还是**无意泄漏**（Claude Code），供应链发布环节的一个小失误都可能造成灾难性后果。

---

## 6. 技术架构亮点（产研价值分析）

从代码工程角度，Claude Code 的架构有以下几个值得关注的亮点：

### 6.1 QueryEngine：46,000 行的推理心脏

单文件 46,000 行代码，专门负责推理逻辑与思维链循环（Think-Act-Observe），这是 Claude Code "聪明"的核心所在。外部可看到其 prompt 设计、token 预算管理、工具调用策略等关键实现细节。

### 6.2 多层权限工具系统

40+ 独立权限控制工具，构成了 Claude Code 操作文件、执行命令时的"安全边界"。这意味着 Claude Code 的沙箱设计是**工具级**而非进程级的，其权限模型比外界预期的更精细。

### 6.3 UDS Inbox：会话间通信协议

通过 Unix Domain Socket 实现的进程间通信，让多个 Claude Code 会话可以互相通信。这一设计支持了复杂的多会话协调场景，也为远程控制（Bride Mode）提供了基础设施。

### 6.4 Coordinator + Bridge 双模块设计

- **Coordinator Mode**：并行生成和管理多个工作代理，类似 Agent 路由
- **Bridge Mode**：通过云端（claude.ai 或手机 App）远程控制本地 CLI

这两者的组合让 Claude Code 具备了**本地算力 + 云端协调**的混合架构能力。

---

## 7. 安全风险评估

### 7.1 对普通用户：无直接风险
泄露的是 CLI 客户端实现代码，不涉及：
- ✅ 用户 API Key
- ✅ 用户对话数据
- ✅ 云端推理服务
- ✅ 核心基座模型

### 7.2 对 Anthropic：中等偏高风险

| 风险维度 | 评级 | 说明 |
|---|---|---|
| 商业机密 | ⚠️ 中 | 未发布功能路线提前曝光，产品差异化缩小 |
| 竞争护城河 | ⚠️ 中 | 架构设计被复制，但模型能力不可复制 |
| 用户信任 | ⚠️ 中高 | 企业客户可能重新评估安全资质 |
| 监管合规 | ⚠️ 低 | 基座模型未泄露，监管影响有限 |
| 资本市场 | 🔴 高 | IPO 筹备期，管理成熟度遭质疑 |
| 品牌声誉 | ⚠️ 中 | 连续泄漏事件影响专业形象 |

### 7.3 对整个行业：正面推动

尽管对 Anthropic 是负面事件，但从整个 AI Agent 赛道看，Claude Code 的架构设计（特别是 Kairos 的 agent 闭环设计）将为行业提供重要的工程参考，可能**加速整个 Agent 生态的技术迭代**。

---

## 8. Anthropic 应采取的修复措施

### 8.1 紧急修复（已完成）
- [x] 从 npm registry 移除 source map 文件
- [x] 删除早期受影响版本

### 8.2 短期（1-2周）
- [ ] 对所有 npm 包发布建立**自动化 pre-publish 检查**，确保 `.map` 文件不进入产物
- [ ] 在 CI/CD 流程中强制加入 `npm pack --dry-run` 或 `npm publish --dry-run` 审计
- [ ] 建立 npm 包内容签名/校验机制
- [ ] 审查所有历史发布版本，确认无其他配置问题

### 8.3 中期（1-3个月）
- [ ] 建立 **SBOM（软件物料清单）**，每次发布自动生成并审查
- [ ] 引入供应链安全扫描工具（如 Socket.dev、Synk）
- [ ] 对第三方依赖（npm 包）建立白名单机制
- [ ] 加强源码分级管理，核心 AI 逻辑与产品胶水代码分离发布
- [ ] 建立**持续性安全披露机制**（类似 Bug Bounty），激励外部发现而非公开传播

### 8.4 长期
- [ ] 考虑将 CLI 核心代码逐步**正式开源**（类似 HashiCorp 模式），化被动为主动
- [ ] 对内建立强制性的**发布安全审计（Release Security Review）**流程
- [ ] 考虑引入第三方代码托管审计机构

---

## 9. 对 AI 编程工具行业的启示

### 9.1 npm/JavaScript 生态的安全脆弱性

npm 是全球最大的代码生态，但发布流程缺乏强制安全门控：
- 没有强制要求排除 source map 的机制
- 包签名机制（npm provenance）虽已引入但未普及
- 恶意包（typosquatting、dependency confusion）和无意泄漏并存

### 9.2 AI Agent 系统的设计启示

Claude Code 源码泄露揭示了当前头部 AI Agent 的工程实践：
- **持久化记忆** = 定期整合而非实时写入（autoDream 机制）
- **多代理协作** = Coordinator 模式可能是主流
- **远程控制** = Bridge Mode 让 AI 不受本地终端限制
- **主动助手** = Kairos 展示了"永远在线 Agent"的实现路径

### 9.3 "透明化竞争"时代的来临

Claude Code 的泄露不是个案。AI 编程工具正进入"透明化竞争"阶段——当所有主流产品的客户端架构都被社区充分理解后，竞争的核心将**完全转移到模型能力、推理成本和云端基础设施**，而非客户端功能设计的差异化。

---

## 10. 未解疑问与后续关注

| 疑问 | 说明 |
|---|---|
| Anthropic 是否有官方声明？ | 截至报告发出时（2026-04-01），Anthropic **尚未公开发表任何官方声明** |
| 这是愚人节营销吗？ | 代码中的彩蛋（`friend-2026-401`、4月1-7日预告窗口）暗示可能是有意为之，但规模过大，可信度存疑 |
| Kairos 何时正式发布？ | 代码标注2026年5月完整发布，但事件可能改变发布时间表 |
| Undercover Mode 会被删除吗？ | 鉴于已被完全曝光，Anthropic 可能重新设计或删除该功能 |
| 是否会影响 Anthropic 的 IPO 进程？ | 需持续跟踪其资本市场动态 |

---

## 参考来源

1. **新浪财经** — Claude Code源代码意外泄露：512K行代码曝光（2026-03-31）  
   https://finance.sina.com.cn/tech/roll/2026-03-31/doc-inhswxzn3168987.shtml

2. **腾讯网/DeepTech深科技** — Claude Code源代码意外泄露（2026-03-31）  
   https://new.qq.com/rain/a/20260331A07XSW00

3. **凤凰网科技** — Claude Code源码泄露，下一个王牌提前曝光（2026-03-31）  
   https://tech.ifeng.com/c/8rwt9tZUW47

4. **凤凰网科技** — 突发！Claude Code"开源"，全网疯传（2026-03-31）  
   https://tech.ifeng.com/c/8rx24JeNn0t

5. **经济观察网** — 源码遭泄露，硅谷头部模型Anthropic"被动开源"了（2026-03-31）  
   http://www.eeo.com.cn/2026/0331/824113.shtml

6. **亿欧快讯** — 突发：Claude Code源代码遭泄露，51万行核心代码及未发布功能曝光（2026-03-31）  
   https://www.iyiou.com/briefing/202603311893739

7. **网易新闻** — Claude Code翻车！源代码直接"裸奔"，AI开发者能"偷师"到哪些神级产品构架？（2026-03-31）  
   https://c.m.163.com/news/a/KPCQ2PG500097U7T.html

8. **搜狐/新智元** — 刚刚，Claude Code开源了！51万行代码，全网狂欢（2026-03-31）  
   https://www.sohu.com/a/1003574599_473283

9. **金十数据** — Claude Code完整源代码疑似因npm配置失误遭泄露（2026-03-31）  
   https://flash.jin10.com/detail/20260331194021815800

10. **ZAKER** — Claude Code源码泄露，下一个王牌提前曝光（2026-03-31）  
    https://www.myzaker.com/article/69cbc1ce8e9f0933c52a2ea1

11. **GitHub 镜像仓库** — sanbuphy/claude-code-source-code  
    https://github.com/sanbuphy/claude-code-source-code

12. **X (Twitter)** — Chaofan Shou (@sanbuphy) 原始披露帖（2026-03-31）  
    https://x.com/sanbuphy/status/2038912992457408838

---

*本报告基于 2026年3月31日—4月1日公开信息综合整理，数据来源于多个独立中文媒体源，事件真实性高度可信。Anthropic 官方截至报告发出时尚未发布声明，部分技术细节基于社区分析，可能存在偏差，仅供参考。*

---

**报告生成时间：** 2026-04-01 00:20 GMT+8  
**研究框架：** Deep Research Framework v1.0  
**分析师：** QClaw AI（自动化深度研究）
