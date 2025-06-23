#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Google 账户删除工具

这个脚本用于自动删除通过 Google OAuth 认证的 Cursor 账户。
脚本会自动打开浏览器，引导用户完成 Google 登录，然后自动导航到
Cursor 设置页面并执行账户删除操作。

主要功能：
- 自动化 Google OAuth 登录流程
- 导航到 Cursor 设置页面的高级选项
- 自动点击删除账户按钮
- 处理删除确认对话框
- 完成账户永久删除

使用方法：
1. 直接运行: python delete_cursor_google.py
2. 作为模块导入: from delete_cursor_google import CursorGoogleAccountDeleter

注意事项：
- 此操作不可逆，删除后无法恢复账户
- 需要有效的 Google 账户用于登录
- 确保网络连接稳定
- 建议在删除前备份重要数据

依赖模块：
- oauth_auth: OAuth 认证处理基类
- colorama: 彩色终端输出
- time: 时间延迟控制
- sys: 系统相关功能

作者: yeongpin
GitHub: https://github.com/yeongpin/cursor-free-vip
"""

from oauth_auth import OAuthHandler
import time
from colorama import Fore, Style, init
import sys

# 初始化 colorama 用于彩色终端输出
init()

# 定义表情符号常量，用于美化终端输出
EMOJI = {
    'START': '🚀',      # 开始图标
    'DELETE': '🗑️',     # 删除图标
    'SUCCESS': '✅',    # 成功图标
    'ERROR': '❌',      # 错误图标
    'WAIT': '⏳',       # 等待图标
    'INFO': 'ℹ️',       # 信息图标
    'WARNING': '⚠️'     # 警告图标
}

class CursorGoogleAccountDeleter(OAuthHandler):
    """
    Cursor Google 账户删除器
    
    这个类继承自 OAuthHandler，专门用于处理通过 Google OAuth 认证的
    Cursor 账户删除操作。它封装了完整的删除流程，包括登录、导航、
    确认和执行删除操作。
    
    继承关系：
    - 继承自 OAuthHandler 类，获得浏览器自动化和 OAuth 处理能力
    - 专门针对 Google 认证方式进行优化
    
    主要方法：
    - delete_google_account(): 执行完整的账户删除流程
    
    使用示例：
        deleter = CursorGoogleAccountDeleter(translator)
        success = deleter.delete_google_account()
    """
    
    def __init__(self, translator=None):
        """
        初始化 Google 账户删除器
        
        Args:
            translator: 可选的翻译器对象，用于国际化消息显示
        
        Note:
            - 自动设置认证类型为 'google'
            - 继承父类的浏览器自动化功能
        """
        super().__init__(translator, auth_type='google')
        
    def delete_google_account(self):
        """
        删除 Cursor 账户（使用 Google OAuth 认证）
        
        这个方法执行完整的账户删除流程，包括：
        1. 设置浏览器和选择配置文件
        2. 导航到 Cursor 认证页面
        3. 执行 Google OAuth 登录
        4. 等待认证完成
        5. 导航到设置页面
        6. 点击高级选项
        7. 找到并点击删除账户按钮
        8. 处理确认对话框
        9. 完成账户删除
        
        Returns:
            bool: 删除成功返回 True，失败返回 False
            
        Raises:
            Exception: 当关键步骤失败时抛出异常
            
        Note:
            - 此操作不可逆，请谨慎使用
            - 需要用户手动选择 Google 账户
            - 整个过程可能需要 2-3 分钟
            - 网络不稳定可能导致超时
        """
        try:
            # 设置浏览器并选择配置文件
            if not self.setup_browser():
                return False
                
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('account_delete.starting_process') if self.translator else 'Starting account deletion process...'}{Style.RESET_ALL}")
            
            # 导航到 Cursor 认证页面（使用与注册相同的 URL）
            self.browser.get("https://authenticator.cursor.sh/sign-up")
            time.sleep(2)
            
            # 使用与注册相同的选择器点击 Google 认证按钮
            selectors = [
                "//a[contains(@href,'GoogleOAuth')]",  # 包含 GoogleOAuth 的链接
                "//a[contains(@class,'auth-method-button') and contains(@href,'GoogleOAuth')]",  # 认证方法按钮
                "(//a[contains(@class,'auth-method-button')])[1]"  # 第一个认证按钮作为备选
            ]
            
            # 尝试找到 Google 认证按钮
            auth_btn = None
            for selector in selectors:
                try:
                    auth_btn = self.browser.ele(f"xpath:{selector}", timeout=2)
                    if auth_btn:
                        break
                except:
                    continue
            
            if not auth_btn:
                raise Exception(self.translator.get('account_delete.google_button_not_found') if self.translator else "Google login button not found")
                
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('account_delete.logging_in') if self.translator else 'Logging in with Google...'}{Style.RESET_ALL}")
            auth_btn.click()  # 点击 Google 登录按钮
            
            # 使用更强健的方法等待认证完成
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('account_delete.waiting_for_auth', fallback='Waiting for Google authentication...')}{Style.RESET_ALL}")
            
            # 动态等待认证完成
            max_wait_time = 120  # 增加最大等待时间到 120 秒
            start_time = time.time()
            check_interval = 3  # 每 3 秒检查一次
            google_account_alert_shown = False  # 跟踪是否已经显示过提醒
            
            while time.time() - start_time < max_wait_time:
                current_url = self.browser.url
                
                # 如果已经在设置或仪表板页面，说明登录成功
                if "/dashboard" in current_url or "/settings" in current_url or "cursor.com" in current_url:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.login_successful') if self.translator else 'Login successful'}{Style.RESET_ALL}")
                    break
                    
                # 如果在 Google 账户页面，等待用户选择账户
                if "accounts.google.com" in current_url:
                    # 只显示一次提醒以避免重复
                    if not google_account_alert_shown:
                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('account_delete.select_google_account', fallback='Please select your Google account...')}{Style.RESET_ALL}")
                        # 显示提醒表示需要用户操作
                        try:
                            self.browser.run_js("""
                            alert('Please select your Google account to continue with Cursor authentication');
                            """)
                            google_account_alert_shown = True  # 标记已经显示过提醒
                        except:
                            pass  # 提醒是可选的
                
                # 等待一段时间后再次检查
                time.sleep(check_interval)
            else:
                # 如果循环完成而没有中断，说明超时了
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('account_delete.auth_timeout', fallback='Authentication timeout, continuing anyway...')}{Style.RESET_ALL}")
            
            # 检查当前 URL 以确定下一步操作
            current_url = self.browser.url
            
            # 如果已经在设置页面，无需导航
            if "/settings" in current_url and "cursor.com" in current_url:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.already_on_settings', fallback='Already on settings page')}{Style.RESET_ALL}")
            # 如果在仪表板或其他 Cursor 页面但不是设置页面，导航到设置
            elif "cursor.com" in current_url or "authenticator.cursor.sh" in current_url:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('account_delete.navigating_to_settings', fallback='Navigating to settings page...')}{Style.RESET_ALL}")
                self.browser.get("https://www.cursor.com/settings")
            # 如果仍在 Google 认证或其他地方，尝试直接导航到设置
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('account_delete.login_redirect_failed', fallback='Login redirection failed, trying direct navigation...')}{Style.RESET_ALL}")
                self.browser.get("https://www.cursor.com/settings")
                
            # 等待设置页面加载
            time.sleep(3)  # 从 5 秒减少到 3 秒
            
            # 首先查找邮箱元素以确认已登录
            email_element = None
            try:
                # 尝试多个选择器查找邮箱元素
                email_selectors = [
                    "[data-testid='user-email']",
                    "[data-testid='email']",
                    "span[class*='email']",
                    "div[class*='email']",
                    "p[class*='email']",
                    "span:contains('@')",
                    "div:contains('@')",
                    "p:contains('@')"
                ]
                
                for selector in email_selectors:
                    try:
                        email_element = self.browser.find(selector, timeout=2)
                        if email_element and '@' in email_element.text:
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.logged_in_as', fallback='Logged in as')}: {email_element.text}{Style.RESET_ALL}")
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('account_delete.email_check_failed', fallback='Could not verify email, continuing...')}{Style.RESET_ALL}")
            
            # 使用多种策略查找删除账户按钮
            delete_button = None
            delete_selectors = [
                "button:contains('Delete Account')",
                "button:contains('delete account')",
                "button:contains('Delete')",
                "a:contains('Delete Account')",
                "a:contains('delete account')",
                "[data-testid='delete-account']",
                "[data-testid='delete-account-button']",
                "button[class*='delete']",
                "button[class*='danger']",
                "button[class*='destructive']"
            ]
            
            # 点击"高级"选项卡或下拉菜单 - 保留成功的方法
            advanced_found = False
            
            # 根据日志记录，使用直接的 JavaScript querySelector 方法
            try:
                advanced_element_js = self.browser.run_js("""
                    // 尝试使用精确的类名查找高级下拉菜单
                    let advancedElement = document.querySelector('div.mb-0.flex.cursor-pointer.items-center.text-xs:not([style*="display: none"])');
                    
                    // 如果未找到，尝试更通用的方法
                    if (!advancedElement) {
                        const allDivs = document.querySelectorAll('div');
                        for (const div of allDivs) {
                            if (div.textContent.includes('Advanced') && 
                                div.className.includes('mb-0') && 
                                div.className.includes('flex') &&
                                div.className.includes('cursor-pointer')) {
                                advancedElement = div;
                                break;
                            }
                        }
                    }
                    
                    // 如果找到元素则点击
                    if (advancedElement) {
                        advancedElement.click();
                        return true;
                    }
                    
                    return false;
                """)
                
                if advanced_element_js:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.advanced_tab_clicked', fallback='Found and clicked Advanced using direct JavaScript selector')}{Style.RESET_ALL}")
                    advanced_found = True
                    time.sleep(1)  # 从 2 秒减少到 1 秒
            except Exception as e:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('account_delete.advanced_tab_error', error=str(e), fallback='JavaScript querySelector approach failed: {str(e)}')}{Style.RESET_ALL}")
            
            if not advanced_found:
                # 备用方案：直接 URL 导航，更快更可靠
                try:
                    self.browser.get("https://www.cursor.com/settings?tab=advanced")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('account_delete.direct_advanced_navigation', fallback='Trying direct navigation to advanced tab')}{Style.RESET_ALL}")
                    advanced_found = True
                except:
                    raise Exception(self.translator.get('account_delete.advanced_tab_not_found') if self.translator else "Advanced option not found after multiple attempts")
            
            # 等待下拉菜单/选项卡内容加载
            time.sleep(2)  # 从 4 秒减少到 2 秒
            
            # 查找并点击"删除账户"按钮
            delete_button_found = False
            
            # 基于有效方法的简化删除按钮查找方式
            delete_button_selectors = [
                'xpath://button[contains(., "Delete Account")]',
                'xpath://button[text()="Delete Account"]',
                'xpath://div[contains(text(), "Delete Account")]',
                'xpath://button[contains(text(), "Delete") and contains(text(), "Account")]'
            ]
                
            for selector in delete_button_selectors:
                try:
                    delete_button = self.browser.ele(selector, timeout=2)
                    if delete_button:
                        delete_button.click()
                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('account_delete.delete_button_clicked') if self.translator else 'Clicked on Delete Account button'}{Style.RESET_ALL}")
                        delete_button_found = True
                        break
                except:
                    continue
            
            if not delete_button_found:
                raise Exception(self.translator.get('account_delete.delete_button_not_found') if self.translator else "Delete Account button not found")
            
            # 等待确认对话框出现
            time.sleep(2)
            
            # 检查是否需要输入"Delete" - 某些模态框可能不需要
            input_required = True
            try:
                # 尝试检测 DELETE 按钮是否已启用
                delete_button_enabled = self.browser.run_js("""
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const deleteButtons = buttons.filter(btn => 
                        btn.textContent.trim() === 'DELETE' || 
                        btn.textContent.trim() === 'Delete'
                    );
                    
                    if (deleteButtons.length > 0) {
                        return !deleteButtons.some(btn => btn.disabled);
                    }
                    return false;
                """)
                
                if delete_button_enabled:
                    print(f"{Fore.CYAN}{EMOJI['INFO']} DELETE button appears to be enabled already. Input may not be required.{Style.RESET_ALL}")
                    input_required = False
            except:
                pass
            
            # 在确认输入框中输入"Delete" - 仅在需要时
            delete_input_found = False
            
            if input_required:
                # 尝试常见的输入框选择器
                delete_input_selectors = [
                    'xpath://input[@placeholder="Delete"]',
                    'xpath://div[contains(@class, "modal")]//input',
                    'xpath://input',
                    'css:input'
                ]
                
                for selector in delete_input_selectors:
                    try:
                        delete_input = self.browser.ele(selector, timeout=3)
                        if delete_input:
                            delete_input.clear()
                            delete_input.input("Delete")
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.typed_delete', fallback='Typed \"Delete\" in confirmation box')}{Style.RESET_ALL}")
                            delete_input_found = True
                            time.sleep(2)
                            break
                    except:
                        # 备用方案：使用直接的 JavaScript 输入
                        try:
                            self.browser.run_js(r"""
                                arguments[0].value = "Delete";
                                const event = new Event('input', { bubbles: true });
                                arguments[0].dispatchEvent(event);
                                const changeEvent = new Event('change', { bubbles: true });
                                arguments[0].dispatchEvent(changeEvent);
                            """, delete_input)
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.typed_delete_js', fallback='Typed \"Delete\" using JavaScript')}{Style.RESET_ALL}")
                            delete_input_found = True
                            time.sleep(2)
                            break
                        except:
                            continue
                
                if not delete_input_found:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('account_delete.delete_input_not_found', fallback='Delete confirmation input not found, continuing anyway')}{Style.RESET_ALL}")
                    time.sleep(2)
            
            # 点击最终删除按钮前等待
            time.sleep(2)
            
            # 点击最终的删除按钮
            confirm_button_found = False
            
            # 使用 JavaScript 方法查找删除按钮
            try:
                delete_button_js = self.browser.run_js("""
                    // 尝试通过精确的文本内容查找删除按钮
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const deleteButton = buttons.find(btn => 
                        btn.textContent.trim() === 'DELETE' || 
                        btn.textContent.trim() === 'Delete'
                    );
                    
                    if (deleteButton) {
                        console.log("Found DELETE button with JavaScript");
                        deleteButton.click();
                        return true;
                    }
                    
                    // 如果通过文本未找到，尝试查找模态框中最右侧的按钮
                    const modalButtons = Array.from(document.querySelectorAll('.relative button, [role="dialog"] button, .modal button, [aria-modal="true"] button'));
                    
                    if (modalButtons.length > 1) {
                        modalButtons.sort((a, b) => {
                            const rectA = a.getBoundingClientRect();
                            const rectB = b.getBoundingClientRect();
                            return rectB.right - rectA.right;
                        });
                        
                        console.log("Clicking right-most button in modal");
                        modalButtons[0].click();
                        return true;
                    } else if (modalButtons.length === 1) {
                        console.log("Clicking single button found in modal");
                        modalButtons[0].click();
                        return true;
                    }
                    
                    return false;
                """)
                
                if delete_button_js:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.delete_button_clicked', fallback='Clicked DELETE button')}{Style.RESET_ALL}")
                    confirm_button_found = True
            except:
                pass
            
            if not confirm_button_found:
                # 备用方案：使用简单选择器
                delete_button_selectors = [
                    'xpath://button[text()="DELETE"]',
                    'xpath://div[contains(@class, "modal")]//button[last()]'
                ]
                
                for selector in delete_button_selectors:
                    try:
                        delete_button = self.browser.ele(selector, timeout=2)
                        if delete_button:
                            delete_button.click()
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('account_delete.delete_button_clicked', fallback='Account deleted successfully!')}{Style.RESET_ALL}")
                            confirm_button_found = True
                            break
                    except:
                        continue
            
            if not confirm_button_found:
                raise Exception(self.translator.get('account_delete.confirm_button_not_found') if self.translator else "Confirm button not found")
            
            # 等待一会儿查看确认结果
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('account_delete.error', error=str(e)) if self.translator else f'Error during account deletion: {str(e)}'}{Style.RESET_ALL}")
            return False
        finally:
            # 清理浏览器资源
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
            
def main(translator=None):
    """
    主函数：处理 Google 账户删除
    
    参数:
        translator: 翻译器对象，用于多语言支持
    
    功能:
        1. 显示警告信息
        2. 请求用户确认
        3. 执行账户删除流程
        4. 处理异常和中断
    """
    print(f"\n{Fore.CYAN}{EMOJI['START']} {translator.get('account_delete.title') if translator else 'Cursor Google Account Deletion Tool'}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 50}{Style.RESET_ALL}")
    
    deleter = CursorGoogleAccountDeleter(translator)
    
    try:
        # 请求用户确认
        print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('account_delete.warning') if translator else 'WARNING: This will permanently delete your Cursor account. This action cannot be undone.'}{Style.RESET_ALL}")
        confirm = input(f"{Fore.RED} {translator.get('account_delete.confirm_prompt') if translator else 'Are you sure you want to proceed? (y/N): '}{Style.RESET_ALL}").lower()
        
        if confirm != 'y':
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('account_delete.cancelled') if translator else 'Account deletion cancelled.'}{Style.RESET_ALL}")
            return
            
        # 执行删除操作
        success = deleter.delete_google_account()
        
        if success:
            print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('account_delete.success') if translator else 'Your Cursor account has been successfully deleted!'}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('account_delete.failed') if translator else 'Account deletion process failed or was cancelled.'}{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('account_delete.interrupted') if translator else 'Account deletion process interrupted by user.'}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_delete.unexpected_error', error=str(e)) if translator else f'Unexpected error: {str(e)}'}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.YELLOW}{'─' * 50}{Style.RESET_ALL}")

# 脚本入口点：当文件作为独立程序运行时执行主函数
if __name__ == "__main__":
    main()