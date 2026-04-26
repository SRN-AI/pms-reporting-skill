from playwright.sync_api import sync_playwright
import json

def main():
    username = "sunrongnan"
    password = "Sunrongnan0808"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 挂载监听器
        def handle_response(response):
            if "pms-gateway/user/login" in response.url:
                print(f"--- 登录接口响应内容 ---")
                try:
                    print(response.json())
                except:
                    print(response.text())
            if "pms-gateway/getSalt" in response.url:
                print(f"--- getSalt接口响应内容 ---")
                try:
                    print(response.json())
                except:
                    print(response.text())

        page.on("response", handle_response)

        page.goto("http://pms.cic.inter/user/login")
        page.get_by_role("textbox", name="请输入用户名/工号/UM码").fill(username)
        page.get_by_role("textbox", name="请输入密码").fill(password)
        page.get_by_role("button", name="登 录").click()
        
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        browser.close()

if __name__ == "__main__":
    main()
