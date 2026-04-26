from playwright.sync_api import sync_playwright

def handle_request(request):
    # 只监听 AJAX 数据请求
    if request.resource_type in ["xhr", "fetch"]:
        # 过滤掉一些无关紧要的请求，重点看业务接口
        if 'pms-gateway' in request.url or 'pms/task' in request.url:
            print(f"\n[Frontend API Request] {request.url}")
            # 打印请求头，看看有没有特殊的 Authorization 字段
            headers = request.headers
            for k, v in headers.items():
                if k.lower() in ['authorization', 'token', 'cookie']:
                    print(f"  --> {k}: {v[:50]}...")
                elif 'pms' in k.lower() or 'auth' in k.lower():
                    print(f"  --> {k}: {v}")

def main():
    username = "sunrongnan"
    password = "Sunrongnan0808"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("正在登录系统...")
        page.goto("http://pms.cic.inter/user/login")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)
        
        # 开始监听网页内部发出的请求
        page.on("request", handle_request)
        
        page.get_by_role("button", name="登 录").click()
        
        print("等待登录成功并监控后续请求...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        browser.close()

if __name__ == "__main__":
    main()
