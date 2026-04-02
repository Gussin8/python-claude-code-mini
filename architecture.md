# Python Claude Code 架构文档

## 1. 项目概述

Python Claude Code 是一个用 Python 实现的 Claude Code CLI 工具，参考了 Anthropic 官方的 `@anthropic-ai/claude-code` TypeScript 实现。

### 1.1 核心目标

- 提供一个 Python 原生的 Claude Code 替代方案
- 保持与官方版本相似的功能和用户体验
- 利用 Python 生态系统优势（易用性、丰富的库）
- 支持 MCP (Model Context Protocol) 协议（计划中）

### 1.2 技术栈

| 组件 | 技术选择 | 说明 |
|------|----------|------|
| CLI 框架 | **Typer** | 基于 type hints，自动生成帮助文档 |
| HTTP 客户端 | **httpx** | 异步支持，更好的性能 |
| YAML 配置 | **PyYAML** | 成熟稳定 |
| 终端 UI | **Rich** | 美观的终端输出 |
| 验证 | **Pydantic** | 强大的数据验证 |
| Anthropic SDK | **anthropic** | 官方 SDK |

---

## 2. 目录结构

```
python-claude-code/
├── src/
│   ├── __init__.py           # 包信息
│   ├── cli.py                # CLI 入口
│   ├── main.py               # REPL 启动器
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py         # 配置管理
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py           # 工具基类
│   │   ├── context.py        # 工具上下文
│   │   ├── registry.py       # 工具注册表
│   │   ├── bash.py           # Bash 工具
│   │   ├── file_read.py      # 文件读取
│   │   ├── file_write.py     # 文件写入
│   │   ├── file_edit.py      # 文件编辑
│   │   ├── glob.py           # Glob 匹配
│   │   └── grep.py           # Grep 搜索
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api.py            # API 服务
│   │   └── retry.py          # 重试机制
│   └── permissions/
│       ├── __init__.py
│       ├── checker.py        # 权限检查器
│       └── classifier.py     # 自动分类器
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 3. 核心模块

### 3.1 工具系统

工具系统是核心，所有功能都通过工具实现。

#### 工具接口

```python
class Tool(ABC, Generic[InputT, OutputT, ProgressT]):
    """工具基类"""
    
    name: str                          # 工具名称
    input_schema: type[BaseModel]      # 输入 Schema
    output_schema: Optional[type]      # 输出 Schema
    
    async def call(...) -> ToolResult[OutputT]:
        """执行工具"""
        pass
    
    def get_description() -> str:
        """获取描述（发送给 AI）"""
        pass
    
    def is_read_only() -> bool:        # 是否只读
    def is_destructive() -> bool:      # 是否破坏性
    def is_concurrency_safe() -> bool: # 是否可并发
```

#### 内置工具

| 工具 | 功能 | 只读 | 并发安全 |
|------|------|------|----------|
| Bash | 执行 Shell 命令 | ❌ | ✅ |
| FileRead | 读取文件 | ✅ | ✅ |
| FileWrite | 写入文件 | ❌ | ❌ |
| FileEdit | 编辑文件 | ❌ | ❌ |
| Glob | 文件匹配 | ✅ | ✅ |
| Grep | 文本搜索 | ✅ | ✅ |

### 3.2 配置系统

三层配置优先级：

1. **命令行参数** - 最高优先级
2. **配置文件** (~/.python-claude-code/config.yaml)
3. **环境变量** - 最低优先级

```python
config = GlobalConfig.load()
# config.auth.api_key
# config.model.default
# config.permissions.mode
```

### 3.3 权限系统

#### 权限模式

- `default` - 默认模式，危险操作询问用户
- `auto` - 自动模式，使用分类器决策
- `bypass` - 绕过权限（仅允许白名单否决）
- `dontAsk` - 不询问，未明确允许的拒绝

#### 权限规则

```yaml
permissions:
  mode: default
  always_allow_rules:
    - tool_name: FileRead
    - tool_name: Bash
      pattern: "git status"
  always_deny_rules:
    - tool_name: Bash
      pattern: "rm -rf /"
```

### 3.4 API 服务

封装 Anthropic SDK：

```python
api = APIService(api_key="...")

options = QueryOptions(
    model="claude-sonnet-4-20250514",
    system_prompt="...",
    tools=[...],
)

async for event in api.query_model(messages, options):
    if event.type == "content_block_delta":
        print(event.data["delta"]["text"], end="")
```

### 3.5 重试机制

指数退避策略：

```python
result = await with_retry(
    api_call,
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True,
)
```

延迟计算：`delay = base_delay * (2 ^ attempt) + jitter`

---

## 4. 核心流程

### 4.1 启动流程

```
CLI 入口 (cli.py)
    ↓
加载配置 (GlobalConfig.load())
    ↓
检查 API Key
    ↓
单次查询 or REPL 模式
    ↓
初始化工具列表
    ↓
启动主循环
```

### 4.2 查询流程

```
用户输入
    ↓
构建消息历史
    ↓
调用 API (query_model)
    ↓
流式接收响应
    ├─ content_block_delta → 显示文本
    └─ tool_use → 执行工具
    ↓
添加工具结果
    ↓
继续对话
```

### 4.3 工具执行流程

```
AI 生成工具调用
    ↓
查找工具 (get_tool_by_name)
    ↓
验证输入 (validate_input)
    ↓
检查权限 (check_permissions)
    ↓
执行工具 (call)
    ↓
渲染结果 (render_tool_result)
    ↓
返回给 AI
```

---

## 5. 扩展开发

### 5.1 添加新工具

1. 创建工具类继承 `Tool`

```python
from .base import Tool, ToolResult, ToolContext

class MyInput(BaseModel):
    param: str

class MyOutput:
    result: str

class MyTool(Tool[MyInput, MyOutput, None]):
    name = "MyTool"
    input_schema = MyInput
    
    def get_description(self):
        return "My custom tool"
    
    async def call(self, args, context, ...):
        # 实现逻辑
        return ToolResult(output=MyOutput(result="..."))
```

2. 注册到工具表

```python
# src/tools/registry.py
def _register_builtin_tools():
    from .my_tool import MyTool
    register_tool(MyTool)
```

### 5.2 自定义权限规则

```python
from .permissions import PermissionChecker, PermissionRule

checker = PermissionChecker(
    always_allow=[
        PermissionRule("FileRead"),
        PermissionRule("Bash", pattern="git *"),
    ],
    always_deny=[
        PermissionRule("Bash", pattern="rm *"),
    ]
)
```

---

## 6. 最佳实践

### 6.1 安全性

- 始终检查工作目录外路径
- 对大输出进行截断
- 危险命令需要确认
- 不保存敏感信息到日志

### 6.2 性能

- 使用异步 I/O
- 工具并发执行（如果安全）
- 缓存文件状态
- 限制搜索结果数量

### 6.3 错误处理

- 捕获并包装所有异常
- 提供有意义的错误消息
- 使用重试机制处理临时错误
- 记录详细日志（verbose 模式）

---

## 7. 测试

### 7.1 单元测试

```python
import pytest
from src.tools.bash import BashTool, BashInput

@pytest.mark.asyncio
async def test_bash_tool():
    tool = BashTool()
    context = ToolContext(working_directory=Path.cwd())
    
    result = await tool.call(
        BashInput(command="echo hello"),
        context=context,
        can_use_tool=lambda: True,
    )
    
    assert result.output.stdout.strip() == "hello"
```

### 7.2 集成测试

```python
@pytest.mark.asyncio
async def test_full_query():
    config = GlobalConfig.load()
    launcher = REPLLauncher(config)
    
    # 模拟用户输入
    launcher.messages.append({"role": "user", "content": "Hello"})
    
    # 执行查询
    await launcher._query_and_respond()
    
    # 检查响应
    assert len(launcher.messages) > 1
```

---

## 8. 故障排除

### 8.1 常见问题

**Q: API key 错误**
```bash
Error: Authentication failed: Invalid API key
```
解决：检查 `ANTHROPIC_API_KEY` 环境变量

**Q: 工具执行超时**
```bash
Command timed out after 60 seconds
```
解决：增加 `timeout` 参数或使用后台执行

**Q: 权限拒绝**
```bash
File is outside allowed directories
```
解决：检查工作目录或添加额外允许目录

### 8.2 调试技巧

启用详细输出：
```bash
python-claude -v
```

查看日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 9. 未来计划

- [ ] MCP 协议支持
- [ ] 更多内置工具（WebSearch, TodoWrite 等）
- [ ] 钩子系统
- [ ] 技能系统
- [ ] 代理模式
- [ ] GUI 界面
