# Agent

这是一个带安全工具白名单的 DeepSeek 命令行 Agent。

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
liuzhengzheng
```

更推荐使用 `pipx` 安装，使 Agent 和其他 Python 工具保持隔离：

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
pipx install D:\AgentProject
liuzhengzheng
```

更新代码后重新安装：

```powershell
pipx install --force D:\AgentProject
```

首次使用时，在项目目录或用户配置位置准备 `.env`，至少配置：

```env
MODEL_PROVIDER=openai-compatible
MODEL_API_KEY=你的模型 API Key
MODEL_NAME=deepseek-chat
MODEL_BASE_URL=https://api.deepseek.com
```

不要把包含真实 API Key 的 `.env` 打包、提交或发送给其他人。分发时应提供 `.env.example`，让每位使用者自行配置自己的 Key。

交互过程中可使用 `/workspace`、`/status`、`/tasks`、`/clear`、`/help` 和 `/quit` 快捷命令。

## 配置模型 API

项目不会内置或上传模型 API Key。使用者需要配置所选模型服务的 API。

可以复制配置模板：

```powershell
Copy-Item agent\.env.example agent\.env
```

然后打开 `.env`，填入自己的值。程序启动时会自动读取 `agent/.env`；PowerShell 用户也可以直接设置环境变量：

```powershell
$env:MODEL_PROVIDER = "openai-compatible"
$env:MODEL_API_KEY = "你的模型 API Key"
$env:MODEL_NAME = "gpt-4o-mini"
$env:MODEL_BASE_URL = "https://api.openai.com/v1"
```

其中：

- `MODEL_PROVIDER` 支持 `openai-compatible`、`anthropic` 和 `gemini`；
- `MODEL_API_KEY` 是必需的；
- `MODEL_NAME` 是模型名称；
- `MODEL_BASE_URL` 用于覆盖模型服务地址；
- 不要把真实 `.env` 提交到 Git 或分享给其他人；
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
```

`MODEL_BASE_URL` 只能使用不包含账号、密码、查询参数或片段的 HTTP(S) 地址。
`AGENT_MAX_ITERATIONS` 限制单次请求的模型/工具往返次数（1-30），
`AGENT_REQUEST_TIMEOUT` 限制单次模型请求超时时间（5-120 秒）。
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
