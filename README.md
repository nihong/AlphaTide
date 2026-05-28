# RGChooseStock: AI 驱动的“10倍股”自动搜寻哨兵

RGChooseStock 是一个全自动化的 AI 投资决策支持系统，专门设计用于在 A 股和港股市场中寻找具备“10倍股”潜力的优质标的。它结合了深度基本面筛选、市场轮动预测、技术面验证以及大模型（DeepSeek）的自动化点评。

## 🌟 核心功能

- **🚦 大盘红绿灯**：实时监控大盘（沪深300）趋势，自动识别多/空环境，空头市场自动预警并停止买入操作。
- **🔥 行业潮汐定位**：通过分析资金流向，锁定处于“蓄势待发”阶段（资金流入但价格未引爆）的潜力行业，拒绝追高。
- **🧬 10倍股基因筛选**：
    - **盈利能力**：ROE > 15%。
    - **利润质量**：净现比 > 1.0（确保赚的是真钱）。
    - **业绩前瞻**：合同负债（预收款）高增长。
- **📈 多维强度验证**：
    - **RS 相对强度**：筛选走势强于大盘的个股，确保是领涨标的。
    - **趋势过滤**：价格必须站稳 MA20 均线。
- **🛑 双轨卖出预警**：
    - **激进型**：破 20 日线止损（趋势破坏）。
    - **保守型**：乖离率过大（BIAS > 15%）止盈（情绪过热）。
- **🧠 AI 自动研报**：集成 DeepSeek API，收盘后自动生成深度分析报告。

## 🏗️ 目录结构

```text
├── main.py                # 系统启动入口
├── AGENTS.md              # AI 智能体指令集（跨模型记忆）
├── reports/               # 每日生成的决策日报 (Markdown)
├── history/               # 行业蓄势指数历史数据
├── src/
│   ├── market_monitor.py  # 核心监控大脑
│   ├── data_fetcher.py    # 数据采集与缓存层
│   ├── rotation_predictor.py # 行业轮动预测
│   ├── screener.py        # 财务/技术筛选引擎
│   ├── risk_manager.py    # RS强度与卖出预警
│   ├── ai_analyst.py      # DeepSeek API 接入
│   └── history_manager.py # 历史记忆管理
└── .env                   # 隐私配置文件（API Key）
```

## 🚀 快速启动

### 1. 环境准备
```bash
git clone https://github.com/你的用户名/RGChooseStock.git
cd RGChooseStock
pip install -r requirements.txt
```

### 2. 配置 API Key
复制 `.env.example` 为 `.env`，填入您的 DeepSeek Key：
```bash
cp .env.example .env
# 编辑 .env 文件，填入 DEEPSEEK_API_KEY=sk-xxxx
```

### 3. 运行自动化扫描
```bash
python3 main.py --auto
```

### 4. 设置每日自动运行 (macOS/Linux)
使用 `crontab` 在每日收盘后（16:00）运行：
```bash
0 16 * * 1-5 cd /你的路径/RGChooseStock && /usr/bin/python3 main.py --auto
```

## 🔐 安全声明
- 本项目严禁在代码中硬编码任何 API 密钥。
- `.env` 文件和 `.cache/` 缓存目录已被加入 `.gitignore`，不会上传至公开仓库。

## 📈 投资策略说明
本项目倡导**“基本面选股 + 资金流择时 + 趋势控仓”**的投资理念。
- **静态选好股**：看财报，找高 ROE 和真现金流。
- **动态选时机**：看潮汐，找蓄势行业。
- **风险控收益**：看均线，不破不走，过热分批。

---
*声明：本工具仅供研究参考，不构成任何投资建议。股市有风险，入市需谨慎。*
