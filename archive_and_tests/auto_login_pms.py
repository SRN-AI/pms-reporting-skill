from playwright.sync_api import sync_playwright
import json
import os

def main():
    # 推荐：在实际生产中，不要将密码硬编码在代码里，而是通过环境变量或配置文件读取
    username = "sunrongnan"
    password = "Sunrongnan0808"

    with sync_playwright() as p:
        # 1. 启动浏览器 (headless=False 可以让你在运行的时候看到浏览器界面，方便调试)
        # 调试成功后，可以将其改为 headless=True 进行后台静默运行
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("正在访问登录页面...")
        page.goto("http://pms.cic.inter/user/login")

        # 2. 定位并输入账号密码
        print("正在输入凭证...")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)

        # 3. 点击登录按钮
        print("正在点击登录...")
        page.get_by_role("button", name="登 录").click()

        # 4. 等待页面加载完成 (等待网络空闲，确保登录跳转和接口请求完毕)
        print("等待登录成功并跳转...")
        # 可以根据登录成功后一定会出现的某个元素来等待，例如：
        # page.wait_for_selector('text="欢迎"') 
        # 这里我们使用通用的等待网络空闲
        page.wait_for_load_state("networkidle")

        # 5. 获取缓存信息 (Cookies & LocalStorage & SessionStorage)
        print("\n--- 获取缓存信息 ---")
        
        # 获取 Cookies
        cookies = context.cookies()
        print(f"成功获取到 {len(cookies)} 个 Cookies。")
        # for cookie in cookies:
        #     print(f"Cookie: {cookie['name']} = {cookie['value']}")

        # 获取 LocalStorage (很多现代前端框架如 Vue/React 会把 Token 存在这里)
        local_storage_str = page.evaluate("() => JSON.stringify(window.localStorage)")
        local_storage = json.loads(local_storage_str)
        print(f"成功获取 LocalStorage，包含 {len(local_storage.keys())} 个键。")
        
        # 尝试寻找常见的 token 字段
        token = local_storage.get("token") or local_storage.get("Authorization") or local_storage.get("Admin-Token")
        if token:
            print(f"在 LocalStorage 中发现疑似 Token: {token[:15]}...")

        # 6. 自动化 HTTP 操作
        print("\n--- 准备发送自动化 HTTP 请求 ---")
        # Playwright 的 APIRequestContext (context.request) 会自动携带我们在上面登录后获取到的 Cookies
        
        # 【请在此处替换为你实际需要调用的业务 API 接口地址，比如自动报工的提交接口】
        api_url = "http://pms.cic.inter/api/some/target_endpoint" 
        
        # 如果接口需要从 localStorage 中提取出的特定 Token 放在 Headers 中，可以在这里添加：
        custom_headers = {
            "Accept": "application/json, text/plain, */*"
        }
        if token:
            custom_headers["Authorization"] = f"Bearer {token}" # 根据实际接口要求的格式修改
            # 或者 custom_headers["token"] = token

        print(f"正在请求 API: {api_url}")
        
        try:
            # 下面是一个发送 GET/POST 请求的示例，请根据实际情况取消注释并修改
            '''
            # GET 请求示例
            response = context.request.get(api_url, headers=custom_headers)
            
            # POST 请求示例 (比如提交报工表单)
            # payload = {"project_id": 123, "hours": 8, "date": "2026-04-24"}
            # response = context.request.post(api_url, headers=custom_headers, data=payload)
            
            print(f"API 响应状态码: {response.status}")
            if response.ok:
                print("API 响应数据:", response.json())
            else:
                print("请求失败:", response.text())
            '''
            print("HTTP 请求代码已准备好，请根据实际接口调整参数后取消注释执行。")
        except Exception as e:
            print(f"请求发生异常: {e}")

        # 任务结束，关闭浏览器
        browser.close()

if __name__ == "__main__":
    main()
