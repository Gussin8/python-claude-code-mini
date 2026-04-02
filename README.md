# python-claude-code-mini

[中文文档](README_zh.md) | **English**

A Python implementation of the Claude Code CLI tool, inspired by Anthropic's official `@anthropic-ai/claude-code`.

## ⚠️ Disclaimer

- **Unofficial Project**: This is an independently developed Python implementation, not affiliated with Anthropic
- **Educational Purpose**: Intended for learning and research use only
- **Feature Reference**: Inspired by the core design principles of the official Claude Code

## ✨ Features

- 🛠️ **Rich Tool System**: 10+ core tools including Bash, file operations, code search, and more
- 🔐 **Permission Management**: Multi-layer permission checks with auto/manual modes
- 📡 **MCP Protocol Support**: Model Context Protocol integration
- 🔄 **Streaming Responses**: Real-time display of AI reasoning and tool execution
- 📝 **Flexible Configuration**: YAML/TOML configuration file support
- 🎯 **Smart Retry**: Exponential backoff + rate limit handling
- 🔌 **Extensible Architecture**: Easy to add custom tools and commands
- 💾 **Persistent Memory System**: File-based memory storage with four memory types (user/feedback/project/reference)
- 🧠 **Context Management**: Intelligent context window control with Compact compression mode
- 📚 **Prompt Engineering**: System prompt construction logic

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Gussin8/python-claude-code-mini.git
cd python-claude-code-mini

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
```

## 🚀 Quick Start

### 1. Configure API Key

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY="your-api-key"

# Option 2: Configuration file
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

### 2. Launch CLI

```bash
# Interactive mode
python-claude

# Single query
python-claude "Show me the file structure of the current directory"

# Specify model
python-claude --model claude-opus-4-20250514 "Analyze the architecture of this project"
```

## 📖 Documentation

### Core Documentation

- [Architecture Design](architecture.md)

## 🛠️ Core Tools

| Tool | Description | Permission |
|------|-------------|------------|
| `Bash` | Execute shell commands | Confirmation required (dangerous commands) |
| `FileRead` | Read file contents | Read-only |
| `FileEdit` | Edit files | Write |
| `FileWrite` | Write new files | Write |
| `Glob` | File pattern matching | Read-only |
| `Grep` | Text search | Read-only |
| `WebSearch` | Web search | Read-only |
| `WebFetch` | Fetch web content | Read-only |
| `AskUserQuestion` | Ask user questions | Interactive |
| `TodoWrite` | Manage task lists | Read-only |

## 📋 Project Structure

```
python-claude-code/
├── src/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point and command parsing
│   ├── main.py             # Main loop and REPL
│   │
│   ├── tools/              # Tool implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Tool base class and interfaces
│   │   ├── bash.py         # Bash tool
│   │   ├── file_read.py    # File reading
│   │   ├── file_edit.py    # File editing
│   │   ├── file_write.py   # File writing
│   │   ├── glob.py         # Glob matching
│   │   ├── grep.py         # Grep search
│   │
│   ├── services/           # Service layer
│   │   ├── __init__.py
│   │   ├── api.py          # Anthropic API wrapper
│   │   ├── prompt.py       # System prompt construction
│   │   ├── context.py      # Context management
│   │   ├── compact.py      # Compact compression
│   │   └── retry.py        # Retry mechanism
│   │
│   ├── memdir/             # Memory system
│   │   ├── __init__.py
│   │   ├── memory_types.py # Four memory type definitions
│   │   ├── memory_scan.py  # Memory file scanning
│   │   ├── memory_age.py   # Memory freshness calculation
│   │   ├── find_relevant_memories.py  # Relevant memory retrieval
│   │   └── memdir.py       # Memory directory management
│   │
│   ├── permissions/        # Permission system
│   │   ├── __init__.py
│   │   ├── checker.py      # Permission checker
│   │   └── classifier.py   # Auto classifier
│   │
│   └── config/             # Configuration management
│       ├── __init__.py
│       └── config.py       # Configuration loading and validation
│
│
└── README.md
```

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

MIT License

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com) - Creator of Claude AI
