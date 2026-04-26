import json
import logging
import asyncio
import os
import io
import sys
from datetime import datetime
from typing import List, Dict, Optional, Any

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class PMSClient:
    """
    PMS 内部项目管理系统的 Python SDK 封装。
    负责自动处理 Playwright 的登录认证，并提供面向对象的业务操作接口。
    """
    def __init__(self, username: str, password: str, headless: bool = True):
        self.username = username
        self.password = password
        self.headless = headless
        
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 缓存数据
        self._oper_code = None
        
    async def start(self):
        """启动浏览器并尝试加载会话"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            
            # 尝试从本地加载已保存的登录态
            storage_path = "storage_state.json"
            if os.path.exists(storage_path):
                logger.info("检测到本地会话文件，尝试直接恢复登录态...")
                self.context = await self.browser.new_context(storage_state=storage_path)
            else:
                self.context = await self.browser.new_context()
                
            self.page = await self.context.new_page()
            
            # 检查是否真的已经登录（访问一个需要登录的页面试试）
            # 如果没加载成功或文件失效，执行登录逻辑
            try:
                await self.page.goto("http://pms.cic.inter/pms/project/projectList", timeout=5000)
                if "login" in self.page.url.lower() or "<html" not in await self.page.content():
                    await self._login()
            except:
                await self._login()

            
    async def _login(self):
        """执行内部登录操作并保存会话"""
        logger.info(f"正在尝试使用账号 {self.username} 登录 PMS 系统...")
        await self.page.goto("http://pms.cic.inter/user/login")
        await self.page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(self.username)
        await self.page.get_by_role("textbox", name="请输入密码").fill(self.password)
        await self.page.get_by_role("button", name="登 录").click()
        await self.page.wait_for_load_state("networkidle")
        
        # 保存登录态到本地
        await self.context.storage_state(path="storage_state.json")
        logger.info("登录成功，会话已保存到 storage_state.json。")

        
    async def close(self):
        """关闭浏览器释放资源"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def _post_json(self, url: str, payload: dict, retry: bool = True) -> dict:
        """发送 JSON 请求的通用方法（带有自动重登录机制）"""
        if not self.context:
            raise RuntimeError("请先调用 start() 方法初始化会话。")
            
        response = await self.context.request.post(
            url, 
            data=json.dumps(payload),
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json"
            }
        )
        
        text_body = await response.text()
        
        # 判断是否因为 Cookie 失效被重定向到了登录页 (通常返回 HTML 而不是 JSON)
        is_expired = False
        if not response.ok and response.status in [401, 403]:
            is_expired = True
        elif "<html" in text_body.lower() or "login" in response.url.lower():
            is_expired = True
            
        if is_expired:
            if retry:
                logger.warning("检测到 PMS 会话可能已过期，触发自动重新登录...")
                await self._login()
                return await self._post_json(url, payload, retry=False)
            else:
                raise Exception(f"会话已过期，且自动重新登录失败！HTTP: {response.status}")
            
        try:
            return await response.json()
        except Exception as e:
            # 如果解析 JSON 失败，十有八九是因为后台返回了拦截页或登录页
            if retry:
                logger.warning(f"接口返回非 JSON 数据，疑似掉线拦截，尝试自动重新登录...")
                await self._login()
                return await self._post_json(url, payload, retry=False)
            raise Exception(f"解析 JSON 失败: {e}\n响应内容片段: {text_body[:500]}")

    async def get_active_projects(self) -> List[Dict[str, Any]]:
        """获取当前状态为'项目已启动'的项目列表"""
        logger.info("正在查询可用项目列表...")
        url = "http://pms.cic.inter/pms/project/projectList"
        payload = {
            "pageNo": 1,
            "pageSize": 20,
            "processStateList": [],
            "projType": [],
            "busiDepartTypeList": [],
            "dimension": "2",
            "dimensionType": "3"
        }
        data = await self._post_json(url, payload)
        
        if data.get("success") and "data" in data and "content" in data["data"]:
            projects = data["data"]["content"]
            active_projects = [p for p in projects if p.get("projectStateName") == "项目已启动"]
            logger.info(f"成功获取到 {len(active_projects)} 个活动项目。")
            return active_projects
        return []

    async def get_my_oper_code(self, project_no: str, task_no: str) -> str:
        """
        根据当前登录的 userName 获取数字型的 operCode。
        只需成功获取一次即可缓存。
        """
        if self._oper_code:
            return self._oper_code
            
        logger.info(f"正在查询项目 {project_no} 下人员列表，以获取 {self.username} 的工号...")
        url = "http://pms.cic.inter/pms/task/loadProjectOper"
        payload = {
            "projectNo": project_no,
            "taskNo": task_no
        }
        data = await self._post_json(url, payload)
        
        if data.get("successed") and "returnObject" in data:
            members = data["returnObject"]
            for member in members:
                if member.get("userName") == self.username:
                    self._oper_code = member.get("operCode")
                    logger.info(f"成功匹配到工号: {self._oper_code}")
                    return self._oper_code
        raise Exception(f"未能在项目 {project_no} 中找到账号 {self.username} 的人员信息。")

    async def get_tasks(self, project_no: str) -> List[Dict[str, Any]]:
        """
        查询指定项目下的任务，并进行业务过滤：
        只返回 剩余可用工时 = planTime - (planTime * taskProgress / 100) > 8 的任务。
        """
        logger.info(f"正在查询项目 [{project_no}] 下的任务...")
        url = "http://pms.cic.inter/pms/task/doQueryTaskTreePage2"
        payload = {
            "taskOperList": None,
            "projectNo": project_no,
            "page": 1,
            "rows": 100,  # 调大一点防止分页遗漏
            "state": "0", # 只查询进行中的任务
            "myTask": "1"
        }
        data = await self._post_json(url, payload)
        
        valid_tasks = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if data.get("success") and "data" in data and "content" in data["data"]:
            tasks = data["data"]["content"]
            for t in tasks:
                dto = t.get("taskDto", {})
                plan_time = dto.get("planTime")
                progress = dto.get("taskProgress")
                
                # 容错处理
                if plan_time is None: continue
                progress = progress or 0.0
                
                # 校验到期时间：计划结束日期必须大于等于今天
                end_date_str = dto.get("endDate", "")
                if end_date_str < today_str:
                    continue
                
                # 核心业务校验：过滤可用工时不足 8 小时的任务
                remaining_hours = plan_time - (plan_time * (progress / 100.0))
                if remaining_hours >= 8.0:
                    valid_tasks.append({
                        "id": t.get("id"),
                        "taskName": t.get("taskName"),
                        "projectNo": project_no,
                        "planTime": plan_time,
                        "taskProgress": progress,
                        "remainingHours": round(remaining_hours, 2)
                    })
            logger.info(f"项目 [{project_no}] 下共有 {len(tasks)} 个任务，可用工时>=8的有效任务有 {len(valid_tasks)} 个。")
        return valid_tasks

    async def divide_task(self, project_no: str, parent_task_id: str, 
                    task_name: str, task_desc: str, 
                    task_priority: str = "02", hours: float = 8.0,
                    date: Optional[str] = None) -> str:
        """
        核心报工方法：从父任务中切分出一个子任务。
        """
        # 自动获取操作人工号
        oper_code = await self.get_my_oper_code(project_no, parent_task_id)

        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"开始填报工时(拆分子任务): '{task_name}', 耗时: {hours}H")
        url = "http://pms.cic.inter/pms/task/doDivideTask"
        payload = {
            "taskName": task_name,
            "taskType": "type005",           # 默认：开发
            "taskPriority": task_priority,   # 01 重要，02 一般
            "beginDate": target_date,
            "endDate": target_date,
            "planTime": hours,
            "operList": [oper_code],
            "fpaInfoIdList": [],
            "fpaPonits": "0.00",
            "fileNo": "",
            "taskDesc": task_desc,
            "taskMatter": "matter002",       # 默认：业务需求
            "projectNo": project_no,
            "fatherTask": parent_task_id
        }
        
        data = await self._post_json(url, payload)
        if data.get("success") and "returnObject" in data:
            new_task_no = data["returnObject"].get("taskNo")
            logger.info(f"报工(切分子任务)成功！新子任务ID: {new_task_no}")
            return new_task_no
        else:
            logger.error(f"报工失败: {data}")
            return ""

    async def delete_task(self, task_no: str) -> bool:
        """
        容错接口：删除拆分错误的子任务。
        """
        logger.info(f"尝试删除/撤销任务: {task_no}")
        url = "http://pms.cic.inter/pms/task/doDelTask"
        payload = {
            "taskNoList": [task_no]
        }
        data = await self._post_json(url, payload)
        if data.get("success") or data.get("successed"):
            logger.info("撤销任务成功！")
            return True
        else:
            logger.error(f"撤销失败，完整响应: {data}")
            return False

    async def report_task_progress(self, task_no: str, task_desc: str, progress: int = 100, date: Optional[str] = None) -> bool:
        """
        报工的最后一步：填写子任务的进度 and 详细日志。
        """
        if date:
            # 兼容 YYYY-MM-DD 格式，转为 YYYY-MM-DD 00:00:00
            target_date = f"{date} 00:00:00"
        else:
            target_date = datetime.now().strftime("%Y-%m-%d 00:00:00")
        
        logger.info(f"提交实际报工日志: 任务 {task_no}, 进度 {progress}%")
        url = "http://pms.cic.inter/pms/task/doAddLogProgress"
        payload = {
            "taskDate": target_date,
            "taskProgress": progress,
            "percent": 1,
            "content": task_desc,
            "taskNo": task_no
        }
        
        data = await self._post_json(url, payload)
        if data.get("success"):
            logger.info("报工日志提交成功！")
            return True
        else:
            logger.error(f"报工日志提交失败: {data}")
            return False

# 命令行入口 (CLI)
if __name__ == "__main__":
    import argparse
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="PMS 报工助手命令行工具")
    subparsers = parser.add_subparsers(dest="action", help="执行的操作")
    
    # 查询任务
    query_parser = subparsers.add_parser("query", help="查询可用任务")
    query_parser.add_argument("--keyword", type=str, default="", help="过滤关键字")
    
    # 提交报工
    submit_parser = subparsers.add_parser("submit", help="提交报工")
    submit_parser.add_argument("--project-no", required=True)
    submit_parser.add_argument("--task-id", required=True)
    submit_parser.add_argument("--name", required=True, help="子任务名称")
    submit_parser.add_argument("--desc", required=True, help="详细日志")
    submit_parser.add_argument("--date", default="", help="日期 YYYY-MM-DD")
    submit_parser.add_argument("--priority", default="02")
    
    # 撤销任务
    revoke_parser = subparsers.add_parser("revoke", help="撤销任务")
    revoke_parser.add_argument("--task-no", required=True)
    
    args = parser.parse_args()
    
    USERNAME = os.getenv("PMS_USERNAME")
    PASSWORD = os.getenv("PMS_PASSWORD")
    
    if not USERNAME or not PASSWORD:
        print("错误: 未配置 PMS_USERNAME 或 PMS_PASSWORD 环境变量。")
        sys.exit(1)
        
    client = PMSClient(username=USERNAME, password=PASSWORD, headless=True)
    
    async def main():
        try:
            await client.start()
            if args.action == "query":
                projects = await client.get_active_projects()
                all_tasks = []
                for p in projects:
                    tasks = await client.get_tasks(p["projectNo"])
                    # 给每个任务打上项目名称的标签
                    for t in tasks:
                        t["projectName"] = p.get("projectName", "未知项目")
                    all_tasks.extend(tasks)
                
                filtered = [t for t in all_tasks if args.keyword.lower() in t["taskName"].lower()] if args.keyword else all_tasks
                
                from datetime import datetime
                print(f"【当前系统日期: {datetime.now().strftime('%Y-%m-%d')}】")
                if not filtered:
                    print(f"未找到匹配 '{args.keyword}' 的可用任务。")
                else:
                    for i, t in enumerate(filtered, 1):
                        print(f"候选 {i}: 任务名称: 【{t['taskName']}】, 任务ID: {t['id']}, 所属项目: {t['projectName']} ({t['projectNo']}), 剩余安全工时: {t['remainingHours']}H")

            
            elif args.action == "submit":
                new_task_no = await client.divide_task(args.project_no, args.task_id, args.name, args.desc, args.priority, 8.0, args.date)
                if new_task_no:
                    success = await client.report_task_progress(new_task_no, args.desc, 100, args.date)
                    if success:
                        print(f"SUCCESS: 报工成功! 子任务ID: {new_task_no}")
                    else:
                        print(f"PARTIAL: 子任务已创建({new_task_no})，但进度更新失败。")
                else:
                    print("ERROR: 无法拆分子任务。")
                    
            elif args.action == "revoke":
                if await client.delete_task(args.task_no):
                    print(f"SUCCESS: 任务 {args.task_no} 已成功撤销。")
                else:
                    print("ERROR: 撤销失败。")
            else:
                parser.print_help()
        finally:
            await client.close()

    asyncio.run(main())

