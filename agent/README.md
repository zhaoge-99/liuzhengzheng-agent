# Agent

这是一个带安全工具白名单、支持多种模型服务的中文命令行 Agent。

## 安装

在项目根目录（包含 `requirements.txt` 和 `agent` 文件夹的目录）下运行：

```powershell
cd AgentProject
python -m pip install -r requirements.txt
```

## 安装为 CLI 命令

开发或本机使用时，可以在项目根目录运行：

```powershell
python -m pip install .
```

安装完成后即可直接启动：

```powershell
aiden
```

更推荐使用 `pipx` 安装，使 Agent 和其他 Python 工具保持隔离：

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
pipx install D:\AgentProject
aiden
```

更新代码后重新安装：

```powershell
pipx install --force D:\AgentProject
```

## 开发测试

项目包含基础单元测试，覆盖工具参数校验、工作区路径限制、时区工具、结构化工具错误以及会话隔离：

```powershell
python -m unittest discover -s tests -v
```

每个 CLI 进程创建一个独立的 `AgentSession`，会话对象持有状态机和对话上下文，避免将不同并发会话的数据放在模块级全局变量中。工具执行统一写入审计日志，并对未知工具、非法参数和执行异常返回包含 `status`、`code`、`message` 的 JSON 错误对象。

## 源码模块结构

```text
agent/
├── PrimaryAgent.py          # 安装命令的稳定入口
├── cli.py                   # 命令行循环和内建命令
├── session.py               # 单次会话、模型/工具往返与并发接入
├── configuration.py         # aiden_env 加载和配置校验
├── prompts.py               # 系统提示、输入校验及上下文脱敏
├── patch_workflow.py        # 补丁预览、确认、应用、验证和回滚流程
├── model_clients/
│   ├── base.py               # 统一客户端接口、响应类型和公共转换
│   ├── openai_compatible.py  # OpenAI 兼容服务适配器
│   ├── anthropic.py          # Anthropic 消息与工具格式适配
│   ├── gemini.py             # Gemini 内容与函数调用格式适配
│   └── factory.py            # 根据环境配置选择模型客户端
├── tooling/
│   ├── definitions.py        # 提供给模型的工具名称和参数 schema
│   ├── registry.py           # 工具名到 Python 函数的白名单映射
│   └── executor.py           # 参数校验、调用和统一错误/审计处理
├── skill_modules/
│   ├── core.py               # 文本校验、工作区根目录与安全路径
│   ├── basic.py              # 计算、天气、时间和运行信息
│   ├── files.py              # 文件读取、搜索和 Python 语法检查
│   ├── project.py            # 项目结构、符号和危险代码分析
│   ├── quality.py            # 测试、密钥扫描、linter 和类型检查
│   ├── patches.py            # Git 补丁校验、应用、预览和回滚
│   ├── tasks.py              # 持久化任务清单
│   └── web.py                # 公开网页读取
├── AgentState.py            # Agent 状态机
├── Concurrency.py           # 进程内并发闸门
└── AuditLog.py              # 脱敏审计日志
```

`CallModel.py`、`Execute_Tool.py` 和 `Skills.py` 保留为兼容入口：旧代码仍可按原来的模块名导入；新功能应放入上面对应职责的模块。主要调用方向是 `cli → session → tooling → skill_modules`，模型通信由 `session → model_clients` 负责，补丁写入流程单独由 `patch_workflow` 管理。

首次使用时，在项目目录或用户配置位置准备 `aiden_env`，至少配置：

```env
MODEL_PROVIDER=openai-compatible
MODEL_API_KEY=你的模型 API Key
MODEL_NAME=deepseek-chat
MODEL_BASE_URL=https://api.deepseek.com
```

不要把包含真实 API Key 的 `aiden_env` 打包、提交或发送给其他人。分发时应提供 `aiden_env.example`，让每位使用者自行配置自己的 Key。

交互过程中可使用 `/workspace`、`/status`、`/tasks`、`/clear`、`/help` 和 `/quit` 快捷命令。

## 配置模型 API

项目不会内置或上传模型 API Key。使用者需要配置所选模型服务的 API。

可以复制配置模板：

```powershell
Copy-Item agent\aiden_env.example aiden_env
```

然后打开项目根目录中的 `aiden_env`，填入自己的值。程序启动时会依次从当前目录、项目根目录和 `agent` 目录读取名为 `aiden_env` 的文件；PowerShell 用户也可以直接设置环境变量：

```powershell
$env:MODEL_PROVIDER = "openai-compatible"
$env:MODEL_API_KEY = "你的模型 API Key"
$env:MODEL_NAME = "gpt-4o-mini"
$env:MODEL_BASE_URL = "https://api.openai.com/v1"
```

安装本产品过程中会要求用户配置环境变量。如果未配置，可以在项目目录下手动创建 `aiden_env` 文件，程序会自动将文件内容加载到环境变量中。如果系统环境变量和 `aiden_env` 中都配置了同一个变量，系统环境变量的优先级最高。

其中：

- `MODEL_PROVIDER` 支持 `openai-compatible`、`anthropic` 和 `gemini`；
- `MODEL_API_KEY` 是必需的；
- `MODEL_NAME` 是模型名称；
- `MODEL_BASE_URL` 用于覆盖模型服务地址；
- 不要把真实 `aiden_env` 提交到 Git 或分享给其他人；
- API Key 不要写入 Python 源码、README 或工具参数。

## 启动

推荐直接运行项目根目录中的启动脚本：

```powershell
cd D:\AgentProject
.\start_agent.ps1
```

也可以双击 `start_agent.bat` 启动。脚本会自动使用项目虚拟环境中的 Python，不需要手动执行 `Activate.ps1`。

如果 PowerShell 阻止执行本地脚本，可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_agent.ps1
```

手动启动方式如下：

```powershell
cd AgentProject
$env:AGENT_WORKSPACE = "$PWD\agent"
python -m agent.PrimaryAgent
```

也可以将 `AGENT_WORKSPACE` 设置为要让 Agent 操作的其他项目目录。该目录必须是绝对路径。

可选配置：

```powershell
$env:MODEL_PROVIDER = "openai-compatible"
$env:MODEL_NAME = "gpt-4o-mini"
$env:MODEL_BASE_URL = "https://api.openai.com/v1"
$env:AGENT_MAX_ITERATIONS = "10"
$env:AGENT_REQUEST_TIMEOUT = "30"
$env:AGENT_MAX_CONCURRENT = "4"
$env:AGENT_QUEUE_TIMEOUT = "10"
```

`MODEL_BASE_URL` 只能使用不包含账号、密码、查询参数或片段的 HTTP(S) 地址。
`AGENT_MAX_ITERATIONS` 限制单次请求的模型/工具往返次数（1-30），
`AGENT_REQUEST_TIMEOUT` 限制单次模型请求超时时间（5-120 秒）。
`AGENT_MAX_CONCURRENT` 限制当前进程同时运行的模型/工具工作流数量，
默认值为 4；`AGENT_QUEUE_TIMEOUT` 限制请求等待并发槽位的时间，默认值为 10 秒。
超过容量的请求会被拒绝，不会无限堆积。单个 `AgentSession` 同时只能执行一个请求，
避免同一会话的对话上下文和状态机发生竞争。
启动时会提示：用户输入和必要的工具结果可能发送到配置的模型服务。
如果模型请求期间按下 `Ctrl+C`，当前请求会被取消并返回提示，不会显示完整 traceback。

## 当前工具

- `get_weather`：查询城市天气。
- `calculate`：计算基础数学表达式，不使用 `eval`。
- `get_current_time`：查询 IANA 时区的当前时间。
- `get_workspace_info`：返回当前工作区的绝对路径和状态。
- `get_runtime_info`：返回脱敏后的工作区、模型和运行环境信息。
- `read_text_file`：读取工作区内的 UTF-8 文本文件。
- `search_text`：在工作区内搜索文本。
- `inspect_python_file`：分析 Python 文件的导入、函数和类，不执行代码。
- `fetch_webpage`：读取公开网页文本，不访问本机或内网地址。
- `list_files`：列出工作区文件。
- `check_python_syntax`：检查 Python 文件或目录的语法，不执行代码。
- `run_python_tests`：运行受限的 `unittest` 或 `pytest` 测试，不能传入自定义 Shell 命令。
- `detect_secrets`：扫描疑似 API Key、Token、密码和私钥，并对结果脱敏。
- `apply_patch`：应用标准 Git/unified patch；这是唯一会修改文件的工具，必须显式传入 `confirm=true`。
- `list_project_structure`：列出项目目录结构和文件大小。
- `analyze_project`：只读分析项目类型、顶层配置、文件结构和 Python 导入，帮助 Agent 规划编程任务。
- `read_config_file`：读取允许的项目配置文件并自动脱敏密钥。
- `find_symbol`：查找 Python 函数和类定义。
- `detect_dangerous_code`：扫描危险调用和不安全反序列化。
- `run_linter`：运行白名单 linter：`ruff`、`flake8` 或 `pylint`。
- `run_type_checker`：运行白名单类型检查器：`mypy` 或 `pyright`。
- `validate_patch`：校验补丁，不修改文件。
- `preview_patch`：预览补丁统计，不修改文件。
- `rollback_patch`：反向应用已确认的补丁，必须传 `confirm=true`。
- `create_task` / `list_tasks`：管理工作区内的 `.agent_tasks.json` 任务清单。
- `update_task`：更新任务状态和执行备注，支持多步骤任务持续跟踪。
- `get_active_tasks`：读取未完成任务，支持中断后恢复上下文。
- `run_quality_checks`：统一运行语法检查、测试、可选 linter 和类型检查。

## 并发控制

Agent 使用进程级并发闸门模拟高并发系统的“限流/排队”部分：

```text
请求 -> 并发槽位 -> 模型与工具循环 -> 释放槽位
              \-> 超时则拒绝
```

这能保护模型 API、文件工具和当前进程资源，但它不是跨服务器的分布式限流。
多实例部署时需要在网关或 Redis 中实现共享配额；高耗时任务还应进一步接入消息队列。

文件相关工具只允许访问 `AGENT_WORKSPACE` 目录；除明确确认的 `apply_patch` 外均为只读操作。
工具调用只能使用 `Execute_Tool.py` 中注册的白名单函数，不能执行任意 Python、Shell 或删除文件操作。

## 修改闭环

当模型需要修改代码时，Agent 会按以下顺序执行：

1. 生成补丁；
2. 预览并校验补丁；
3. 在终端要求使用者确认；
4. 应用补丁；
5. 自动检查 Python 语法并运行 `unittest`；
6. 如果验证失败，自动用原补丁回滚；
7. 把验证结果返回给模型。

模型不能通过工具参数自行伪造用户确认。测试不存在时会记录为“无测试”，不会因此回滚。

## 状态、审计和执行隔离

- Agent 使用状态机跟踪 `planning`、`analyzing`、`waiting_confirmation`、`applying`、`validating`、`rolling_back`、`completed` 和 `failed`。
- 工具调用和补丁生命周期会记录到 `AGENT_WORKSPACE/.agent_audit.jsonl`，日志会截断并脱敏敏感参数。
- 如果主审计日志无法写入，程序会向标准错误输出告警并累计错误次数；可通过 `AGENT_AUDIT_FALLBACK_PATH` 配置备用 JSONL 日志路径。
- 测试、linter 和类型检查只继承受限环境变量，不会把 `MODEL_API_KEY` 等密钥传给项目代码。
- 当前隔离是进程级限制，不等同于容器或操作系统沙箱；不可信项目代码仍不应在生产环境直接运行。
- 工具权限分为只读和写入两级；补丁工具仍必须经过预览、校验和终端确认。
- 发往模型的用户输入和工具结果会进行长度限制及常见密钥模式脱敏。
