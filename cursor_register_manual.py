#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 手动注册模块

功能:
    提供 Cursor 账户的自动注册功能，包括邮箱设置、账户信息生成、
    注册流程执行、令牌获取和账户信息保存等完整流程。

主要特性:
    - 自动生成随机账户信息（姓名、密码）
    - 支持邮箱建议和手动输入
    - 集成临时邮箱服务（TempMailPlus）
    - 自动化浏览器操作完成注册
    - 自动获取和保存认证令牌
    - 重置机器 ID 以确保账户独立性

作者: kingmo888
项目: https://github.com/kingmo888/cursor-free-vip
"""

# 标准库导入
import os
import time
import random

# 第三方库导入
from colorama import Fore, Style, init  # 终端颜色输出
from faker import Faker  # 生成虚假数据（姓名、密码等）

# 自定义模块导入
from cursor_auth import CursorAuth  # Cursor 认证管理
from reset_machine_manual import MachineIDResetter  # 机器 ID 重置
from get_user_token import get_token_from_cookie  # 从 Cookie 获取令牌
from config import get_config  # 配置管理
from account_manager import AccountManager  # 账户信息管理

# 环境变量设置 - 禁用详细输出以保持界面整洁
os.environ["PYTHONVERBOSE"] = "0"  # 禁用 Python 详细输出
os.environ["PYINSTALLER_VERBOSE"] = "0"  # 禁用 PyInstaller 详细输出

# 初始化 colorama 以支持跨平台终端颜色输出
init(autoreset=True)

# 表情符号常量 - 用于美化终端输出界面
EMOJI = {
    'success': '✅',    # 成功操作
    'error': '❌',      # 错误信息
    'warning': '⚠️',    # 警告信息
    'info': 'ℹ️',       # 一般信息
    'email': '📧',      # 邮箱相关
    'user': '👤',       # 用户相关
    'password': '🔑',   # 密码相关
    'loading': '⏳',    # 加载中
    'check': '🔍',      # 检查操作
    'save': '💾',       # 保存操作
    'reset': '🔄'       # 重置操作
}

class CursorRegistration:
    """
    Cursor 注册管理类
    
    负责处理 Cursor 账户的完整注册流程，包括:
    - 用户信息生成和收集
    - 邮箱设置和验证
    - 自动化注册流程
    - 令牌获取和保存
    - 机器 ID 重置
    
    属性:
        config: 配置信息
        account_manager: 账户管理器实例
        faker: 虚假数据生成器
        first_name: 用户名字
        last_name: 用户姓氏
        email: 用户邮箱
        password: 用户密码
    """
    def __init__(self, translator=None):
        """
        初始化 CursorRegistration 实例
        
        参数:
            translator: 翻译器实例，用于多语言支持
        """
        self.translator = translator  # 翻译器实例
        # Set to display mode
        os.environ['BROWSER_HEADLESS'] = 'False'
        self.browser = None
        self.controller = None
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        self.settings_url = "https://www.cursor.com/settings"
        self.email_address = None
        self.signup_tab = None
        self.email_tab = None
        
        # initialize Faker instance
        self.faker = Faker()  # 虚假数据生成器
        
        # generate account information
        self.password = self._generate_password()  # 用户密码
        self.first_name = self.faker.first_name()  # 用户名字
        self.last_name = self.faker.last_name()    # 用户姓氏
        
        # modify the first letter of the first name(keep the original function)
        new_first_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.first_name = new_first_letter + self.first_name[1:]
        
        print(f"\n{Fore.CYAN}{EMOJI['PASSWORD']} {self.translator.get('register.password')}: {self.password} {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.first_name')}: {self.first_name} {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.last_name')}: {self.last_name} {Style.RESET_ALL}")

    def _generate_password(self, length=12):
        """
        生成随机密码
        
        使用 Faker 库生成包含大小写字母、数字和特殊字符的随机密码。
        
        参数:
            length: 密码长度，默认为 12 位
            
        返回:
            str: 生成的随机密码
        """
        return self.faker.password(length=length, special_chars=True, digits=True, upper_case=True, lower_case=True)

    def get_suggested_email(self):
        """
        生成建议的邮箱地址
        
        基于用户的姓名生成一个建议的邮箱地址，包含随机数字以确保唯一性。
        从常见的邮箱服务提供商中随机选择一个作为邮箱后缀。
        
        生成规则:
            - 格式: 名字.姓氏+随机数字@邮箱提供商
            - 随机数字范围: 100-999
            - 支持的邮箱提供商: Gmail, Outlook, Yahoo, Hotmail
        
        返回:
            str: 生成的邮箱地址，失败时返回 None
        """
        try:
            # 基于用户姓名生成邮箱前缀
            base_email = f"{self.first_name.lower()}.{self.last_name.lower()}"
            
            # 添加随机数字确保唯一性
            random_num = random.randint(100, 999)
            
            # 从常见邮箱提供商中随机选择
            providers = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com']
            provider = random.choice(providers)
            
            suggested_email = f"{base_email}{random_num}@{provider}"
            return suggested_email
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.email_suggestion_failed', error=str(e))}{Style.RESET_ALL}")
            return None

    def run_registration(self):
        """
        执行完整的注册流程
        
        这是注册流程的主要方法，协调各个步骤的执行:
        1. 设置邮箱
        2. 显示用户信息
        3. 执行自动化注册
        4. 获取认证令牌
        5. 保存账户信息
        6. 重置机器 ID
        
        返回:
            bool: 注册成功返回 True，失败返回 False
        """
        pass

    def setup_email(self):
        """
        设置注册邮箱
        
        提供邮箱建议选项或允许用户手动输入邮箱地址。
        邮箱建议基于用户的姓名生成，包含常见的邮箱服务提供商。
        
        流程:
            1. 生成邮箱建议列表
            2. 显示建议选项和手动输入选项
            3. 处理用户选择
            4. 验证并设置邮箱
        """
        try:
            # Try to get a suggested email
            account_manager = AccountManager(self.translator)
            suggested_email = account_manager.suggest_email(self.first_name, self.last_name)
            
            if suggested_email:
                print(f"{Fore.CYAN}{EMOJI['info']} {self.translator.get('register.suggest_email', suggested_email=suggested_email) if self.translator else f'Suggested email: {suggested_email}'}")
                print(f"{Fore.CYAN}{EMOJI['info']} {self.translator.get('register.use_suggested_email_or_enter') if self.translator else 'Type "yes" to use this email or enter your own email:'}")
                user_input = input().strip()
                
                if user_input.lower() == 'yes' or user_input.lower() == 'y':
                    self.email_address = suggested_email
                else:
                    # User input is their own email address
                    self.email_address = user_input
            else:
                # If there's no suggested email
                print(f"{Fore.CYAN}{EMOJI['info']} {self.translator.get('register.manual_email_input') if self.translator else 'Please enter your email address:'}")
                self.email_address = input().strip()
            
            # Validate if the email is valid
            if '@' not in self.email_address:
                print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.invalid_email') if self.translator else 'Invalid email address'}{Style.RESET_ALL}")
                return False
                
            print(f"{Fore.CYAN}{EMOJI['email']} {self.translator.get('register.email_address')}: {self.email_address}" + "\n" + f"{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.email_setup_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def get_verification_code(self):
        """
        手动获取验证码
        
        提示用户手动输入从邮箱收到的6位数字验证码。
        验证码必须是6位纯数字格式。
        
        返回:
            str: 有效的6位验证码，输入无效时返回 None
        
        验证规则:
            - 必须是纯数字
            - 长度必须为6位
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['info']} {self.translator.get('register.manual_code_input') if self.translator else 'Please enter the verification code:'}")
            code = input().strip()
            
            if not code.isdigit() or len(code) != 6:
                print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.invalid_code') if self.translator else 'Invalid verification code'}{Style.RESET_ALL}")
                return None
                
            return code
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.code_input_failed', error=str(e))}{Style.RESET_ALL}")
            return None

    def register_cursor(self):
        """
        执行 Cursor 注册流程
        
        使用自动化浏览器操作完成 Cursor 账户注册。支持集成临时邮箱服务
        (TempMailPlus) 进行邮箱验证。注册完成后获取账户信息和认证令牌。
        
        流程:
            1. 检查并配置临时邮箱服务
            2. 调用 new_signup.py 执行注册
            3. 获取账户信息和令牌
            4. 清理浏览器资源
        
        返回:
            bool: 注册成功返回 True，失败返回 False
        """
        browser_tab = None
        try:
            print(f"{Fore.CYAN}{EMOJI['loading']} {self.translator.get('register.register_start')}...{Style.RESET_ALL}")
            
            # 检查是否启用了临时邮箱服务
            config = get_config(self.translator)
            email_tab = None
            if config and config.has_section('TempMailPlus'):
                if config.getboolean('TempMailPlus', 'enabled'):
                    email = config.get('TempMailPlus', 'email')
                    epin = config.get('TempMailPlus', 'epin')
                    if email and epin:
                        from email_tabs.tempmail_plus_tab import TempMailPlusTab
                        email_tab = TempMailPlusTab(email, epin, self.translator)
                        print(f"{Fore.CYAN}{EMOJI['email']} {self.translator.get('register.using_tempmail_plus')}{Style.RESET_ALL}")
            
            # 直接使用 new_signup.py 进行注册
            from new_signup import main as new_signup_main
            
            # 执行新的注册流程，传递翻译器
            result, browser_tab = new_signup_main(
                email=self.email_address,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                email_tab=email_tab,  # 如果启用了临时邮箱则传递 email_tab
                controller=self,  # 传递 self 而不是 self.controller
                translator=self.translator
            )
            
            if result:
                # 使用返回的浏览器实例获取账户信息
                self.signup_tab = browser_tab  # 保存浏览器实例
                success = self._get_account_info()
                
                # 获取信息后关闭浏览器
                if browser_tab:
                    try:
                        browser_tab.quit()
                    except:
                        pass
                
                return success
            
            return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.register_process_error', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            # 确保在任何情况下都关闭浏览器
            if browser_tab:
                try:
                    browser_tab.quit()
                except:
                    pass
                
    def _get_account_info(self):
        """
        获取账户信息和认证令牌
        
        从 Cursor 设置页面获取账户使用情况信息，并从浏览器 Cookie 中
        提取认证令牌。使用重试机制确保令牌获取的可靠性。
        
        流程:
            1. 导航到设置页面
            2. 提取使用情况信息
            3. 从 Cookie 中获取认证令牌
            4. 保存账户信息
        
        返回:
            bool: 成功获取并保存信息返回 True，失败返回 False
        """
        """Get Account Information and Token"""
        try:
            self.signup_tab.get(self.settings_url)
            time.sleep(2)
            
            usage_selector = (
                "css:div.col-span-2 > div > div > div > div > "
                "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
                "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
            )
            usage_ele = self.signup_tab.ele(usage_selector)
            total_usage = "未知"
            if usage_ele:
                total_usage = usage_ele.text.split("/")[-1].strip()

            print(f"Total Usage: {total_usage}\n")
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('register.get_token')}...{Style.RESET_ALL}")
            max_attempts = 30
            retry_interval = 2
            attempts = 0

            while attempts < max_attempts:
                try:
                    cookies = self.signup_tab.cookies()
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            token = get_token_from_cookie(cookie["value"], self.translator)
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.token_success')}{Style.RESET_ALL}")
                            self._save_account_info(token, total_usage)
                            return True

                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)
                    else:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_max_attempts', max=max_attempts)}{Style.RESET_ALL}")

                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_failed', error=str(e))}{Style.RESET_ALL}")
                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)

            return False

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.account_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def _save_account_info(self, token, total_usage):
        """
        保存账户信息到文件
        
        将注册成功的账户信息保存到本地文件，包括更新认证信息、
        重置机器 ID 和保存账户详细信息。
        
        参数:
            token (str): 认证令牌
            total_usage (str): 账户使用情况信息
        
        流程:
            1. 更新 Cursor 认证信息
            2. 重置机器 ID 确保账户独立性
            3. 使用 AccountManager 保存账户信息
        
        返回:
            bool: 保存成功返回 True，失败返回 False
        """
        try:
            # 首先更新认证信息
            print(f"{Fore.CYAN}{EMOJI['password']} {self.translator.get('register.update_cursor_auth_info')}...{Style.RESET_ALL}")
            if self.update_cursor_auth(email=self.email_address, access_token=token, refresh_token=token, auth_type="Auth_0"):
                print(f"{Fore.GREEN}{EMOJI['success']} {self.translator.get('register.cursor_auth_info_updated')}...{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.cursor_auth_info_update_failed')}...{Style.RESET_ALL}")

            # 重置机器 ID
            print(f"{Fore.CYAN}{EMOJI['reset']} {self.translator.get('register.reset_machine_id')}...{Style.RESET_ALL}")
            resetter = MachineIDResetter(self.translator)  # 创建带翻译器的实例
            if not resetter.reset_machine_ids():  # 直接调用 reset_machine_ids 方法
                raise Exception("Failed to reset machine ID")
            
            # 使用 AccountManager 保存账户信息到文件
            account_manager = AccountManager(self.translator)
            if account_manager.save_account_info(self.email_address, self.password, token, total_usage):
                return True
            else:
                return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['error']} {self.translator.get('register.save_account_info_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def start(self):
        """
        启动注册流程
        
        这是注册流程的入口方法，按顺序执行邮箱设置和注册流程。
        确保在流程结束后正确清理资源（如临时邮箱标签页）。
        
        流程:
            1. 设置邮箱
            2. 执行注册
            3. 清理资源
        
        返回:
            bool: 注册成功返回 True，失败返回 False
        """
        try:
            if self.setup_email():
                if self.register_cursor():
                    print(f"\n{Fore.GREEN}{EMOJI['success']} {self.translator.get('register.cursor_registration_completed')}...{Style.RESET_ALL}")
                    return True
            return False
        finally:
            # 关闭邮箱标签页
            if hasattr(self, 'temp_email'):
                try:
                    self.temp_email.close()
                except:
                    pass

    def update_cursor_auth(self, email=None, access_token=None, refresh_token=None, auth_type="Auth_0"):
        """
        更新 Cursor 认证信息的便捷函数
        
        封装 CursorAuth 类的功能，用于更新用户的认证信息。
        
        参数:
            email (str): 用户邮箱
            access_token (str): 访问令牌
            refresh_token (str): 刷新令牌
            auth_type (str): 认证类型，默认为 "Auth_0"
        
        返回:
            bool: 更新成功返回 True，失败返回 False
        """
        auth_manager = CursorAuth(translator=self.translator)
        return auth_manager.update_auth(email, access_token, refresh_token, auth_type)

def main(translator=None):
    """
    主函数 - 从 main.py 调用的入口点
    
    创建 CursorRegistration 实例并启动注册流程。
    提供友好的用户界面和错误处理。
    
    参数:
        translator: 翻译器实例，用于多语言支持
    
    返回:
        bool: 注册成功返回 True，失败返回 False
    """
    # 显示注册流程标题和分隔线
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['loading']} {translator.get('register.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # 创建注册实例并启动注册流程
    registration = CursorRegistration(translator)
    registration.start()

    # 显示完成信息并等待用户确认
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['info']} {translator.get('register.press_enter')}...")

if __name__ == "__main__":
    """
    程序入口点
    
    当文件作为脚本直接运行时，从 main.py 导入翻译器并启动注册流程。
    这允许独立测试和运行注册功能。
    """
    from main import translator as main_translator
    main(main_translator)