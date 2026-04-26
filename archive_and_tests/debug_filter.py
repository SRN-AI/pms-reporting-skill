from playwright.sync_api import sync_playwright
import json

def test_filtering():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("http://pms.cic.inter/user/login")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill("sunrongnan")
        page.get_by_role("textbox", name="请输入密码").fill("Sunrongnan0808.")
        page.get_by_role("button", name="登 录").click()
        page.wait_for_load_state("networkidle")
        
        url = "http://pms.cic.inter/pms/task/doQueryTaskTreePage2"
        payload = {
            "taskOperList": None,
            "projectNo": "20251103",
            "page": 1,
            "rows": 100,
            "myTask": "1"
        }
        res = context.request.post(url, data=payload, headers={"X-Requested-With": "XMLHttpRequest"}).json()
        
        tasks = res.get("data", {}).get("content", [])
        print(f"Total tasks fetched: {len(tasks)}")
        
        reasons = {"missing_dto": 0, "plan_time_none": 0, "plan_time_zero": 0, "remaining_less_than_8": 0, "valid": 0}
        
        for t in tasks:
            dto = t.get("taskDto")
            if not dto:
                reasons["missing_dto"] += 1
                continue
                
            plan = dto.get("planTime")
            if plan is None:
                reasons["plan_time_none"] += 1
                print(f"Skipped Task {t.get('taskName')} - planTime is None")
                continue
            if plan == 0:
                reasons["plan_time_zero"] += 1
                continue
                
            prog = dto.get("taskProgress") or 0.0
            rem = plan - (plan * (prog / 100.0))
            
            if rem < 8.0:
                reasons["remaining_less_than_8"] += 1
                print(f"Skipped Task {t.get('taskName')} - Plan: {plan}, Prog: {prog}%, Rem: {rem}")
            else:
                reasons["valid"] += 1
                print(f"VALID Task {t.get('taskName')} - Plan: {plan}, Prog: {prog}%, Rem: {rem}")
                
        print("\nSummary of filtering:")
        print(json.dumps(reasons, indent=2))
        
        browser.close()

if __name__ == "__main__":
    test_filtering()
