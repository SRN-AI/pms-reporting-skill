from playwright.sync_api import sync_playwright
import time

def main():
    username = "sunrongnan"
    password = "Sunrongnan0808"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("1. 正在登录门户...")
        page.goto("http://pms.cic.inter/user/login")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)
        page.get_by_role("button", name="登 录").click()
        
        # 等待跳转完成
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        print("2. 访问业务系统首页，触发会话初始化 (非常关键！)...")
        # 很多微服务/SSO架构中，仅登录网关不够，需要访问具体子系统(如slave)以在子系统中建立Session
        page.goto("http://pms.cic.inter/slave/project/project/projectQuery", timeout=15000)
        page.wait_for_load_state("load")
        time.sleep(2) # 等待各种前端请求完成

        print("3. 尝试在业务页面上下文中发起 Fetch 请求...")
        # 直接使用页面内置的 fetch 方法
        script = """
        async () => {
            const url = '/pms/task/doQueryTaskTreePage2';
            const payload = {
                "taskOperList": null,
                "projectNo": "20251102",
                "page": 1,
                "rows": 10,
                "myTask": "1"
            };
            
            try {
                // 默认 JSON 格式尝试
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/plain, */*',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(payload)
                });
                return { status: res.status, text: await res.text() };
            } catch (e) {
                return { error: e.toString() };
            }
        }
        """
        result = page.evaluate(script)
        print(f"JSON 模式评估结果: {result}")
        
        # 为了防万一，同时也测试一下 context.request.post (看独立发起是否也可以)
        print("\n--- 测试独立的 HTTP Context 发送 ---")
        api_url = "http://pms.cic.inter/pms/task/doQueryTaskTreePage2"
        payload = {
            "taskOperList": None,
            "projectNo": "20251102",
            "page": 1,
            "rows": 10,
            "myTask": "1"
        }
        response = context.request.post(api_url, data=payload, headers={'X-Requested-With': 'XMLHttpRequest'})
        print(f"独立请求 HTTP 状态码: {response.status}")
        print(f"独立请求 响应片段: {response.text()[:200]}")

        browser.close()

if __name__ == "__main__":
    main()
