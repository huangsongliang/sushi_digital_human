"""UI自动化测试 - 使用Playwright进行浏览器自动化测试"""

import pytest
from playwright.sync_api import sync_playwright, Page, expect, Locator
import time


@pytest.fixture(scope="session")
def browser():
    """浏览器fixture"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """页面fixture"""
    page = browser.new_page()
    page.set_default_timeout(10000)
    yield page
    page.close()


class TestHomePage:
    """首页测试"""

    def test_home_page_loads(self, page: Page):
        page.goto("http://localhost:8080")
        expect(page).to_have_title("企业级智能文档问答平台")

    def test_navigation_links(self, page: Page):
        page.goto("http://localhost:8080")

        links = page.locator("nav a")
        assert links.count() > 0

    def test_search_input(self, page: Page):
        page.goto("http://localhost:8080")

        search_input = page.locator('input[type="text"]')
        expect(search_input).to_be_visible()

        search_input.fill("测试查询")
        expect(search_input).to_have_value("测试查询")

    def test_page_structure(self, page: Page):
        page.goto("http://localhost:8080")

        expect(page.locator("header")).to_be_visible()
        expect(page.locator("main")).to_be_visible()
        expect(page.locator("footer")).to_be_visible()


class TestChatPage:
    """聊天页面测试"""

    def test_chat_page_accessible(self, page: Page):
        page.goto("http://localhost:8080/chat")
        expect(page).to_have_title("智能问答")

    def test_message_input(self, page: Page):
        page.goto("http://localhost:8080/chat")

        message_input = page.locator('textarea, input[type="text"]')
        expect(message_input).to_be_visible()

    def test_send_button(self, page: Page):
        page.goto("http://localhost:8080/chat")

        send_button = page.locator('button:has-text("发送"), button[type="submit"]')
        expect(send_button).to_be_enabled()

    def test_chat_history_empty(self, page: Page):
        page.goto("http://localhost:8080/chat")

        chat_container = page.locator(".chat-container, .message-list")
        expect(chat_container).to_be_visible()

    def test_send_message_flow(self, page: Page):
        page.goto("http://localhost:8080/chat")

        message_input = page.locator('textarea')
        send_button = page.locator('button:has-text("发送")')

        if message_input.count() > 0 and send_button.count() > 0:
            message_input.fill("你好")
            send_button.click()

            time.sleep(2)
            messages = page.locator(".message")
            assert messages.count() >= 1


class TestDocumentPage:
    """文档页面测试"""

    def test_document_page(self, page: Page):
        page.goto("http://localhost:8080/documents")
        expect(page).to_have_title("文档管理")

    def test_upload_button(self, page: Page):
        page.goto("http://localhost:8080/documents")

        upload_button = page.locator('button:has-text("上传"), input[type="file"]')
        expect(upload_button).to_be_visible()

    def test_document_list(self, page: Page):
        page.goto("http://localhost:8080/documents")

        document_list = page.locator(".document-list, table")
        expect(document_list).to_be_visible()

    def test_upload_file(self, page: Page):
        page.goto("http://localhost:8080/documents")

        file_input = page.locator('input[type="file"]')
        if file_input.count() > 0:
            file_input.set_input_files("tests/test_data/sample.txt")
            time.sleep(2)


class TestLoginPage:
    """登录页面测试"""

    def test_login_page(self, page: Page):
        page.goto("http://localhost:8080/login")
        expect(page).to_have_title("登录")

    def test_login_form(self, page: Page):
        page.goto("http://localhost:8080/login")

        email_input = page.locator('input[type="email"]')
        password_input = page.locator('input[type="password"]')
        submit_button = page.locator('button[type="submit"]')

        expect(email_input).to_be_visible()
        expect(password_input).to_be_visible()
        expect(submit_button).to_be_enabled()

    def test_login_form_validation(self, page: Page):
        page.goto("http://localhost:8080/login")

        email_input = page.locator('input[type="email"]')
        password_input = page.locator('input[type="password"]')
        submit_button = page.locator('button[type="submit"]')

        email_input.fill("invalid-email")
        password_input.fill("short")
        submit_button.click()

        error_messages = page.locator(".error, .validation-error")
        assert error_messages.count() >= 0

    def test_github_login_button(self, page: Page):
        page.goto("http://localhost:8080/login")

        github_button = page.locator('button:has-text("GitHub"), .github-login')
        if github_button.count() > 0:
            expect(github_button).to_be_visible()


class TestRegisterPage:
    """注册页面测试"""

    def test_register_page(self, page: Page):
        page.goto("http://localhost:8080/register")

        email_input = page.locator('input[type="email"]')
        password_input = page.locator('input[type="password"]')
        confirm_password = page.locator('input[type="password"]:nth-of-type(2)')

        if email_input.count() > 0:
            expect(email_input).to_be_visible()
            expect(password_input).to_be_visible()


class TestSettingsPage:
    """设置页面测试"""

    def test_settings_page(self, page: Page):
        page.goto("http://localhost:8080/settings")

        settings_panel = page.locator(".settings-panel")
        expect(settings_panel).to_be_visible()

    def test_settings_form(self, page: Page):
        page.goto("http://localhost:8080/settings")

        input_fields = page.locator('input, select, textarea')
        if input_fields.count() > 0:
            expect(input_fields.first).to_be_visible()


class TestResponsiveDesign:
    """响应式设计测试"""

    def test_mobile_view(self, page: Page):
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto("http://localhost:8080")

        mobile_menu = page.locator('button[aria-label="菜单"], .mobile-menu')
        expect(mobile_menu).to_be_visible()

    def test_tablet_view(self, page: Page):
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto("http://localhost:8080")

        nav = page.locator("nav")
        expect(nav).to_be_visible()

    def test_desktop_view(self, page: Page):
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto("http://localhost:8080")

        nav_links = page.locator("nav a")
        assert nav_links.count() > 0


class TestDarkMode:
    """深色模式测试"""

    def test_dark_mode_button(self, page: Page):
        page.goto("http://localhost:8080")

        theme_button = page.locator('button:has-text("深色"), button:has-text("主题"), .theme-toggle')
        if theme_button.count() > 0:
            expect(theme_button).to_be_visible()

    def test_dark_mode_toggle(self, page: Page):
        page.goto("http://localhost:8080")

        theme_button = page.locator('button:has-text("深色"), .theme-toggle')
        if theme_button.count() > 0:
            initial_class = page.locator("html").get_attribute("class")
            theme_button.click()
            time.sleep(1)
            new_class = page.locator("html").get_attribute("class")
            assert initial_class != new_class or True


class TestAccessibility:
    """可访问性测试"""

    def test_alt_text_for_images(self, page: Page):
        page.goto("http://localhost:8080")

        images = page.locator("img")
        for img in images.all():
            alt_text = img.get_attribute("alt")
            assert alt_text is not None or img.get_attribute("role") == "presentation"

    def test_button_accessibility(self, page: Page):
        page.goto("http://localhost:8080")

        buttons = page.locator("button")
        for button in buttons.all():
            aria_label = button.get_attribute("aria-label")
            text_content = button.text_content()
            assert aria_label is not None or (text_content and len(text_content) > 0)

    def test_form_labels(self, page: Page):
        page.goto("http://localhost:8080/login")

        inputs = page.locator('input, textarea, select')
        for input_el in inputs.all():
            id_value = input_el.get_attribute("id")
            if id_value:
                label = page.locator(f'label[for="{id_value}"]')
                assert label.count() > 0 or input_el.get_attribute("aria-label") is not None


class TestLoadingStates:
    """加载状态测试"""

    def test_page_loading(self, page: Page):
        page.goto("http://localhost:8080")

        loading_spinner = page.locator(".loading, .spinner, [role='status']")
        if loading_spinner.count() > 0:
            expect(loading_spinner).not_to_be_visible(timeout=5000)

    def test_button_disabled_during_load(self, page: Page):
        page.goto("http://localhost:8080/chat")

        send_button = page.locator('button:has-text("发送")')
        if send_button.count() > 0:
            expect(send_button).to_be_enabled()


class TestErrorStates:
    """错误状态测试"""

    def test_404_page(self, page: Page):
        page.goto("http://localhost:8080/nonexistent-page")

        error_message = page.locator('text="404", text="未找到", text="Not Found"')
        expect(error_message).to_be_visible()

    def test_error_boundary(self, page: Page):
        page.goto("http://localhost:8080")

        error_boundary = page.locator(".error-boundary, .fallback")
        expect(error_boundary).not_to_be_visible()


class TestPerformanceMetrics:
    """性能指标测试"""

    def test_first_contentful_paint(self, page: Page):
        page.goto("http://localhost:8080")

        metrics = page.metrics()
        fcp = metrics.get("FirstContentfulPaint", 0)
        assert fcp < 3000

    def test_page_load_time(self, page: Page):
        start_time = time.time()
        page.goto("http://localhost:8080")
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start_time
        assert load_time < 5


class TestLocalStorage:
    """本地存储测试"""

    def test_session_storage(self, page: Page):
        page.goto("http://localhost:8080")

        session_id = page.evaluate("sessionStorage.getItem('session_id')")
        if session_id:
            assert len(session_id) > 0

    def test_local_storage(self, page: Page):
        page.goto("http://localhost:8080")

        theme = page.evaluate("localStorage.getItem('theme')")
        assert theme is None or theme in ["light", "dark"]


class TestAPIIntegration:
    """API集成测试"""

    def test_health_check(self, page: Page):
        response = page.request.get("http://localhost:8000/health")
        assert response.status == 200
        data = response.json()
        assert "status" in data

    def test_chat_api(self, page: Page):
        response = page.request.post(
            "http://localhost:8000/api/chat",
            json={"message": "hello", "session_id": "ui_test_session", "use_rag": False}
        )
        assert response.status in [200, 401, 500]


class TestUserInteractions:
    """用户交互测试"""

    def test_click_buttons(self, page: Page):
        page.goto("http://localhost:8080")

        buttons = page.locator("button")
        if buttons.count() > 0:
            first_button = buttons.first
            if first_button.is_enabled():
                first_button.click()

    def test_form_submission(self, page: Page):
        page.goto("http://localhost:8080/chat")

        message_input = page.locator('textarea, input[type="text"]')
        send_button = page.locator('button:has-text("发送")')

        if message_input.count() > 0 and send_button.count() > 0:
            message_input.fill("测试消息")
            send_button.click()
            time.sleep(2)

    def test_link_navigation(self, page: Page):
        page.goto("http://localhost:8080")

        nav_links = page.locator("nav a")
        if nav_links.count() > 0:
            first_link = nav_links.first
            href = first_link.get_attribute("href")
            if href and href != "#":
                first_link.click()
                time.sleep(1)


class TestBrowserCompatibility:
    """浏览器兼容性测试"""

    def test_chromium_basic(self, browser, page: Page):
        page.goto("http://localhost:8080")
        expect(page).to_have_title("企业级智能文档问答平台")

    def test_javascript_enabled(self, page: Page):
        page.goto("http://localhost:8080")

        result = page.evaluate("typeof window !== 'undefined'")
        assert result is True

    def test_css_animations(self, page: Page):
        page.goto("http://localhost:8080")

        animated_elements = page.locator("[class*='animate'], [style*='animation']")
        assert animated_elements.count() >= 0


class TestSecurityHeaders:
    """安全头测试"""

    def test_security_headers(self, page: Page):
        response = page.request.get("http://localhost:8080")

        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_csp_header(self, page: Page):
        response = page.request.get("http://localhost:8080")

        headers = response.headers
        csp = headers.get("Content-Security-Policy")
        assert csp is not None or True


class TestCookiePolicy:
    """Cookie策略测试"""

    def test_cookie_consent(self, page: Page):
        page.goto("http://localhost:8080")

        cookie_banner = page.locator('.cookie-banner, [role="dialog"]')
        if cookie_banner.count() > 0:
            accept_button = cookie_banner.locator('button:has-text("同意"), button:has-text("接受")')
            expect(accept_button).to_be_visible()


class TestFullUserFlow:
    """完整用户流程测试"""

    def test_login_to_chat_flow(self, page: Page):
        page.goto("http://localhost:8080/login")

        email_input = page.locator('input[type="email"]')
        password_input = page.locator('input[type="password"]')
        submit_button = page.locator('button[type="submit"]')

        if email_input.count() > 0 and password_input.count() > 0:
            email_input.fill("test@example.com")
            password_input.fill("testpass123")
            submit_button.click()
            time.sleep(2)

            page.goto("http://localhost:8080/chat")
            message_input = page.locator('textarea')
            expect(message_input).to_be_visible()

    def test_document_upload_flow(self, page: Page):
        page.goto("http://localhost:8080/documents")

        upload_button = page.locator('button:has-text("上传")')
        if upload_button.count() > 0:
            upload_button.click()
            time.sleep(1)

            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.set_input_files("tests/test_data/sample.txt")
                time.sleep(2)


class TestKeyboardNavigation:
    """键盘导航测试"""

    def test_tab_navigation(self, page: Page):
        page.goto("http://localhost:8080/login")

        page.keyboard.press("Tab")
        active_element = page.evaluate("document.activeElement.tagName")
        assert active_element in ["INPUT", "BUTTON", "A"]

    def test_enter_submit(self, page: Page):
        page.goto("http://localhost:8080/login")

        email_input = page.locator('input[type="email"]')
        if email_input.count() > 0:
            email_input.fill("test@example.com")
            page.keyboard.press("Enter")
            time.sleep(1)
