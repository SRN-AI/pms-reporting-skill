---
name: pms-work-reporting
description: "通过运行本地 Python 脚本自动处理 PMS 系统的报工流程。适用于需要查询任务详情、自动润色日报文案并提交 8 小时工时记录的场景。支持自动处理登录态保持、任务关键字匹配以及报工结果反馈。"
allowed-tools:
  - bash
---

# PMS 自动报工助手 (Standard Skill)

## 概览 (Overview)

本 Skill 旨在帮助开发人员自动化处理繁琐的 PMS 报工任务。它通过执行本地 Python 脚本与 PMS 系统进行交互，支持从口语化的工作描述自动生成专业的报工记录。

## 快速参考 (Quick Reference)

| 任务 | 脚本指令 | 说明 |
| :--- | :--- | :--- |
| **查询任务** | `python pmsSkill/scripts/pms_client.py query` | 列出所有可用任务 |
| **搜索任务** | `python pmsSkill/scripts/pms_client.py query --keyword "支付"` | 按关键词搜索任务 |
| **提交报工** | `python pmsSkill/scripts/pms_client.py submit ...` | 拆分子任务并汇报进度 |
| **撤销报工** | `python pmsSkill/scripts/pms_client.py revoke --task-no "123"` | 删除错误的报工记录 |

---

## 工作流指令 (Workflow Instructions)

当用户提出报工请求时，请严格按照以下步骤操作：

### 步骤 1：获取任务上下文
首先，必须调用查询工具获取准确的任务 ID 和项目编号。
- **操作**：运行 `python pmsSkill/scripts/pms_client.py query`（如果用户提到了具体业务，加上 `--keyword` 参数）。
- **注意**：工具会返回任务的“剩余安全工时”，请确保所选任务剩余工时 >= 8 小时。

### 步骤 2：生成报工内容
基于用户的原始描述，生成以下两个字段：
1. **汇总标题** (`task_name`)：用 10-15 字简要概括今日核心工作（如：“支付系统接口联调与测试”）。
2. **专业详情** (`task_desc`)：对工作内容进行职场化润色，描述具体成果和技术点。

### 步骤 3：正式提交
- **操作**：运行 `python pmsSkill/scripts/pms_client.py submit`，传入项目号、父任务 ID、标题、详情及日期。
- **日期处理**：如果用户说“昨天”，请根据当前系统日期（查询结果中会显示）计算出具体的 `YYYY-MM-DD` 格式。

### 步骤 4：反馈结果
报工成功后，以“老板”称呼用户并汇报成果：
> 报告老板，报工已完成！
> **项目**：[项目名称]
> **标题**：[汇总标题]
> **详情**：[专业详情]
> **状态**：已填报 8 小时，进度 100%。

---

## 关键规则 (Critical Rules)

- **优先查询**：禁止在没有查询到最新 `task_id` 的情况下猜测 ID 进行提交。
- **会话持久化**：脚本会自动处理 `storage_state.json`，如果运行失败并提示登录过期，请尝试重新运行以触发自动登录。
- **日期准确性**：务必确认填报日期。默认不传日期代表今天，跨天报工必须传准确的日期字符串。
- **工时校验**：只对返回列表中存在的任务进行报工，不要尝试给工时已用完的任务报工。

## 依赖说明 (Dependencies)

- **Python 3.8+**
- **Playwright**: 核心自动化驱动。
- **python-dotenv**: 环境配置管理。
