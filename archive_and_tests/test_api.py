from playwright.sync_api import sync_playwright
import json

def main():
    username = "sunrongnan"
    password = "Sunrongnan0808."

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("正在登录系统...")
        page.goto("http://pms.cic.inter/user/login")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)
        page.get_by_role("button", name="登 录").click()
        page.wait_for_load_state("networkidle")
        
        # 1. 获取活动项目列表
        print("\n--- 步骤 1：获取可用项目列表 ---")
        project_api_url = "http://pms.cic.inter/pms/project/projectList"
        project_payload = {
            "pageNo": 1,
            "pageSize": 20,
            "processStateList": [],
            "projType": [],
            "busiDepartTypeList": [],
            "dimension": "2",
            "dimensionType": "3"
        }
        
        active_projects = []
        try:
            response = context.request.post(
                project_api_url, 
                data=project_payload,
                headers={"X-Requested-With": "XMLHttpRequest"}
            )
            if response.ok:
                data = response.json()
                if data.get("success") and "data" in data and "content" in data["data"]:
                    projects = data["data"]["content"]
                    # 过滤出 "项目已启动" 的项目
                    active_projects = [p for p in projects if p.get("projectStateName") == "项目已启动"]
                    print(f"找到 {len(active_projects)} 个已启动的项目：")
                    for p in active_projects:
                        print(f"  - [{p.get('projectNo')}] {p.get('projectName')}")
            else:
                print(f"获取项目列表失败: {response.status}")
        except Exception as e:
            print(f"获取项目异常: {e}")

        # 2. 针对每个活跃项目，获取其下的任务
        print("\n--- 步骤 2：遍历活跃项目，查询具体任务 ---")
        task_api_url = "http://pms.cic.inter/pms/task/doQueryTaskTreePage2"
        
        for proj in active_projects:
            proj_no = proj.get("projectNo")
            proj_name = proj.get("projectName")
            print(f"\n>> 正在查询项目 [{proj_name}] 的任务...")
            
            task_payload = {
                "taskOperList": None,
                "projectNo": proj_no,
                "page": 1,
                "rows": 10,
                "myTask": "1"  # "1" 表示只查我的任务
            }
            
            try:
                task_res = context.request.post(
                    task_api_url, 
                    data=task_payload,
                    headers={"X-Requested-With": "XMLHttpRequest"}
                )
                if task_res.ok:
                    task_data = task_res.json()
                    if task_data.get("success") and "data" in task_data and "content" in task_data["data"]:
                        tasks = task_data["data"]["content"]
                        print(f"   该项目下找到 {task_data['data']['total']} 个任务。第一页数据：")
                        for t in tasks:
                            print(f"     - 任务名称: {t.get('taskName')} (ID: {t.get('id')})")
            except Exception as e:
                print(f"   查询任务异常: {e}")

        browser.close()

if __name__ == "__main__":
    main()
