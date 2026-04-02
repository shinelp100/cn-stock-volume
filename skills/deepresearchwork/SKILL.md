---
name: deep-research
description: Comprehensive research framework that combines web search, content analysis, source verification, and iterative investigation to conduct in-depth research on any topic. Use when you need to perform thorough research with multiple sources, cross-validation, and structured findings.
---

# Deep Research Framework

## Overview

The Deep Research skill provides a systematic approach to conducting thorough investigations on any topic. It combines multiple tools and methodologies to gather, analyze, verify, and synthesize information.

## Core Components

### 1. Research Planning
- Define research objectives
- Identify key questions
- Establish search criteria
- Determine validation requirements

### 2. Information Gathering
- Multi-source web search
- Content extraction from various formats
- Source diversity verification
- Temporal relevance assessment

### 3. Analysis & Synthesis
- Cross-reference multiple sources
- Identify patterns and contradictions
- Evaluate source credibility
- Organize findings systematically

### 4. Validation & Verification
- Fact-checking against authoritative sources
- Cross-validation of claims
- Identify potential biases
- Assess information reliability

## Research Workflow

### Phase 1: Initial Investigation
1. **Topic Analysis**
   - Clarify research scope
   - Identify key concepts and terms
   - Define specific questions to answer

2. **Broad Search**
   - Use `web_search` to identify major sources
   - Gather diverse perspectives
   - Map the landscape of available information

3. **Source Prioritization**
   - Rank sources by authority and relevance
   - Identify primary vs. secondary sources
   - Note publication dates and context

### Phase 2: Deep Dive
1. **Detailed Content Extraction**
   - Use `web_fetch` to retrieve full articles/pages
   - Extract key information systematically
   - Maintain source attribution

2. **Cross-Reference Analysis**
   - Compare claims across multiple sources
   - Identify agreements and disagreements
   - Note inconsistencies for further investigation

3. **Expert Sources**
   - Seek academic papers, expert opinions
   - Look for peer-reviewed sources
   - Identify recognized authorities on the topic

### Phase 3: Synthesis & Validation
1. **Pattern Recognition**
   - Identify consistent themes across sources
   - Highlight areas of disagreement
   - Note gaps in available information

2. **Fact Verification**
   - Cross-check claims against authoritative sources
   - Verify dates, statistics, and attributions
   - Identify potential misinformation

3. **Bias Assessment**
   - Evaluate source objectivity
   - Identify potential conflicts of interest
   - Consider temporal context of information

### Phase 4: Report Generation — ⚠️ MANDATORY VISUALIZATION STEP
> **⚠️ CRITICAL — ASCII diagrams MUST be converted to Mermaid before final output**
> This step is mandatory for ALL deep research reports. Do not skip.

When the research involves any of the following, you **MUST** invoke the `mermaid-diagrams` skill and convert ASCII/text diagrams into proper Mermaid syntax:
- 📊 **Architecture diagrams** (公司架构、业务结构、股权结构)
- 🔄 **Process flows** (业务流程、重整理赔流程、重组时间线)
- 🏢 **Organizational charts** (股权结构图、集团子公司关系图)
- 📈 **Market comparison tables** (竞争格局矩阵)
- 🔗 **Relationship diagrams** (供应链关系、上下游关系、概念股图谱)
- 📋 **Timeline diagrams** (发展历程、重大事件时间轴)

**Conversion rules (ASCII → Mermaid):**

| ASCII 类型 | Mermaid 类型 | 理由 |
|-----------|-------------|------|
| 树状/层级文本图 | `flowchart TD/LR` | 展示层级关系和决策路径 |
| 股权结构文字 | `flowchart TB` + 子图 `subgraph` | 清晰展示控制链 |
| 业务流程步骤 | `flowchart LR` + 决策节点 | 展示流程与分支 |
| 公司沿革时间线 | `flowchart LR` 或 `gantt` | 展示时间序列 |
| 竞争格局对比 | `quadrantChart` 或表格 | 不适合 Mermaid → 保留 Markdown 表格 |
| 架构分层图 | `C4` diagram 或 `flowchart` | 系统/业务架构 |

**⚠️ 关键约束（Mermaid 图表规则）：**
1. 节点数 ≤ 15 个（超出则拆分为多个图）
2. 每条连线必须有文字标签
3. 必须有标题/图注
4. 禁止用 Mermaid 画数据图表（柱状图/折线图等）
5. 产出为 `.mmd` 文件或嵌入 Markdown 的 Mermaid 代码块

**Step-by-step conversion workflow:**

```
Step 1: 识别报告中的 ASCII 图/文字架构图
         ↓
Step 2: 判断最适合的 Mermaid 类型 (flowchart / C4 / gantt / etc.)
         ↓
Step 3: 读取 mermaid-diagrams skill 获取该类型的标准语法
         ↓
Step 4: 逐节点转换（节点 label 保持中文，≤ 40字符）
         ↓
Step 5: 验证 Mermaid 语法（无断行语法错误）
         ↓
Step 6: 嵌入 Markdown 报告（或输出独立 .mmd 文件）
```

**Phase 4 完整输出清单：**
1. ✅ Executive Summary（执行摘要，2-3句）
2. ✅ Mermaid 可视化图表（所有 ASCII 架构图已转换）
3. ✅ Structured findings（按主题组织）
4. ✅ Source evaluation（来源可信度评估）
5. ✅ Limitations（研究局限性）
6. ✅ Remaining questions（待深入研究的问题）

#### 1. Structured Summary
   - Executive summary of key findings
   - Detailed findings organized by theme
   - Supporting evidence for each claim

#### 2. Mermaid Visualization (MANDATORY)
   - Convert ALL ASCII/text architecture diagrams to Mermaid
   - Include at minimum: corporate structure, business overview, key timelines
   - Use appropriate diagram type per content (see conversion table above)

#### 3. Source Evaluation
   - Assessment of source credibility
   - Identification of limitations
   - Confidence levels for different claims

#### 4. Remaining Questions
   - Areas requiring further investigation
   - Conflicting information needing resolution
   - Gaps in current knowledge

## Tools Integration

### Web Research
- `web_search`: Initial broad search to identify sources
- `web_fetch`: Retrieve detailed content from specific URLs
- `browser`: For complex sites or when web_fetch fails

### Content Processing
- `read`: Process downloaded content or documents
- `write`: Create structured research notes
- `edit`: Refine and organize findings

### Mermaid Visualization (MANDATORY — Phase 4)
> **⚠️ Use `mermaid-diagrams` skill for ALL diagram generation.**
> ASCII diagrams in reports are a quality failure. Every architecture,
> process, or relationship diagram must be rendered as proper Mermaid.
- `mermaid-diagrams` skill: Read the skill file to get standard syntax for
  `flowchart`, `C4`, `gantt`, `sequenceDiagram`, `classDiagram`, `erDiagram`
- Output: `.mmd` files or `mermaid` code blocks embedded in Markdown
- See Phase 4 rules for node count limit (≤ 15), labeling rules, and type selection

### Memory & Organization
- `memory_get` / `memory_search`: Reference previous research
- `write`: Create persistent research records
- Structured file organization for findings

## Research Quality Standards

### Source Diversity
- Include multiple perspectives on controversial topics
- Balance popular and academic sources
- Include international viewpoints when relevant
- Seek primary sources when possible

### Temporal Relevance
- Prioritize recent information for fast-changing topics
- Consider historical context for trend analysis
- Note when information was published
- Flag potentially outdated information

### Authority Assessment
- Prioritize peer-reviewed academic sources
- Consider author credentials and institutional affiliation
- Check for potential conflicts of interest
- Verify organizational reputation

## Iterative Research Approach

### Cycle 1: General Overview
- Broad search to understand the topic landscape
- Identify key terms, concepts, and stakeholders
- Establish initial research questions

### Cycle 2: Focused Investigation
- Targeted searches based on initial findings
- Deep dive into specific aspects
- Begin synthesis of information

### Cycle 3: Validation & Refinement
- Verify key claims across multiple sources
- Resolve contradictions
- Refine understanding based on evidence

### Cycle 4: Synthesis & Reporting
- Combine findings into coherent narrative
- **🔴 Convert ALL ASCII diagrams to Mermaid (mermaid-diagrams skill is MANDATORY)**
- Identify remaining uncertainties
- Prepare final research report
- **Quality gate: Does the report contain any ASCII art/box diagrams that should be Mermaid?**

## Output Structure

### Research Report Template
```
# [Research Topic] - Deep Research Report

## Executive Summary
[2-3 sentence summary of key findings]

## Research Questions
[Specific questions investigated]

## Methodology
[Description of research approach and tools used]

## Key Findings
[Main discoveries organized by theme]

## [REQUIRED] Mermaid Visualizations
[Convert all ASCII diagrams to Mermaid code blocks.
 At minimum include: corporate structure, business overview, key event timeline.
 Mermaid code blocks go in this section. See Phase 4 Mermaid rules.]

## Supporting Evidence
[Evidence supporting each finding with sources]

## Contradictions/Debates
[Areas of disagreement among sources]

## Source Credibility Assessment
[Evaluation of information sources]

## Limitations
[Identified limitations in research]

## Further Research Needed
[Questions requiring additional investigation]
```

> **⚠️ REMINDER: Before finalizing the report, ALWAYS invoke `mermaid-diagrams` skill
> and convert any ASCII/text architecture diagrams to proper Mermaid syntax.**
> See Phase 4 → Mermaid Visualization section for full conversion rules.

## Use Cases

### Academic Research
- Literature reviews
- Topic exploration
- Source verification

### Business Intelligence
- Market analysis
- Competitive research
- Technology trends

### Fact Checking
- Claim verification
- Misinformation identification
- Source credibility assessment

### Personal Learning
- Deep topic exploration
- Concept clarification
- Question resolution

## Quality Assurance

- Always verify critical claims against multiple sources
- Flag information that seems unreliable
- Maintain skepticism toward sensational claims
- Prioritize authoritative sources over anonymous ones
- Document all sources for verification purposes