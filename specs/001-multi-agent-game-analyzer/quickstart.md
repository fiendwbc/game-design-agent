# Quickstart Guide: Multi-Agent Game Analysis System

本指南帮助你快速启动并运行游戏分析系统。

## 前置要求

- **操作系统**: Windows 10/11
- **Python**: 3.11+
- **网络**: 需要访问 Google Gemini API
- **API Key**: Google AI Studio API Key (GOOGLE_API_KEY)

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd game-design-agent
```

### 2. 安装 uv (如果尚未安装)

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### 3. 创建虚拟环境并安装依赖

```bash
uv venv
uv sync
```

### 4. 配置环境变量

创建 `.env` 文件：

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key_here
```

或设置环境变量：

```powershell
# PowerShell
$env:GOOGLE_API_KEY = "your_gemini_api_key_here"
```

## 基本使用

### 1. 查看帮助

```bash
uv run python -m src.main --help
```

### 2. 选择游戏窗口区域

```bash
uv run python -m src.main select-region
```

这将打开一个交互式工具，让你选择游戏窗口区域。选择完成后，配置将保存到 `config.json`。

### 3. 开始分析会话

```bash
# 使用默认配置 (探索模式, 50步)
uv run python -m src.main run

# 指定步数和策略
uv run python -m src.main run --max-steps 100 --strategy completion

# 指定输出目录
uv run python -m src.main run --output ./my_analysis
```

### 4. 查看生成的文档

分析完成后，文档将保存在输出目录：

```
output/
├── session_2025-12-16_143022/
│   ├── gdd.md                 # 游戏策划案
│   ├── numerical_analysis.json # 数值分析
│   ├── art_report.md          # 美术风格报告
│   ├── ui_flow.json           # UI 流程图数据
│   ├── screenshots/           # 关键截图
│   └── logs/                  # 会话日志
```

## 配置文件

### config.json 示例

```json
{
  "window_region": {
    "x": 100,
    "y": 100,
    "width": 800,
    "height": 600
  },
  "max_steps": 100,
  "strategy": "exploration",
  "output_dir": "./output",
  "log_level": "detailed",
  "video_segment_duration": 3.0
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| window_region | object | - | 游戏窗口区域 |
| max_steps | int | 100 | 最大步数 (1-1000) |
| strategy | string | "exploration" | 策略: exploration/completion |
| output_dir | string | "./output" | 输出目录 |
| log_level | string | "detailed" | 日志级别: minimal/detailed/debug |
| video_segment_duration | float | 3.0 | 视频片段时长 (2-5秒) |

## 命令参考

### run - 运行分析会话

```bash
uv run python -m src.main run [OPTIONS]

Options:
  --config PATH           配置文件路径 [default: config.json]
  --max-steps INT         最大步数 [default: 100]
  --strategy TEXT         策略: exploration/completion [default: exploration]
  --output PATH           输出目录 [default: ./output]
  --log-level TEXT        日志级别: minimal/detailed/debug [default: detailed]
  --help                  显示帮助信息
```

### select-region - 选择窗口区域

```bash
uv run python -m src.main select-region [OPTIONS]

Options:
  --save PATH             保存配置到文件 [default: config.json]
  --help                  显示帮助信息
```

### export - 导出分析结果

```bash
uv run python -m src.main export SESSION_DIR [OPTIONS]

Options:
  --format TEXT           导出格式: markdown/json/html [default: markdown]
  --output PATH           输出路径
  --help                  显示帮助信息
```

## 日志级别

### minimal
仅记录错误信息，适合生产环境或不需要调试时使用。

### detailed (推荐)
记录每步决策和 API 调用，适合大多数场景。

```
[INFO] Step 1: Observing game screen...
[INFO] Step 1: Player-Agent decision: click at (500, 300) - "点击开始按钮"
[INFO] Step 1: Action executed successfully
[INFO] Step 1: Mechanics-Analyst: Identified main menu
[INFO] Step 1: UI-Agent: Added node "主界面"
```

### debug
完整调试信息，包含截图和视频存档路径，适合问题排查。

```
[DEBUG] Step 1: Screenshot saved to ./debug/step_001_before.png
[DEBUG] Step 1: Video segment: ./debug/step_001_video.mp4
[DEBUG] Step 1: Gemini API request: {...}
[DEBUG] Step 1: Gemini API response: {...}
```

## 常见问题

### Q: 游戏窗口无法捕获？

确保：
1. 游戏以窗口模式运行（非全屏独占）
2. 窗口区域坐标正确
3. 以管理员权限运行（某些游戏需要）

### Q: 鼠标点击无效？

某些游戏可能有反作弊机制。尝试：
1. 以管理员权限运行
2. 关闭游戏的反作弊功能（如果可以）
3. 使用更慢的点击速度

### Q: API 调用失败？

检查：
1. GOOGLE_API_KEY 是否正确设置
2. 网络连接是否正常
3. API 配额是否充足

系统会自动重试 3 次。如果持续失败，会暂停等待你的决定。

### Q: 文档生成不完整？

QA-Critic 会检查文档完整性。如果发现缺失：
1. 检查游戏会话是否足够长（至少 30 步推荐）
2. 确保游戏包含多种玩法元素
3. 查看日志了解哪些分析步骤失败

## 下一步

- 阅读 [技术架构文档](./plan.md) 了解系统设计
- 查看 [数据模型文档](./data-model.md) 了解数据结构
- 参考 [API 契约](./contracts/) 了解 Agent 输出格式
