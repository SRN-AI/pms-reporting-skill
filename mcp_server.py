import os
import asyncio
import logging
from typing import List, Dict, Any, Optional

# 使用官方的 MCP Python SDK (FastMCP)
from mcp.server.fastmcp import FastMCP

from pms_client import PMSClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# 创建 FastMCP 实例
mcp = FastMCP("PMS_Agent_Skill")

# 初始化底层 PMS 客户端 
USERNAME = os.getenv("PMS_USERNAME")
PASSWORD = os.getenv("PMS_PASSWORD")

if not USERNAME or not PASSWORD:
    logger.warning("未检测到 PMS_USERNAME 或 PMS_PASSWORD 环境变量，请确保已配置。")

client = PMSClient(username=USERNAME, password=PASSWORD, headless=True)


@mcp.tool()
async def query_available_tasks(keyword: str = "") -> str:
    """
    【必须优先调用】当用户想知道自己有什么任务可以报工时，或者需要根据业务描述查找对应的任务时调用此工具。
    该工具会自动遍历系统内所有活跃项目，并返回符合报工条件（剩余可用工时 >= 8小时）的任务列表。
    
    Args:
        keyword: 选填。用户的业务名词（如'临分分入'）。如果有，会优先返回匹配的任务；如果不填则返回所有可用任务。
        
    Returns:
        一段格式化的字符串文本，包含 任务ID、项目编号 和 剩余工时 等核心信息。
    """
    logger.info(f"收到大模型任务查询请求，关键字: '{keyword}'")
    try:
        # 如果尚未启动浏览器会话，则先启动
        if not client.context:
            await client.start()
        
        projects = await client.get_active_projects()
        all_tasks = []
        for p in projects:
            p_no = p["projectNo"]
            tasks = await client.get_tasks(p_no)
            # 给任务打上项目名称标签
            for t in tasks:
                t["projectName"] = p.get("projectName", "未知项目")
            all_tasks.extend(tasks)
            
        # 关键字过滤
        if keyword:
            filtered = [t for t in all_tasks if keyword.lower() in t["taskName"].lower()]
        else:
            filtered = all_tasks
            
        # 业务防错：让大模型知道找不到任务
        if not filtered:
            return f"没有找到符合关键字 '{keyword}' 且工时充足的活跃任务。请您先向用户追问确认任务全称，或确认其任务是否已被他人报满额度。"
            
        # 格式化输出，帮助大模型提取字段
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        res = [f"【当前系统日期: {today}】", "找到以下可报工的安全任务候选："]
        for i, t in enumerate(filtered, 1):
            res.append(f"候选 {i}: 任务名称: 【{t['taskName']}】, 任务ID: {t['id']}, 所属项目: {t['projectName']} ({t['projectNo']}), 剩余安全工时: {t['remainingHours']}H")

        
        return "\n".join(res)
    except Exception as e:
        logger.error(f"查询任务异常: {e}")
        return f"查询任务系统异常: {str(e)}"


@mcp.tool()
async def submit_daily_timesheet(project_no: str, task_id: str, task_name: str, task_desc: str, date: str, priority: str = "02") -> str:
    """
    【重要】如果你要报非今天的工（如：昨天、前天），请务必根据当前系统日期计算出 YYYY-MM-DD 格式并通过 date 参数传入。
    
    执行真实的报工操作！将用户的口语化描述提取为汇总标题，并润色为详细文案后，调用此工具向系统填报 8 小时的工时。
    警告：必须先调用 query_available_tasks 获取准确的 project_no 和 task_id 才能调用此工具！
    
    Args:
        project_no: 所属项目编号（例如：20251102，由 query_available_tasks 获得）
        task_id: 父任务的 ID (例如: 1776222782630，由 query_available_tasks 获得)
        task_name: 必填。报工任务的简要汇总（如：支付大屏联调开发）。
        task_desc: 必填。这是经过你润色优化后的专业报工详情（即当天的具体工作成果，如：完成支付大屏前端与后端的接口联调开发，并修复相关缺陷）。
        priority: 任务优先级。01 代表紧急重要，02 代表常规一般。默认 02。如果用户强调了特别紧急，请传 01。
        date: 报工日期（格式：YYYY-MM-DD）。【重要】如果用户提到了“昨天”、“前天”、“周三”等相对时间，请你先根据当前系统时间计算出具体的日期字符串再传入。如果用户未明确提及日期，则不传，系统默认为今天。
        
    Returns:
        报工结果的字符串文本。
    """
    logger.info(f"收到大模型报工请求: project_no={project_no}, task_id={task_id}, date={date}, name={task_name}")
    try:
        if not client.context:
            await client.start()
            
        # 步骤 1: 拆分任务 (报坑位)
        new_task_no = await client.divide_task(
            project_no=project_no,
            parent_task_id=task_id,
            task_name=task_name,
            task_desc=task_desc,
            task_priority=priority,
            hours=8.0,
            date=date
        )
        
        if not new_task_no:
            return "报工失败(阶段1)：无法拆分子任务。可能是因为父任务的工时在刚才被人占用了，或者权限不足。"
            
        # 步骤 2: 汇报进度 100% (填坑位)
        success = await client.report_task_progress(
            task_no=new_task_no,
            task_desc=task_desc,
            progress=100,
            date=date
        )
        
        if success:
            return (f"报工完全成功！日期: {date or '今天'}。已在项目 {project_no} 的父任务 {task_id} 下，"
                    f"成功生成了名为【{task_name}】的子任务 (ID: {new_task_no})，并将进度设为 100%。"
                    f"\n【重要指令】请务必在回答中明确告诉用户：你已经成功为他报了哪个任务（原话描述），耗时 8 小时。")
        else:
            return f"报工存在瑕疵(阶段2)：子任务 {new_task_no} 已创建，但汇报 100% 进度时失败。请尝试调用 revoke_task 撤销刚才的创建以保持数据干净。"
            
    except Exception as e:
        logger.error(f"报工发生异常: {e}")
        return f"报工发生系统异常: {str(e)}"


@mcp.tool()
async def revoke_task(task_no: str) -> str:
    """
    撤销工具（极品后悔药）。如果报工(submit_daily_timesheet)时出现错误，或者用户对刚才的报工内容不满意，
    可以调用此工具删除对应的子任务。
    
    Args:
        task_no: 需要删除的子任务ID (由 submit_daily_timesheet 返回)
    """
    logger.info(f"收到大模型撤销任务请求: task_no={task_no}")
    try:
        if not client.context:
            await client.start()
        success = await client.delete_task(task_no)
        if success:
            return f"任务 {task_no} 撤销成功！数据已回滚。"
        else:
            return f"任务 {task_no} 撤销失败，请重试或通知管理员。"
    except Exception as e:
        logger.error(f"撤销发生异常: {e}")
        return f"撤销发生系统异常: {str(e)}"

if __name__ == "__main__":
    # 启动 MCP 服务器
    mcp.run()
