# Multi-Agent Game Analysis System - 使用说明

本文档介绍如何安装、配置和使用 game-design-agent 系统。

---

## 目录

1. [环境要求](#环境要求)
2. [安装步骤](#安装步骤)
3. [配置说明](#配置说明)
4. [CLI 命令详解](#cli-命令详解)
5. [快速开始](#快速开始)
6. [常见问题](#常见问题)

---

## 环境要求

### 系统要求
- **操作系统**: Windows 10/11 (pydirectinput 仅支持 Windows)
- **Python**: 3.11 或更高版本
- **包管理**: uv (推荐) 或 pip

### API 密钥
- **Google AI API Key**: 用于访问 Gemini 模型
  - 获取地址: https://makersuite.google.com/app/apikey

---

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd game-design-agent
```

### 2. 安装依赖

使用 uv (推荐):
```bash
uv sync
uv sync --extra dev  # 包含开发依赖
```

使用 pip:
```bash
pip install -e .
pip install -e ".[dev]"  # 包含开发依赖
```

### 3. 配置环境变量

复制环境变量模板:
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API 密钥:
```env
GOOGLE_API_KEY=your-api-key-here
LOG_LEVEL=detailed
OUTPUT_DIR=./output
```

### 4. 验证安装

```bash
uv run python -m src.main status
```

如果看到所有依赖显示 "✓ Installed"，说明安装成功。

---

## 配置说明

### 环境变量 (.env)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GOOGLE_API_KEY` | Google AI API 密钥 | (必填) |
| `LOG_LEVEL` | 日志级别: minimal/detailed/debug | detailed |
| `OUTPUT_DIR` | 输出目录 | ./output |
| `MAX_STEPS` | 默认最大步数 | 100 |
| `PLAY_STRATEGY` | 默认策略: exploration/completion | exploration |
| `PLAYER_MODEL` | Player-Agent 模型 | gemini-2.0-flash |
| `ANALYST_MODEL` | 分析 Agent 模型 | gemini-3-pro-preview |

### 配置文件 (config.json)

可以创建 `config.json` 保存会话配置:

```json
{
  "window_region": {
    "x": 100,
    "y": 100,
    "width": 800,
    "height": 600
  },
  "max_steps": 50,
  "strategy": "exploration"
}
```

---

## CLI 命令详解

### 查看帮助

```bash
uv run python -m src.main --help
uv run python -m src.main <command> --help
```

### status - 系统状态

检查系统配置和依赖状态:

```bash
uv run python -m src.main status
```

输出示例:
```
               System Status
┌───────────────────┬──────────────────────┐
│ Setting           │ Value                │
├───────────────────┼──────────────────────┤
│ Google API Key    │ Set                  │
│ Log Level         │ detailed             │
│ Player Model      │ gemini-2.0-flash     │
│ Analyst Model     │ gemini-3-pro-preview │
└───────────────────┴──────────────────────┘
```

### select-region - 选择游戏窗口区域

#### 列出所有可见窗口

```bash
uv run python -m src.main select-region --list
```

#### 按窗口标题选择

```bash
uv run python -m src.main select-region --window "游戏窗口标题"
```

#### 交互式选择

```bash
uv run python -m src.main select-region --interactive
```

#### 保存配置

```bash
uv run python -m src.main select-region --window "Game" --save config.json
```

### test-capture - 测试屏幕捕获

验证捕获区域是否正确:

```bash
# 使用默认区域
uv run python -m src.main test-capture

# 指定区域
uv run python -m src.main test-capture --x 100 --y 100 -W 800 -H 600 -o screenshot.png
```

### run - 运行游戏分析会话

#### 基本用法

```bash
uv run python -m src.main run
```

#### 使用配置文件

```bash
uv run python -m src.main run --config config.json
```

#### 指定参数

```bash
uv run python -m src.main run \
  --x 100 --y 100 -W 800 -H 600 \
  --max-steps 50 \
  --strategy exploration \
  --output ./my_output \
  --log-level detailed
```

#### 预览配置（不运行）

```bash
uv run python -m src.main run --dry-run
```

#### 参数说明

| 参数 | 短参数 | 说明 | 默认值 |
|------|--------|------|--------|
| `--config` | `-c` | 配置文件路径 | - |
| `--max-steps` | `-n` | 最大步数 (1-1000) | 100 |
| `--strategy` | `-S` | 策略: exploration/completion | exploration |
| `--output` | `-o` | 输出目录 | ./output |
| `--log-level` | `-l` | 日志级别 | detailed |
| `--x` | - | 窗口区域 X 坐标 | 100 |
| `--y` | - | 窗口区域 Y 坐标 | 100 |
| `--width` | `-W` | 窗口区域宽度 | 800 |
| `--height` | `-H` | 窗口区域高度 | 600 |
| `--dry-run` | `-d` | 仅显示配置不运行 | false |

### export - 导出分析结果

#### 导出为 Markdown

```bash
uv run python -m src.main export ./output -f markdown -o report.md
```

#### 导出为 JSON

```bash
uv run python -m src.main export ./output -f json -o report.json
```

#### 输出到终端

```bash
uv run python -m src.main export ./output
```

---

## 快速开始

### 步骤 1: 配置 API 密钥

```bash
# 创建 .env 文件
echo "GOOGLE_API_KEY=your-key-here" > .env
```

### 步骤 2: 检查系统状态

```bash
uv run python -m src.main status
```

### 步骤 3: 找到游戏窗口

```bash
# 列出所有窗口
uv run python -m src.main select-region --list

# 选择目标窗口并保存
uv run python -m src.main select-region --window "Minesweeper" --save config.json
```

### 步骤 4: 测试屏幕捕获

```bash
uv run python -m src.main test-capture -o test.png
# 检查 test.png 确认捕获区域正确
```

### 步骤 5: 运行游戏分析

```bash
# 使用配置文件运行
uv run python -m src.main run --config config.json --max-steps 20

# 或直接指定参数
uv run python -m src.main run --x 100 --y 100 -W 800 -H 600 -n 20
```

### 步骤 6: 查看结果

```bash
# 导出报告
uv run python -m src.main export ./output -f markdown -o report.md
```

---

## 常见问题

### Q: 提示 "Google API Key Not Set"

A: 确保在 `.env` 文件中正确设置了 `GOOGLE_API_KEY`，或者设置环境变量:
```bash
set GOOGLE_API_KEY=your-key-here  # Windows
export GOOGLE_API_KEY=your-key-here  # Linux/Mac
```

### Q: 屏幕捕获失败

A:
1. 确保目标窗口没有被其他窗口遮挡
2. 使用 `test-capture` 命令验证区域设置
3. 某些游戏可能使用硬件加速，导致捕获黑屏

### Q: pydirectinput 导入错误

A: pydirectinput 仅支持 Windows 系统。确保在 Windows 环境下运行。

### Q: 会话中途停止

A:
- 按 `Ctrl+C` 可以中断会话
- 检查 `output` 目录中的 `play_log_*.json` 了解停止原因
- 如果是 API 错误，检查 API 配额和网络连接

### Q: 游戏检测不到结束

A: Player-Agent 的游戏结束检测基于视觉分析。对于某些游戏，可能需要：
- 增加 `--max-steps` 限制
- 使用 `completion` 策略

---

## 程序化使用

### 基本示例

```python
from pathlib import Path
from src.models import PlayStrategy, LogLevel
from src.models.session import PlaySession, SessionConfig, WindowRegion
from src.orchestrator.graph import run_game_session

# 配置会话
region = WindowRegion(x=100, y=100, width=800, height=600)
config = SessionConfig(
    window_region=region,
    max_steps=50,
    strategy=PlayStrategy.EXPLORATION,
    output_dir=Path("./output"),
    log_level=LogLevel.DETAILED,
)

# 创建并运行会话
session = PlaySession(config=config)
final_state = run_game_session(session)

print(f"Session completed with status: {final_state['status']}")
print(f"Total steps: {final_state['current_step']}")
```

### 使用回调

```python
from src.orchestrator.graph import SessionRunner

def on_step(step: int, state: dict):
    action = state.get("pending_action")
    if action:
        print(f"Step {step}: {action.action_type.value}")

runner = SessionRunner(session)
runner.add_callback(on_step)
final_state = runner.run()
```

### 单步调试

```python
from src.orchestrator.graph import create_initial_state, run_single_step
from src.orchestrator.nodes import init_session_resources

# 初始化资源
init_session_resources(
    region=session.config.window_region,
    session_id=session.id,
    output_dir=session.config.output_dir,
)

# 创建初始状态
state = create_initial_state(session)

# 执行单步
state = run_single_step(state)
print(f"Action: {state.get('pending_action')}")
```

---

## 更多资源

- [开发进展报告](./development-progress.md)
- [设计规范](../specs/001-multi-agent-game-analyzer/spec.md)
- [任务列表](../specs/001-multi-agent-game-analyzer/tasks.md)
