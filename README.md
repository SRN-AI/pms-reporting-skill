# PMS 自动报工项目 (MCP + Skill 混合架构)

本项目是一个功能完备的 AI Agent 示例，用于自动处理 PMS 系统的报工流程。

## 目录结构

- `mcp_server.py`: 基于 FastMCP 的工具服务器，负责提供查询、提交、撤销等核心工具。
- `pms_client.py`: 封装了 PMS 系统的底层 API，支持 Playwright 自动化。
- `SKILL.md`: 针对 MCP 架构编写的指令文件。
- `pmsSkill/`: [对比版本] 纯指令式 Skill 目录，不使用 MCP，直接通过 bash 调用脚本。
- `docs/`: 项目架构说明及相关文档。

## 快速开始 (MCP 版本)

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境
在根目录下创建 `.env` 文件，填入您的 PMS 账号密码。

### 3. 注册并使用
将 `mcp_server.py` 注册到 Claude Code：
```bash
/mcp add pms-agent python e:/Code/CIC/AI培训/自动报工skill/mcp_server.py
```

## 架构说明
详见 [docs/mcp_vs_skill.html](docs/mcp_vs_skill.html)。
本项目支持两种架构：
1. **MCP + Skill**: 性能最佳，状态保持好，适合高频使用。
2. **Pure Skill (pmsSkill/)**: 零配置，直接调用 CLI 脚本，适合轻量使用。
