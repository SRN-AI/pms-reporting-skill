import logging
import re
from mcp_server import query_available_tasks, submit_daily_timesheet, revoke_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WorkflowTest")

def main():
    logger.info("====== 开始模拟大模型工作流测试 ======")
    
    # 模拟步骤1：大模型接到用户命令 "帮我查查今天有什么任务可以报工"
    logger.info(">> 步骤1：查询可用任务...")
    tasks_text = query_available_tasks()
    print("\n[AI 收到查询结果]:")
    print(tasks_text)
    
    # 解析输出结果，挑一个安全的任务做测试
    if "候选" not in tasks_text:
        print("未找到任务，停止测试。")
        return
        
    # 简单用正则从返回的纯文本中提取第一个任务的信息
    match = re.search(r"任务ID: (\d+), 所属项目: (\d+)", tasks_text)
    if not match:
        print("解析任务文本失败。")
        return
        
    task_id = match.group(1)
    project_no = match.group(2)
    
    print(f"\n[AI 解析出] 目标 Project: {project_no}, 目标 Task: {task_id}")
    
    # 模拟步骤2：大模型自动调用报工接口
    logger.info(">> 步骤2：执行报工操作 (生成子任务并汇报进度)...")
    report_res = submit_daily_timesheet(
        project_no=project_no,
        task_id=task_id,
        task_desc="【AI 自动化测试】工作流联调，请忽略",
        priority="02"
    )
    print("\n[AI 收到报工结果]:")
    print(report_res)
    
    # 模拟步骤3：大模型调用撤销接口 (因为这是测试，必须清理现场)
    if "报工完全成功" in report_res:
        logger.info(">> 步骤3：测试完成，开始清理现场 (撤销刚才建的测试任务)...")
        # 从报工成功文本中提取新子任务 ID
        # 返回文案是: "报工完全成功！已成功挂载子任务 ID: 1777041587555，并将进度设为 100%。..."
        match_new_task = re.search(r"ID: (\d+)", report_res)
        if match_new_task:
            new_task_id = match_new_task.group(1)
            revoke_res = revoke_task(new_task_id)
            print("\n[AI 收到撤销结果]:")
            print(revoke_res)
        else:
            print("未能提取新任务 ID 进行撤销。")
            
    logger.info("====== 模拟大模型工作流测试结束 ======")

if __name__ == "__main__":
    main()
