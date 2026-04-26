# PMS 自动报工 Skill

这是一个标准的 Claude Code Skill，旨在帮助开发人员自动化处理 PMS 系统的报工流程。

## 功能特性

- **自动查询任务**：根据关键字自动匹配当前活跃且剩余工时充足的 PMS 任务。
- **智能文案润色**：将口语化的工作描述自动转化为专业的汇总标题和详细日志。
- **一键填报**：自动完成子任务拆分和 100% 进度汇报。
- **错误撤销**：支持一键撤销（删除）错误的报工记录。

## 目录结构

- `SKILL.md`: Skill 的核心指令和元数据。
- `mcp_server.py`: 基于 FastMCP 的工具服务器实现。
- `pms_client.py`: 封装了 PMS 系统的底层 API（基于 Playwright）。
- `requirements.txt`: 项目依赖列表。

## 安装与配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量
请在项目目录下创建 `.env` 文件（可参考 `.env.example`）：
- `PMS_USERNAME`: 您的 PMS 用户名
- `PMS_PASSWORD`: 您的 PMS 密码

### 3. 在 Claude Code 中使用
这是一个 **Pure Skill**，无需注册 MCP。Claude 会自动识别项目根目录下的 `SKILL.md` 文件。

如果您想在其他项目中使用，只需将 `SKILL.md` 放到该项目的 `.claude/skills/` 目录下，并确保路径正确。

## 使用说明
直接告诉 Claude 您今天做了什么，例如：
> “我今天完成了支付大屏的接口联调，帮我报个工。”

Claude 会通过 `bash` 调用 `pms_client.py` 脚本，自动处理登录态、查询任务、润色文案并完成提交。
首次运行会自动登录并生成 `storage_state.json` 以保持后续会话。

