# python-claude-code-mini

**中文** | [English](README.md)

一个用 Python 实现的 Claude Code CLI 工具，参考自 Anthropic 官方的 `@anthropic-ai/claude-code`。

## ⚠️ 重要声明

- **非官方项目**：本项目是独立开发的 Python 实现，与 Anthropic 官方无关
- **学习目的**：仅供学习和研究使用
- **功能参考**：参考了官方 Claude Code 的核心设计理念

## ✨ 特性

- 🛠️ **丰富的工具系统**：支持 Bash、文件操作、代码搜索等 10+ 核心工具
- 🔐 **权限管理**：多层权限检查，支持自动/手动模式
- 📡 **MCP 协议支持**：Model Context Protocol 集成
- 🔄 **流式响应**：实时显示 AI 思考和工具执行过程
- 📝 **灵活配置**：YAML/TOML 配置文件支持
- 🎯 **智能重试**：指数退避 + 速率限制处理
- 🔌 **可扩展架构**：易于添加自定义工具和命令
- 💾 **持久化记忆系统**：基于文件的记忆存储，支持四种记忆类型（用户/反馈/项目/参考）
- 🧠 **上下文管理**：智能上下文窗口控制，支持 Compact 压缩模式
- 📚 **Prompt 工程**：系统 Prompt 构建逻辑

## 📦 安装

```bash
# 克隆项目
git clone https://github.com/Gussin8/python-claude-code-mini.git
cd python-claude-code-mini

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或者
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## 🚀 快速开始

### 1. 配置 API Key

```bash
# 方式 1: 环境变量
export ANTHROPIC_API_KEY="your-api-key"

# 方式 2: 配置文件
mkdir -p ~/.python-claude-mini
cat > ~/.python-claude-code-mini/config.yaml << EOF
auth:
  api_key: your-api-key
  
model:
  default: claude-sonnet-4-20250514
  
permissions:
  mode: default  # default, auto, bypass
EOF
```

### 2. 启动 CLI

```bash
# 交互模式
python-claude

# 单次查询
python-claude "帮我查看当前目录的文件结构"

# 指定模型
python-claude --model claude-opus-4-20250514 "分析这个项目的架构"
```

## 📖 文档

### 核心文档

- [架构设计](architecture.md)

## 🛠️ 核心工具

| 工具 | 描述 | 权限要求 |
|------|------|----------|
| `Bash` | 执行 Shell 命令 | 需要确认（危险命令） |
| `FileRead` | 读取文件内容 | 只读 |
| `FileEdit` | 编辑文件 | 写入 |
| `FileWrite` | 写入新文件 | 写入 |
| `Glob` | 文件模式匹配 | 只读 |
| `Grep` | 文本搜索 | 只读 |
| `WebSearch` | 网络搜索 | 只读 |
| `WebFetch` | 获取网页内容 | 只读 |
| `AskUserQuestion` | 向用户提问 | 交互 |
| `TodoWrite` | 管理任务列表 | 只读 |

## 📋 项目结构

```
python-claude-code/
├── src/
│   ├── __init__.py
│   ├── cli.py              # CLI 入口和命令解析
│   ├── main.py             # 主循环和 REPL
│   │
│   ├── tools/              # 工具实现
│   │   ├── __init__.py
│   │   ├── base.py         # 工具基类和接口
│   │   ├── bash.py         # Bash 工具
│   │   ├── file_read.py    # 文件读取
│   │   ├── file_edit.py    # 文件编辑
│   │   ├── file_write.py   # 文件写入
│   │   ├── glob.py         # Glob 匹配
│   │   ├── grep.py         # Grep 搜索
│   │
│   ├── services/           # 服务层
│   │   ├── __init__.py
│   │   ├── api.py          # Anthropic API 封装
│   │   ├── prompt.py       # System Prompt 构建
│   │   ├── context.py      # 上下文管理
│   │   ├── compact.py      # Compact 压缩
│   │   └── retry.py        # 重试机制
│   │
│   ├── memdir/             # 记忆系统
│   │   ├── __init__.py
│   │   ├── memory_types.py # 四种记忆类型定义
│   │   ├── memory_scan.py  # 记忆文件扫描
│   │   ├── memory_age.py   # 记忆新鲜度计算
│   │   ├── find_relevant_memories.py  # 相关记忆检索
│   │   └── memdir.py       # 记忆目录管理
│   │
│   ├── permissions/        # 权限系统
│   │   ├── __init__.py
│   │   ├── checker.py      # 权限检查器
│   │   └── classifier.py   # 自动分类器
│   │
│   └── config/             # 配置管理
│       ├── __init__.py
│       └── config.py       # 配置加载和验证
│
│
└── README.md
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Anthropic](https://www.anthropic.com) - Claude AI 的创造者
