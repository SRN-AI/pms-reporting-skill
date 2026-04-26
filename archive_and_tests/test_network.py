from playwright.sync_api import sync_playwright
import json

def handle_response(response):
    # 监听所有响应，特别是可能包含 token 的接口
    # 过滤掉一些静态资源以减少噪音
    if response.request.resource_type in ["xhr", "fetch"]:
        url = response.url
        print(f"\n[Network] 收到接口响应: {url}")
        print(f"[Network] 状态码: {response.status}")
        
        # 尝试打印响应头，看看有没有类似 Set-Cookie, Token, Authorization 这样的字段
        headers = response.headers
        auth_headers = {k: v for k, v in headers.items() if 'token' in k.lower() or 'auth' in k.lower() or 'cookie' in k.lower()}
        if auth_headers:
            print(f"[Network] 发现敏感响应头: {auth_headers}")

        # 尝试解析 JSON 响应体，很多时候 token 在 login 接口的返回 json 里
        try:
            body = response.json()
            # 简单查一下有没有 token 字段
            body_str = json.dumps(body, ensure_ascii=False)
            if 'token' in body_str.lower() or 'session' in body_str.lower() or 'auth' in body_str.lower():
                print(f"[Network] 响应体包含敏感信息: {str(body)[:200]}...") # 只打印前200字符防刷屏
        except:
            pass

def main():
    username = "sunrongnan"
    password = "Sunrongnan0808"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # 使用无头模式在后台快速跑完
        context = browser.new_context()
        page = context.new_page()

        # 挂载网络监听器
        page.on("response", handle_response)

        print("正在访问登录页面...")
        page.goto("http://pms.cic.inter/user/login")

        print("正在填写凭证并点击登录...")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)
        page.get_by_role("button", name="登 录").click()

        print("等待网络空闲...")
        page.wait_for_load_state("networkidle")
        
        # 额外等待一小会儿以确保所有的异步请求都返回了
        page.wait_for_timeout(2000)

        print("\n--- 最终的 Cookies ---")
        cookies = context.cookies()
        for cookie in cookies:
             print(f"{cookie['name']}: {cookie['value'][:20]}...")
             
        print("\n--- 最终的 LocalStorage ---")
        local_storage = page.evaluate("() => JSON.stringify(window.localStorage)")
        ls_dict = json.loads(local_storage)
        for k, v in ls_dict.items():
            print(f"{k}: {str(v)[:50]}...")

        print("\n--- 最终的 SessionStorage ---")
        session_storage = page.evaluate("() => JSON.stringify(window.sessionStorage)")
        ss_dict = json.loads(session_storage)
        for k, v in ss_dict.items():
            print(f"{k}: {str(v)[:50]}...")

        browser.close()

if __name__ == "__main__":
    main()
