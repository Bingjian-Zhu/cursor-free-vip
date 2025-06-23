#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor OAuth 认证处理器

该文件实现了 Cursor 编辑器的 OAuth 认证流程，支持多种浏览器和配置文件管理。

主要功能:
1. 自动化浏览器操作进行 OAuth 认证
2. 支持多种浏览器（Chrome、Brave、Edge、Firefox、Opera）
3. 浏览器配置文件选择和管理
4. 跨平台支持（Windows、macOS、Linux）
5. 自动获取和处理认证令牌
6. 完整的错误处理和用户交互

使用方法:
1. 直接运行: python oauth_auth.py
2. 作为模块导入:
   from oauth_auth import OAuthHandler
   handler = OAuthHandler(translator, auth_type)
   success = handler.run_oauth_flow()

支持的认证类型:
- Google OAuth
- GitHub OAuth
- Microsoft OAuth
- 其他第三方 OAuth 提供商

注意事项:
- 需要安装支持的浏览器
- 确保网络连接稳定
- 某些操作可能需要用户手动干预
- 建议关闭其他浏览器实例以避免冲突

依赖模块:
- DrissionPage: 浏览器自动化
- colorama: 彩色终端输出
- cursor_auth: Cursor 认证核心模块
- utils: 工具函数
- config: 配置管理

作者: Cursor Free VIP 项目组
版本: 1.0
"""

import os
from colorama import Fore, Style, init
import time
import random
import webbrowser
import sys
import json
from DrissionPage import ChromiumPage, ChromiumOptions
from cursor_auth import CursorAuth
from utils import get_random_wait_time, get_default_browser_path
from config import get_config
import platform
from get_user_token import get_token_from_cookie

# 初始化 colorama 以支持跨平台彩色输出
init()

# 定义表情符号常量，用于美化终端输出
EMOJI = {
    'START': '🚀',      # 开始操作
    'OAUTH': '🔑',      # OAuth 认证
    'SUCCESS': '✅',    # 成功
    'ERROR': '❌',      # 错误
    'WAIT': '⏳',       # 等待
    'INFO': 'ℹ️',       # 信息
    'WARNING': '⚠️'     # 警告
}

class OAuthHandler:
    """
    OAuth 认证处理器类
    
    该类负责处理 Cursor 编辑器的 OAuth 认证流程，包括浏览器管理、
    配置文件选择、认证流程执行等功能。
    
    主要功能:
    - 自动化浏览器操作
    - 多浏览器支持（Chrome、Brave、Edge、Firefox、Opera）
    - 配置文件管理和选择
    - OAuth 认证流程控制
    - 令牌获取和处理
    - 错误处理和用户交互
    
    属性:
        translator: 翻译器对象，用于多语言支持
        config: 配置对象，包含浏览器和认证设置
        auth_type: 认证类型（如 'google', 'github' 等）
        browser: DrissionPage 浏览器实例
        selected_profile: 选中的浏览器配置文件
    
    使用示例:
        handler = OAuthHandler(translator, 'google')
        success = handler.run_oauth_flow()
        if success:
            print("认证成功")
    """
    
    def __init__(self, translator=None, auth_type=None):
        """
        初始化 OAuth 处理器
        
        参数:
            translator: 翻译器对象，用于多语言支持（可选）
            auth_type: 认证类型，如 'google', 'github', 'microsoft' 等（可选）
        
        注意事项:
            - 会自动加载配置文件
            - 设置浏览器为非无头模式（需要用户交互）
            - 初始化浏览器和配置文件变量
        """
        self.translator = translator  # 翻译器对象，用于多语言支持
        self.config = get_config(translator)  # 加载配置文件
        self.auth_type = auth_type  # 认证类型（google、github 等）
        os.environ['BROWSER_HEADLESS'] = 'False'  # 设置浏览器为非无头模式
        self.browser = None  # DrissionPage 浏览器实例
        self.selected_profile = None  # 选中的浏览器配置文件
        
    def _get_available_profiles(self, user_data_dir):
        """
        获取可用的浏览器配置文件列表及其名称
        
        该方法扫描指定的用户数据目录，读取浏览器的配置文件信息，
        并返回可用配置文件的列表。
        
        参数:
            user_data_dir (str): 浏览器用户数据目录路径
        
        返回:
            list: 包含 (配置文件目录名, 显示名称) 元组的列表
                 例如: [('Default', 'Person 1'), ('Profile 1', 'Work')]
        
        处理流程:
        1. 读取 Local State 文件获取配置文件显示名称
        2. 扫描用户数据目录查找配置文件目录
        3. 匹配目录名和显示名称
        4. 返回排序后的配置文件列表
        
        异常处理:
            如果读取失败，会打印错误信息并返回空列表
        """
        try:
            profiles = []  # 存储配置文件列表
            profile_names = {}  # 存储配置文件名称映射
            
            # 读取 Local State 文件以获取配置文件的显示名称
            local_state_path = os.path.join(user_data_dir, 'Local State')
            if os.path.exists(local_state_path):
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    # 获取配置文件信息缓存
                    info_cache = local_state.get('profile', {}).get('info_cache', {})
                    for profile_dir, info in info_cache.items():
                        # 标准化路径分隔符
                        profile_dir = profile_dir.replace('\\', '/')
                        if profile_dir == 'Default':
                            # 默认配置文件
                            profile_names['Default'] = info.get('name', 'Default')
                        elif profile_dir.startswith('Profile '):
                            # 其他配置文件
                            profile_names[profile_dir] = info.get('name', profile_dir)

            # 扫描用户数据目录获取配置文件目录列表
            for item in os.listdir(user_data_dir):
                # 检查是否为有效的配置文件目录
                if item == 'Default' or (item.startswith('Profile ') and os.path.isdir(os.path.join(user_data_dir, item))):
                    # 添加到配置文件列表，使用显示名称或目录名
                    profiles.append((item, profile_names.get(item, item)))
            return sorted(profiles)  # 返回排序后的配置文件列表
        except Exception as e:
            # 错误处理：打印错误信息并返回空列表
            error_msg = self.translator.get('chrome_profile.error_loading', error=str(e)) if self.translator else f'Error loading Chrome profiles: {e}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return []

    def _select_profile(self):
        """
        允许用户选择要使用的浏览器配置文件
        
        该方法显示可用的浏览器配置文件列表，让用户选择一个用于 OAuth 认证。
        支持多种浏览器类型，并提供友好的用户交互界面。
        
        返回:
            bool: 如果用户成功选择配置文件返回 True，选择退出返回 False
        
        处理流程:
        1. 从配置中获取浏览器类型
        2. 显示选择提示信息
        3. 加载可用的配置文件列表
        4. 显示配置文件选项
        5. 处理用户输入和选择
        6. 设置选中的配置文件
        
        异常处理:
            如果出现任何错误，会自动使用默认配置文件
        """
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type_display = browser_type.capitalize()  # 首字母大写用于显示
            
            # 显示配置文件选择提示
            if self.translator:
                # 使用翻译器显示多语言提示
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.select_profile', browser=browser_type_display)}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{self.translator.get('oauth.profile_list', browser=browser_type_display)}{Style.RESET_ALL}")
            else:
                # 使用英文提示
                print(f"{Fore.CYAN}{EMOJI['INFO']} Select {browser_type_display} profile to use:{Style.RESET_ALL}")
                print(f"Available {browser_type_display} profiles:")
            
            # 获取指定浏览器类型的用户数据目录
            user_data_dir = self._get_user_data_directory()
            
            # 从选定的浏览器类型加载可用的配置文件
            try:
                local_state_file = os.path.join(user_data_dir, "Local State")
                if os.path.exists(local_state_file):
                    # 读取浏览器的本地状态文件
                    with open(local_state_file, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                    # 获取配置文件信息缓存
                    profiles_data = state_data.get('profile', {}).get('info_cache', {})
                    
                    # 创建可用配置文件列表
                    profiles = []
                    for profile_id, profile_info in profiles_data.items():
                        name = profile_info.get('name', profile_id)  # 获取配置文件显示名称
                        # 标记默认配置文件
                        if profile_id.lower() == 'default':
                            name = f"{name} (Default)"
                        profiles.append((profile_id, name))
                    
                    # 按名称排序配置文件
                    profiles.sort(key=lambda x: x[1])
                    
                    # 显示可用的配置文件选项
                    if self.translator:
                        print(f"{Fore.CYAN}0. {self.translator.get('menu.exit')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}0. Exit{Style.RESET_ALL}")
                    
                    # 显示配置文件列表（从1开始编号）
                    for i, (profile_id, name) in enumerate(profiles, 1):
                        print(f"{Fore.CYAN}{i}. {name}{Style.RESET_ALL}")
                    
                    # 获取用户的选择
                    max_choice = len(profiles)
                    choice_prompt = self.translator.get('menu.input_choice', choices=f'0-{max_choice}') if self.translator else f'Please enter your choice (0-{max_choice})'
                    choice_str = input(f"\n{Fore.CYAN}{choice_prompt}{Style.RESET_ALL}")
                    
                    try:
                        choice = int(choice_str)  # 将用户输入转换为整数
                        if choice == 0:
                            # 用户选择退出
                            return False
                        elif 1 <= choice <= max_choice:
                            # 用户选择了有效的配置文件
                            selected_profile = profiles[choice-1][0]  # 获取配置文件ID
                            self.selected_profile = selected_profile  # 保存选中的配置文件
                            
                            # 显示选择成功信息
                            if self.translator:
                                success_msg = self.translator.get('oauth.profile_selected', profile=selected_profile)
                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {success_msg}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Selected profile: {selected_profile}{Style.RESET_ALL}")
                            return True
                        else:
                            # 用户输入的数字超出范围
                            if self.translator:
                                error_msg = self.translator.get('oauth.invalid_selection')
                                print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.RED}{EMOJI['ERROR']} Invalid selection. Please try again.{Style.RESET_ALL}")
                            return self._select_profile()  # 递归调用重新选择
                    except ValueError:
                        # 用户输入的不是有效数字
                        if self.translator:
                            error_msg = self.translator.get('oauth.invalid_selection')
                            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}{EMOJI['ERROR']} Invalid selection. Please try again.{Style.RESET_ALL}")
                        return self._select_profile()  # 递归调用重新选择
                else:
                    # 没有找到 Local State 文件，使用默认配置文件
                    warning_msg = self.translator.get('oauth.no_profiles', browser=browser_type_display) if self.translator else f'No {browser_type_display} profiles found'
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")
                    self.selected_profile = "Default"  # 设置为默认配置文件
                    return True
                    
            except Exception as e:
                # 加载配置文件时出错，使用默认配置文件
                error_msg = self.translator.get('oauth.error_loading', error=str(e), browser=browser_type_display) if self.translator else f'Error loading {browser_type_display} profiles: {str(e)}'
                print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
                self.selected_profile = "Default"  # 设置为默认配置文件
                return True
            
        except Exception as e:
            # 配置文件选择过程中的一般性错误，使用默认配置文件
            error_msg = self.translator.get('oauth.profile_selection_error', error=str(e)) if self.translator else f'Error during profile selection: {str(e)}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            self.selected_profile = "Default"  # 设置为默认配置文件
            return True

    def setup_browser(self):
        """
        为 OAuth 认证流程设置浏览器
        
        该方法负责初始化和配置浏览器实例，包括平台检测、浏览器路径获取、
        配置文件选择、浏览器选项配置等步骤。
        
        返回:
            bool: 如果浏览器设置成功返回 True，否则返回 False
        
        处理流程:
        1. 检测操作系统平台
        2. 获取浏览器类型和路径
        3. 验证浏览器可用性
        4. 关闭现有浏览器进程
        5. 选择浏览器配置文件
        6. 配置浏览器选项
        7. 启动浏览器实例
        
        异常处理:
            如果任何步骤失败，会显示详细的错误信息和解决建议
        """
        try:
            # 显示浏览器设置初始化信息
            init_msg = self.translator.get('oauth.initializing_browser_setup') if self.translator else 'Initializing browser setup...'
            print(f"{Fore.CYAN}{EMOJI['INFO']} {init_msg}{Style.RESET_ALL}")
            
            # 平台特定的初始化
            platform_name = platform.system().lower()
            platform_msg = self.translator.get('oauth.detected_platform', platform=platform_name) if self.translator else f'Detected platform: {platform_name}'
            print(f"{Fore.CYAN}{EMOJI['INFO']} {platform_msg}{Style.RESET_ALL}")
            
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            
            # 获取浏览器路径和用户数据目录
            user_data_dir = self._get_user_data_directory()
            browser_path = self._get_browser_path()
            
            # 验证浏览器路径是否有效
            if not browser_path:
                # 构建详细的错误信息，包含支持的浏览器列表
                no_browser_msg = self.translator.get('oauth.no_compatible_browser_found') if self.translator else 'No compatible browser found. Please install Google Chrome or Chromium.'
                supported_msg = self.translator.get('oauth.supported_browsers', platform=platform_name) if self.translator else f'Supported browsers for {platform_name}:'
                error_msg = (
                    f"{no_browser_msg}" + 
                    "\n" +
                    f"{supported_msg}\n" + 
                    "- Windows: Google Chrome, Chromium\n" +
                    "- macOS: Google Chrome, Chromium\n" +
                    "- Linux: Google Chrome, Chromium, google-chrome-stable"
                )
                raise Exception(error_msg)
            
            # 显示找到的浏览器数据目录
            data_dir_msg = self.translator.get('oauth.found_browser_data_directory', path=user_data_dir) if self.translator else f'Found browser data directory: {user_data_dir}'
            print(f"{Fore.CYAN}{EMOJI['INFO']} {data_dir_msg}{Style.RESET_ALL}")
            
            # 显示关于关闭浏览器的警告 - 使用动态提示
            if self.translator:
                warning_msg = self.translator.get('oauth.warning_browser_close', browser=browser_type)
            else:
                warning_msg = f'Warning: This will close all running {browser_type} processes'
            
            print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")
            
            # 获取用户确认
            continue_prompt = self.translator.get('menu.continue_prompt', choices='y/N') if self.translator else 'Continue? (y/N)'
            choice = input(f"{Fore.YELLOW} {continue_prompt} {Style.RESET_ALL}").lower()
            if choice != 'y':
                # 用户取消操作
                cancel_msg = self.translator.get('menu.operation_cancelled_by_user') if self.translator else 'Operation cancelled by user'
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {cancel_msg}{Style.RESET_ALL}")
                return False

            # 关闭现有的浏览器进程
            self._kill_browser_processes()
            
            # 让用户选择配置文件
            if not self._select_profile():
                # 用户取消了配置文件选择
                cancel_msg = self.translator.get('menu.operation_cancelled_by_user') if self.translator else 'Operation cancelled by user'
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {cancel_msg}{Style.RESET_ALL}")
                return False
            
            # 配置浏览器选项
            co = self._configure_browser_options(browser_path, user_data_dir, self.selected_profile)
            
            # 启动浏览器
            start_msg = self.translator.get('oauth.starting_browser', path=browser_path) if self.translator else f'Starting browser at: {browser_path}'
            print(f"{Fore.CYAN}{EMOJI['INFO']} {start_msg}{Style.RESET_ALL}")
            self.browser = ChromiumPage(co)
            
            # 验证浏览器是否成功启动
            if not self.browser:
                failed_msg = self.translator.get('oauth.browser_failed_to_start') if self.translator else 'Failed to initialize browser instance'
                raise Exception(failed_msg)
            
            # 显示设置完成信息
            success_msg = self.translator.get('oauth.browser_setup_completed') if self.translator else 'Browser setup completed successfully'
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {success_msg}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            # 浏览器设置失败的异常处理
            error_msg = self.translator.get('oauth.browser_setup_failed', error=str(e)) if self.translator else f'Browser setup failed: {str(e)}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            
            # 根据具体错误类型提供解决建议
            if "DevToolsActivePort file doesn't exist" in str(e):
                # DevTools 端口文件不存在错误
                sudo_msg = self.translator.get('oauth.try_running_without_sudo_admin') if self.translator else 'Try running without sudo/administrator privileges'
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {sudo_msg}{Style.RESET_ALL}")
            elif "Chrome failed to start" in str(e):
                # Chrome 启动失败错误
                install_msg = self.translator.get('oauth.make_sure_chrome_chromium_is_properly_installed') if self.translator else 'Make sure Chrome/Chromium is properly installed'
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {install_msg}{Style.RESET_ALL}")
                # Linux 系统特定的安装建议
                if platform_name == 'linux':
                    linux_install_msg = self.translator.get('oauth.try_install_chromium') if self.translator else 'Try: sudo apt install chromium-browser'
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {linux_install_msg}{Style.RESET_ALL}")
            return False

    def _kill_browser_processes(self):
        """
        根据平台和浏览器类型关闭现有的浏览器进程
        
        该方法会根据当前配置的浏览器类型和操作系统平台，
        关闭所有相关的浏览器进程，以确保新的浏览器实例能够正常启动。
        
        处理流程:
        1. 获取配置的浏览器类型
        2. 根据平台和浏览器类型确定要关闭的进程名称
        3. 执行平台特定的进程关闭命令
        4. 等待进程完全关闭
        
        支持的浏览器:
        - Chrome/Chromium
        - Brave Browser
        - Microsoft Edge
        - Firefox
        - Opera
        
        异常处理:
            如果关闭进程失败，会显示警告信息但不会中断程序执行
        """
        try:
            # 从配置中获取浏览器类型
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()  # 转换为小写以便匹配
            
            # 根据浏览器类型和平台定义要关闭的进程名称
            browser_processes = {
                'chrome': {
                    'win': ['chrome.exe', 'chromium.exe'],  # Windows 下的 Chrome 进程
                    'linux': ['chrome', 'chromium', 'chromium-browser', 'google-chrome-stable'],  # Linux 下的 Chrome 进程
                    'mac': ['Chrome', 'Chromium']  # macOS 下的 Chrome 进程
                },
                'brave': {
                    'win': ['brave.exe'],  # Windows 下的 Brave 进程
                    'linux': ['brave', 'brave-browser'],  # Linux 下的 Brave 进程
                    'mac': ['Brave Browser']  # macOS 下的 Brave 进程
                },
                'edge': {
                    'win': ['msedge.exe'],  # Windows 下的 Edge 进程
                    'linux': ['msedge'],  # Linux 下的 Edge 进程
                    'mac': ['Microsoft Edge']  # macOS 下的 Edge 进程
                },
                'firefox': {
                    'win': ['firefox.exe'],  # Windows 下的 Firefox 进程
                    'linux': ['firefox'],  # Linux 下的 Firefox 进程
                    'mac': ['Firefox']  # macOS 下的 Firefox 进程
                },
                'opera': {
                    'win': ['opera.exe', 'launcher.exe'],  # Windows 下的 Opera 进程
                    'linux': ['opera'],  # Linux 下的 Opera 进程
                    'mac': ['Opera']  # macOS 下的 Opera 进程
                }
            }
            
            # 获取当前操作系统平台类型
            if os.name == 'nt':
                platform_type = 'win'  # Windows 系统
            elif sys.platform == 'darwin':
                platform_type = 'mac'  # macOS 系统
            else:
                platform_type = 'linux'  # Linux 系统
            
            # 获取要关闭的进程列表，如果找不到指定浏览器则使用 Chrome 的进程列表
            processes = browser_processes.get(browser_type, browser_processes['chrome']).get(platform_type, [])
            
            # 显示正在关闭浏览器进程的信息
            if self.translator:
                kill_msg = self.translator.get('oauth.killing_browser_processes', browser=browser_type)
                print(f"{Fore.CYAN}{EMOJI['INFO']} {kill_msg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}{EMOJI['INFO']} Killing {browser_type} processes...{Style.RESET_ALL}")
            
            # 根据平台执行相应的进程关闭命令
            if os.name == 'nt':  # Windows 系统
                for proc in processes:
                    # 使用 taskkill 命令强制关闭进程
                    os.system(f'taskkill /f /im {proc} >nul 2>&1')
            else:  # Linux/Mac 系统
                for proc in processes:
                    # 使用 pkill 命令关闭进程
                    os.system(f'pkill -f {proc} >/dev/null 2>&1')
            
            time.sleep(1)  # 等待进程完全关闭
        except Exception as e:
            # 关闭进程失败的警告处理
            warning_msg = self.translator.get('oauth.warning_could_not_kill_existing_browser_processes', error=str(e)) if self.translator else f'Warning: Could not kill existing browser processes: {e}'
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {warning_msg}{Style.RESET_ALL}")

    def _get_user_data_directory(self):
        """
        根据浏览器类型和平台获取默认的用户数据目录
        
        该方法会从配置文件中读取浏览器类型，然后根据操作系统和浏览器类型
        返回相应的用户数据目录路径。支持多种浏览器和操作系统。
        
        Returns:
            str: 用户数据目录的绝对路径
        """
        try:
            # 从配置文件中获取浏览器类型，默认为 Chrome
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()  # 转换为小写以便比较
            
            # 根据操作系统和浏览器类型定义用户数据目录映射
            if os.name == 'nt':  # Windows 系统
                user_data_dirs = {
                    'chrome': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
                    'brave': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'User Data'),
                    'edge': os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data'),
                    'firefox': os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles'),
                    'opera': os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera Stable'),
                    'operagx': os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera GX Stable')
                }
            elif sys.platform == 'darwin':  # macOS 系统
                user_data_dirs = {
                    'chrome': os.path.expanduser('~/Library/Application Support/Google/Chrome'),
                    'brave': os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
                    'edge': os.path.expanduser('~/Library/Application Support/Microsoft Edge'),
                    'firefox': os.path.expanduser('~/Library/Application Support/Firefox/Profiles'),
                    'opera': os.path.expanduser('~/Library/Application Support/com.operasoftware.Opera'),
                    'operagx': os.path.expanduser('~/Library/Application Support/com.operasoftware.OperaGX')
                }
            else:  # Linux 系统
                user_data_dirs = {
                    'chrome': os.path.expanduser('~/.config/google-chrome'),
                    'brave': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser'),
                    'edge': os.path.expanduser('~/.config/microsoft-edge'),
                    'firefox': os.path.expanduser('~/.mozilla/firefox'),
                    'opera': os.path.expanduser('~/.config/opera'),
                    'operagx': os.path.expanduser('~/.config/opera-gx')
                }
            
            # 获取指定浏览器的用户数据目录
            user_data_dir = user_data_dirs.get(browser_type)
            
            # 检查目录是否存在
            if user_data_dir and os.path.exists(user_data_dir):
                # 找到用户数据目录，显示成功信息
                success_msg = self.translator.get('oauth.found_browser_user_data_dir', browser=browser_type, path=user_data_dir) if self.translator else f'Found {browser_type} user data directory: {user_data_dir}'
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {success_msg}{Style.RESET_ALL}")
                return user_data_dir
            else:
                # 未找到指定浏览器的用户数据目录，显示警告并回退到 Chrome
                warning_msg = self.translator.get('oauth.user_data_dir_not_found', browser=browser_type, path=user_data_dir) if self.translator else f'{browser_type} user data directory not found at {user_data_dir}, will try Chrome instead'
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")
                return user_data_dirs['chrome']  # 回退到 Chrome 目录
            
        except Exception as e:
            # 获取用户数据目录时发生错误
            error_msg = self.translator.get('oauth.error_getting_user_data_directory', error=str(e)) if self.translator else f'Error getting user data directory: {e}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            
            # 在出错时提供一个默认的 Chrome 目录
            if os.name == 'nt':
                return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
            elif sys.platform == 'darwin':
                return os.path.expanduser('~/Library/Application Support/Google/Chrome')
            else:
                return os.path.expanduser('~/.config/google-chrome')

    def _get_browser_path(self):
        """
        根据平台和选定的浏览器类型获取合适的浏览器路径
        
        该方法会按以下顺序查找浏览器：
        1. 检查配置文件中是否有明确指定的浏览器路径
        2. 尝试获取默认的浏览器路径
        3. 在常见安装位置搜索浏览器
        4. 如果找不到指定浏览器，回退到 Chrome
        
        Returns:
            str: 浏览器可执行文件的绝对路径，如果找不到则返回 None
        """
        try:
            # 从配置文件中获取浏览器类型，默认为 Chrome
            config = get_config(self.translator)
            browser_type = config.get('Browser', 'default_browser', fallback='chrome')
            browser_type = browser_type.lower()  # 转换为小写以便比较
            
            # 首先检查配置文件中是否有明确指定的浏览器路径
            browser_path = config.get('Browser', f'{browser_type}_path', fallback=None)
            if browser_path and os.path.exists(browser_path):
                # 使用配置文件中指定的浏览器路径
                success_msg = self.translator.get('oauth.using_configured_browser_path', browser=browser_type, path=browser_path) if self.translator else f'Using configured {browser_type} path: {browser_path}'
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {success_msg}{Style.RESET_ALL}")
                return browser_path
            
            # 尝试获取系统默认的浏览器路径
            browser_path = get_default_browser_path(browser_type)
            if browser_path and os.path.exists(browser_path):
                return browser_path
            
            # 显示正在搜索替代浏览器安装的信息
            search_msg = self.translator.get('oauth.searching_for_alternative_browser_installations') if self.translator else 'Searching for alternative browser installations...'
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {search_msg}{Style.RESET_ALL}")
            
            # 如果未找到配置中指定的浏览器，则在常见位置搜索浏览器
            if os.name == 'nt':  # Windows 系统
                possible_paths = []  # 存储可能的浏览器路径列表
                
                if browser_type == 'brave':
                    # Brave 浏览器在 Windows 下的常见安装路径
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
                    ]
                elif browser_type == 'edge':
                    # Microsoft Edge 浏览器在 Windows 下的常见安装路径
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe')
                    ]
                elif browser_type == 'firefox':
                    # Firefox 浏览器在 Windows 下的常见安装路径
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Mozilla Firefox', 'firefox.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Mozilla Firefox', 'firefox.exe')
                    ]
                elif browser_type == 'opera':
                    # Opera 浏览器（包括 Opera GX）在 Windows 下的常见安装路径
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'launcher.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera', 'opera.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'launcher.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Opera GX', 'opera.exe')
                    ]
                else:  # 默认为 Chrome
                    # Google Chrome 浏览器在 Windows 下的常见安装路径
                    possible_paths = [
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
                    ]
                
            elif sys.platform == 'darwin':  # macOS 系统
                possible_paths = []  # 存储可能的浏览器路径列表
                
                if browser_type == 'brave':
                    # Brave 浏览器在 macOS 下的安装路径
                    possible_paths = ['/Applications/Brave Browser.app/Contents/MacOS/Brave Browser']
                elif browser_type == 'edge':
                    # Microsoft Edge 浏览器在 macOS 下的安装路径
                    possible_paths = ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
                elif browser_type == 'firefox':
                    # Firefox 浏览器在 macOS 下的安装路径
                    possible_paths = ['/Applications/Firefox.app/Contents/MacOS/firefox']
                else:  # 默认为 Chrome
                    # Google Chrome 浏览器在 macOS 下的安装路径
                    possible_paths = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
                
            else:  # Linux 系统
                possible_paths = []  # 存储可能的浏览器路径列表
                
                if browser_type == 'brave':
                    # Brave 浏览器在 Linux 下的常见安装路径
                    possible_paths = ['/usr/bin/brave-browser', '/usr/bin/brave']
                elif browser_type == 'edge':
                    # Microsoft Edge 浏览器在 Linux 下的安装路径
                    possible_paths = ['/usr/bin/microsoft-edge']
                elif browser_type == 'firefox':
                    # Firefox 浏览器在 Linux 下的安装路径
                    possible_paths = ['/usr/bin/firefox']
                else:  # 默认为 Chrome
                    # Google Chrome 和 Chromium 浏览器在 Linux 下的常见安装路径
                    possible_paths = [
                        '/usr/bin/google-chrome-stable',  # 优先检查 google-chrome-stable
                        '/usr/bin/google-chrome',
                        '/usr/bin/chromium',
                        '/usr/bin/chromium-browser'
                    ]
                
            # 遍历检查每个可能的浏览器路径
            for path in possible_paths:
                if os.path.exists(path):
                    # 找到可用的浏览器，显示成功信息并返回路径
                    found_msg = self.translator.get('oauth.found_browser_at', path=path) if self.translator else f'Found browser at: {path}'
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {found_msg}{Style.RESET_ALL}")
                    return path
            
            # 如果找不到指定的浏览器，则尝试回退到 Chrome
            if browser_type != 'chrome':
                warning_msg = self.translator.get('oauth.browser_not_found_trying_chrome', browser=browser_type) if self.translator else f'Could not find {browser_type}, trying Chrome instead'
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")
                return self._get_chrome_path()  # 调用获取 Chrome 路径的方法
            
            # 如果连 Chrome 也找不到，返回 None
            return None
            
        except Exception as e:
            # 查找浏览器路径时发生错误
            error_msg = self.translator.get('oauth.error_finding_browser_path', error=str(e)) if self.translator else f'Error finding browser path: {e}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return None

    def _configure_browser_options(self, browser_path, user_data_dir, active_profile):
        """
        根据平台配置浏览器选项
        
        该方法会创建并配置 ChromiumOptions 对象，设置浏览器路径、用户数据目录、
        配置文件以及各种启动参数，包括平台特定的优化选项。
        
        Args:
            browser_path (str): 浏览器可执行文件的路径
            user_data_dir (str): 用户数据目录路径
            active_profile (str): 要使用的配置文件名称
            
        Returns:
            ChromiumOptions: 配置好的浏览器选项对象
            
        Raises:
            Exception: 配置浏览器选项时发生错误
        """
        try:
            # 创建 ChromiumOptions 对象
            co = ChromiumOptions()
            
            # 设置浏览器路径和用户数据目录
            co.set_paths(browser_path=browser_path, user_data_path=user_data_dir)
            
            # 设置要使用的配置文件目录
            co.set_argument(f'--profile-directory={active_profile}')
            
            # 基础选项配置
            co.set_argument('--no-first-run')  # 跳过首次运行向导
            co.set_argument('--no-default-browser-check')  # 不检查默认浏览器
            co.set_argument('--disable-gpu')  # 禁用 GPU 加速
            co.set_argument('--remote-debugging-port=9222')  # 明确指定远程调试端口
            
            # 根据操作系统平台设置特定选项
            if sys.platform.startswith('linux'):  # Linux 系统
                co.set_argument('--no-sandbox')  # 禁用沙盒模式
                co.set_argument('--disable-dev-shm-usage')  # 禁用 /dev/shm 使用
                co.set_argument('--disable-setuid-sandbox')  # 禁用 setuid 沙盒
            elif sys.platform == 'darwin':  # macOS 系统
                co.set_argument('--disable-gpu-compositing')  # 禁用 GPU 合成
            elif os.name == 'nt':  # Windows 系统
                co.set_argument('--disable-features=TranslateUI')  # 禁用翻译界面
                co.set_argument('--disable-features=RendererCodeIntegrity')  # 禁用渲染器代码完整性
            
            return co
            
        except Exception as e:
            # 配置浏览器选项时发生错误
            error_msg = self.translator.get('oauth.error_configuring_browser_options', error=str(e)) if self.translator else f'Error configuring browser options: {e}'
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            raise

    def _fix_chrome_permissions(self, user_data_dir):
        """
        修复 Chrome 用户数据目录的权限
        
        该方法主要用于 macOS 系统，修复 Chrome 用户数据目录的文件权限问题。
        在某些情况下，Chrome 目录的权限可能不正确，导致浏览器无法正常访问配置文件。
        
        Args:
            user_data_dir (str): 用户数据目录路径（当前未使用，但保留以备将来扩展）
        """
        try:
            if sys.platform == 'darwin':  # 仅在 macOS 系统上执行权限修复
                import subprocess
                import pwd
                
                # 获取当前用户名
                current_user = pwd.getpwuid(os.getuid()).pw_name
                
                # 获取 Chrome 用户数据目录路径
                chrome_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
                
                # 检查 Chrome 目录是否存在
                if os.path.exists(chrome_dir):
                    # 递归修改目录权限，给用户添加读写执行权限
                    subprocess.run(['chmod', '-R', 'u+rwX', chrome_dir])
                    
                    # 递归修改目录所有者为当前用户和 staff 组
                    subprocess.run(['chown', '-R', f'{current_user}:staff', chrome_dir])
                    
                    # 显示权限修复成功信息
                    success_msg = self.translator.get('oauth.chrome_permissions_fixed') if self.translator else 'Fixed Chrome user data directory permissions'
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {success_msg}{Style.RESET_ALL}")
        except Exception as e:
            # 权限修复失败的警告处理
            warning_msg = self.translator.get('oauth.chrome_permissions_fix_failed', error=str(e)) if self.translator else f'Failed to fix Chrome permissions: {str(e)}'
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {warning_msg}{Style.RESET_ALL}")

    def handle_google_auth(self):
        """Handle Google OAuth authentication"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.google_start') if self.translator else 'Starting Google OAuth authentication...'}{Style.RESET_ALL}")
            
            # Setup browser
            if not self.setup_browser():
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.browser_failed') if self.translator else 'Browser failed to initialize'}{Style.RESET_ALL}")
                return False, None
            
            # Get user data directory for later use
            user_data_dir = self._get_user_data_directory()
            
            # Navigate to auth URL
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_authentication_page') if self.translator else 'Navigating to authentication page...'}{Style.RESET_ALL}")
                self.browser.get("https://authenticator.cursor.sh/sign-up")
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Look for Google auth button
                selectors = [
                    "//a[contains(@href,'GoogleOAuth')]",
                    "//a[contains(@class,'auth-method-button') and contains(@href,'GoogleOAuth')]",
                    "(//a[contains(@class,'auth-method-button')])[1]"  # First auth button as fallback
                ]
                
                auth_btn = None
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=2)
                        if auth_btn and auth_btn.is_displayed():
                            break
                    except:
                        continue
                
                if not auth_btn:
                    raise Exception("Could not find Google authentication button")
                
                # Click the button and wait for page load
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_google_authentication') if self.translator else 'Starting Google authentication...'}{Style.RESET_ALL}")
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Check if we're on account selection page
                if "accounts.google.com" in self.browser.url:
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue...'}{Style.RESET_ALL}")
                    
                    # 获取配置中是否启用 alert 选项
                    config = get_config(self.translator)
                    show_alert = config.getboolean('OAuth', 'show_selection_alert', fallback=False)
                    
                    if show_alert:
                        alert_message = self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue with Cursor authentication'
                        try:
                            self.browser.run_js(f"""
                            alert('{alert_message}');
                            """)
                        except:
                            pass  # Alert is optional
                
                # Wait for authentication to complete
                auth_info = self._wait_for_auth()
                if not auth_info:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.timeout') if self.translator else 'Timeout'}{Style.RESET_ALL}")
                    return False, None
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.success') if self.translator else 'Success'}{Style.RESET_ALL}")
                return True, auth_info
                
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_error', error=str(e)) if self.translator else f'Authentication error: {str(e)}'}{Style.RESET_ALL}")
                return False, None
            finally:
                try:
                    if self.browser:
                        self.browser.quit()
                        # Fix Chrome permissions after browser is closed
                        self._fix_chrome_permissions(user_data_dir)
                except:
                    pass
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed', error=str(e))}{Style.RESET_ALL}")
            return False, None

    def _wait_for_auth(self):
        """Wait for authentication to complete and extract auth info"""
        try:
            max_wait = 300  # 5 minutes
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('oauth.waiting_for_authentication', timeout='5 minutes') if self.translator else 'Waiting for authentication (timeout: 5 minutes)'}{Style.RESET_ALL}")
            
            while time.time() - start_time < max_wait:
                try:
                    # Check for authentication cookies
                    cookies = self.browser.cookies()
                    
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            value = cookie.get("value", "")
                            token = get_token_from_cookie(value, self.translator)
                            if token:
                                # Get email from settings page
                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.authentication_successful_getting_account_info') if self.translator else 'Authentication successful, getting account info...'}{Style.RESET_ALL}")
                                self.browser.get("https://www.cursor.com/settings")
                                time.sleep(3)
                                
                                email = None
                                try:
                                    email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                    if email_element:
                                        email = email_element.text
                                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=email) if self.translator else f'Found email: {email}'}{Style.RESET_ALL}")
                                except:
                                    email = "user@cursor.sh"  # Fallback email
                                
                                # Check usage count
                                try:
                                    usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                    if usage_element:
                                        usage_text = usage_element.text
                                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                        
                                        def check_usage_limits(usage_str):
                                            try:
                                                parts = usage_str.split('/')
                                                if len(parts) != 2:
                                                    return False
                                                current = int(parts[0].strip())
                                                limit = int(parts[1].strip())
                                                return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                            except:
                                                return False

                                        if check_usage_limits(usage_text):
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                            if self._delete_current_account():
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                if self.auth_type == "google":
                                                    return self.handle_google_auth()
                                                else:
                                                    return self.handle_github_auth()
                                            else:
                                                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                        else:
                                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                except Exception as e:
                                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                
                                return {"email": email, "token": token}
                    
                    # Also check URL as backup
                    if "cursor.com/settings" in self.browser.url:
                        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.detected_successful_login') if self.translator else 'Detected successful login'}{Style.RESET_ALL}")
                    
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.waiting_for_authentication', error=str(e)) if self.translator else f'Waiting for authentication... ({str(e)})'}{Style.RESET_ALL}")
                
                time.sleep(check_interval)
            
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_timeout') if self.translator else 'Authentication timeout'}{Style.RESET_ALL}")
            return None
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.error_waiting_for_authentication', error=str(e)) if self.translator else f'Error while waiting for authentication: {str(e)}'}{Style.RESET_ALL}")
            return None
        
    def handle_github_auth(self):
        """Handle GitHub OAuth authentication"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.github_start')}{Style.RESET_ALL}")
            
            # Setup browser
            if not self.setup_browser():
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.browser_failed', error=str(e)) if self.translator else 'Browser failed to initialize'}{Style.RESET_ALL}")
                return False, None
            
            # Navigate to auth URL
            try:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_authentication_page') if self.translator else 'Navigating to authentication page...'}{Style.RESET_ALL}")
                self.browser.get("https://authenticator.cursor.sh/sign-up")
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Look for GitHub auth button
                selectors = [
                    "//a[contains(@href,'GitHubOAuth')]",
                    "//a[contains(@class,'auth-method-button') and contains(@href,'GitHubOAuth')]",
                    "(//a[contains(@class,'auth-method-button')])[2]"  # Second auth button as fallback
                ]
                
                auth_btn = None
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=2)
                        if auth_btn and auth_btn.is_displayed():
                            break
                    except:
                        continue
                
                if not auth_btn:
                    raise Exception("Could not find GitHub authentication button")
                
                # Click the button and wait for page load
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_github_authentication') if self.translator else 'Starting GitHub authentication...'}{Style.RESET_ALL}")
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Wait for authentication to complete
                auth_info = self._wait_for_auth()
                if not auth_info:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.timeout') if self.translator else 'Timeout'}{Style.RESET_ALL}")
                    return False, None
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.success')}{Style.RESET_ALL}")
                return True, auth_info
                
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_error', error=str(e)) if self.translator else f'Authentication error: {str(e)}'}{Style.RESET_ALL}")
                return False, None
            finally:
                try:
                    if self.browser:
                        self.browser.quit()
                except:
                    pass
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed', error=str(e))}{Style.RESET_ALL}")
            return False, None
        
    def _handle_oauth(self, auth_type):
        """Handle OAuth authentication for both Google and GitHub
        
        Args:
            auth_type (str): Type of authentication ('google' or 'github')
        """
        try:
            if not self.setup_browser():
                return False, None
                
            # Navigate to auth URL
            self.browser.get("https://authenticator.cursor.sh/sign-up")
            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
            
            # Set selectors based on auth type
            if auth_type == "google":
                selectors = [
                    "//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'][contains(@href,'GoogleOAuth')]",
                    "(//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'])[1]"
                ]
            else:  # github
                selectors = [
                    "(//a[@class='rt-reset rt-BaseButton rt-r-size-3 rt-variant-surface rt-high-contrast rt-Button auth-method-button_AuthMethodButton__irESX'])[2]"
                ]
            
            # Wait for the button to be available
            auth_btn = None
            max_button_wait = 30  # 30 seconds
            button_start_time = time.time()
            
            while time.time() - button_start_time < max_button_wait:
                for selector in selectors:
                    try:
                        auth_btn = self.browser.ele(f"xpath:{selector}", timeout=1)
                        if auth_btn and auth_btn.is_displayed():
                            break
                    except:
                        continue
                if auth_btn:
                    break
                time.sleep(1)
            
            if auth_btn:
                # Click the button and wait for page load
                auth_btn.click()
                time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                
                # Check if we're on account selection page
                if auth_type == "google" and "accounts.google.com" in self.browser.url:
                    alert_message = self.translator.get('oauth.please_select_your_google_account_to_continue') if self.translator else 'Please select your Google account to continue with Cursor authentication'
                    try:
                        self.browser.run_js(f"""
                        alert('{alert_message}');
                        """)
                    except Exception as e:
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.alert_display_failed', error=str(e)) if self.translator else f'Alert display failed: {str(e)}'}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.please_select_your_google_account_manually_to_continue_with_cursor_authentication') if self.translator else 'Please select your Google account manually to continue with Cursor authentication...'}{Style.RESET_ALL}")
                
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.waiting_for_authentication_to_complete') if self.translator else 'Waiting for authentication to complete...'}{Style.RESET_ALL}")
                
                # Wait for authentication to complete
                max_wait = 300  # 5 minutes
                start_time = time.time()
                last_url = self.browser.url
                
                print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('oauth.checking_authentication_status') if self.translator else 'Checking authentication status...'}{Style.RESET_ALL}")
                
                while time.time() - start_time < max_wait:
                    try:
                        # Check for authentication cookies
                        cookies = self.browser.cookies()
                        
                        for cookie in cookies:
                            if cookie.get("name") == "WorkosCursorSessionToken":
                                value = cookie.get("value", "")
                                token = get_token_from_cookie(value, self.translator)
                                if token:
                                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.authentication_successful') if self.translator else 'Authentication successful!'}{Style.RESET_ALL}")
                                    # Navigate to settings page
                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.navigating_to_settings_page') if self.translator else 'Navigating to settings page...'}{Style.RESET_ALL}")
                                    self.browser.get("https://www.cursor.com/settings")
                                    time.sleep(3)  # Wait for settings page to load
                                    
                                    # Get email from settings page
                                    try:
                                        email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                        if email_element:
                                            actual_email = email_element.text
                                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=actual_email) if self.translator else f'Found email: {actual_email}'}{Style.RESET_ALL}")
                                    except Exception as e:
                                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_find_email', error=str(e)) if self.translator else f'Could not find email: {str(e)}'}{Style.RESET_ALL}")
                                        actual_email = "user@cursor.sh"
                                    
                                    # Check usage count
                                    try:
                                        usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                        if usage_element:
                                            usage_text = usage_element.text
                                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                            
                                            def check_usage_limits(usage_str):
                                                try:
                                                    parts = usage_str.split('/')
                                                    if len(parts) != 2:
                                                        return False
                                                    current = int(parts[0].strip())
                                                    limit = int(parts[1].strip())
                                                    return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                                except:
                                                    return False

                                            if check_usage_limits(usage_text):
                                                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                                if self._delete_current_account():
                                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                    if self.auth_type == "google":
                                                        return self.handle_google_auth()
                                                    else:
                                                        return self.handle_github_auth()
                                                else:
                                                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                            else:
                                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                    except Exception as e:
                                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                    
                                    # Remove the browser stay open prompt and input wait
                                    return True, {"email": actual_email, "token": token}
                        
                        # Also check URL as backup
                        current_url = self.browser.url
                        if "cursor.com/settings" in current_url:
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.already_on_settings_page') if self.translator else 'Already on settings page!'}{Style.RESET_ALL}")
                            time.sleep(1)
                            cookies = self.browser.cookies()
                            for cookie in cookies:
                                if cookie.get("name") == "WorkosCursorSessionToken":
                                    value = cookie.get("value", "")
                                    token = get_token_from_cookie(value, self.translator)
                                    if token:
                                        # 获取邮箱地址并检查使用情况
                                        # Get email and check usage here too
                                        try:
                                            # 使用CSS选择器查找包含邮箱地址的元素
                                            # Use CSS selector to find the element containing email address
                                            email_element = self.browser.ele("css:div[class='flex w-full flex-col gap-2'] div:nth-child(2) p:nth-child(2)")
                                            if email_element:
                                                actual_email = email_element.text
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_email', email=actual_email) if self.translator else f'Found email: {actual_email}'}{Style.RESET_ALL}")
                                        except Exception as e:
                                            # 如果无法找到邮箱地址，使用默认值
                                            # If email address cannot be found, use default value
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_find_email', error=str(e)) if self.translator else f'Could not find email: {str(e)}'}{Style.RESET_ALL}")
                                            actual_email = "user@cursor.sh"
                                        
                                        # 检查使用量计数
                                        # Check usage count
                                        try:
                                            # 查找显示使用量的元素
                                            # Find the element displaying usage count
                                            usage_element = self.browser.ele("css:div[class='flex flex-col gap-4 lg:flex-row'] div:nth-child(1) div:nth-child(1) span:nth-child(2)")
                                            if usage_element:
                                                usage_text = usage_element.text
                                                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.usage_count', usage=usage_text) if self.translator else f'Usage count: {usage_text}'}{Style.RESET_ALL}")
                                                
                                                # 定义检查使用量限制的函数
                                                # Define function to check usage limits
                                                def check_usage_limits(usage_str):
                                                    try:
                                                        # 解析使用量字符串（格式：当前使用量/总限制）
                                                        # Parse usage string (format: current_usage/total_limit)
                                                        parts = usage_str.split('/')
                                                        if len(parts) != 2:
                                                            return False
                                                        # 提取当前使用量和总限制
                                                        # Extract current usage and total limit
                                                        current = int(parts[0].strip())
                                                        limit = int(parts[1].strip())
                                                        # 检查是否达到使用限制（50/50 或 150/150）
                                                        # Check if usage limit is reached (50/50 or 150/150)
                                                        return (limit == 50 and current >= 50) or (limit == 150 and current >= 150)
                                                    except:
                                                        # 解析失败时返回 False
                                                        # Return False if parsing fails
                                                        return False

                                            # 检查是否达到使用限制
                                            # Check if usage limit is reached
                                            if check_usage_limits(usage_text):
                                                # 账户已达到最大使用量，需要删除
                                                # Account has reached maximum usage, needs to be deleted
                                                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.account_has_reached_maximum_usage', deleting='deleting') if self.translator else 'Account has reached maximum usage, deleting...'}{Style.RESET_ALL}")
                                                if self._delete_current_account():
                                                    # 删除成功，开始新的认证流程
                                                    # Deletion successful, start new authentication process
                                                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.starting_new_authentication_process') if self.translator else 'Starting new authentication process...'}{Style.RESET_ALL}")
                                                    if self.auth_type == "google":
                                                        return self.handle_google_auth()
                                                    else:
                                                        return self.handle_github_auth()
                                                else:
                                                    # 删除失败
                                                    # Deletion failed
                                                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.failed_to_delete_expired_account') if self.translator else 'Failed to delete expired account'}{Style.RESET_ALL}")
                                            else:
                                                # 账户仍然有效
                                                # Account is still valid
                                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.account_is_still_valid', usage=usage_text) if self.translator else f'Account is still valid (Usage: {usage_text})'}{Style.RESET_ALL}")
                                        except Exception as e:
                                            # 检查使用量时发生错误
                                            # Error occurred while checking usage count
                                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.could_not_check_usage_count', error=str(e)) if self.translator else f'Could not check usage count: {str(e)}'}{Style.RESET_ALL}")
                                        
                                        # 移除浏览器保持打开提示和输入等待
                                        # Remove the browser stay open prompt and input wait
                                        # 返回认证成功结果，包含邮箱和令牌
                                        # Return authentication success result with email and token
                                        return True, {"email": actual_email, "token": token}
                        elif current_url != last_url:
                            # 页面发生变化，重新检查认证状态
                            # Page changed, recheck authentication status
                            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.page_changed_checking_auth') if self.translator else 'Page changed, checking auth...'}{Style.RESET_ALL}")
                            last_url = current_url
                            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
                    except Exception as e:
                        # 状态检查时发生错误，继续重试
                        # Error occurred during status check, continue retrying
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('oauth.status_check_error', error=str(e)) if self.translator else f'Status check error: {str(e)}'}{Style.RESET_ALL}")
                        time.sleep(1)
                        continue
                    time.sleep(1)
                    
                # 认证超时
                # Authentication timeout
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_timeout') if self.translator else 'Authentication timeout'}{Style.RESET_ALL}")
                return False, None
                
            # 未找到认证按钮
            # Authentication button not found
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_button_not_found') if self.translator else 'Authentication button not found'}{Style.RESET_ALL}")
            return False, None
            
        except Exception as e:
            # 认证失败
            # Authentication failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('oauth.authentication_failed', error=str(e)) if self.translator else f'Authentication failed: {str(e)}'}{Style.RESET_ALL}")
            return False, None
        finally:
            # 确保浏览器被正确关闭
            # Ensure browser is properly closed
            if self.browser:
                self.browser.quit()

    def _extract_auth_info(self):
        """在成功的 OAuth 认证后提取认证信息
        Extract authentication information after successful OAuth
        
        Returns:
            tuple: (success: bool, auth_data: dict or None)
                  成功时返回包含邮箱和令牌的字典，失败时返回 None
                  Returns dict with email and token on success, None on failure
        """
        try:
            # 重试获取 cookies
            # Get cookies with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    cookies = self.browser.cookies()
                    if cookies:
                        break
                    time.sleep(1)
                except:
                    # 如果是最后一次尝试，抛出异常
                    # If this is the last attempt, raise exception
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1)
            
            # 调试 cookie 信息
            # Debug cookie information
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.found_cookies', count=len(cookies)) if self.translator else f'Found {len(cookies)} cookies'}{Style.RESET_ALL}")
            
            # 初始化邮箱和令牌变量
            # Initialize email and token variables
            email = None
            token = None
            
            # 遍历所有 cookies 查找认证信息
            # Iterate through all cookies to find authentication information
            for cookie in cookies:
                name = cookie.get("name", "")
                if name == "WorkosCursorSessionToken":
                    # 提取会话令牌
                    # Extract session token
                    try:
                        value = cookie.get("value", "")
                        token = get_token_from_cookie(value, self.translator)
                    except Exception as e:
                        error_message = f'Failed to extract auth info: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_extract_auth_info', error=str(e))
                        print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
                elif name == "cursor_email":
                    # 提取邮箱地址
                    # Extract email address
                    email = cookie.get("value")
                    
            # 检查是否成功获取了邮箱和令牌
            # Check if email and token were successfully obtained
            if email and token:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('oauth.authentication_successful', email=email) if self.translator else f'Authentication successful - Email: {email}'}{Style.RESET_ALL}")
                return True, {"email": email, "token": token}
            else:
                # 检查缺少哪些认证数据
                # Check which authentication data is missing
                missing = []
                if not email:
                    missing.append("email")
                if not token:
                    missing.append("token")
                error_message = f"Missing authentication data: {', '.join(missing)}" if not self.translator else self.translator.get('oauth.missing_authentication_data', data=', '.join(missing))
                print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
                return False, None
            
        except Exception as e:
            # 提取认证信息时发生错误
            # Error occurred while extracting authentication information
            error_message = f'Failed to extract auth info: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_extract_auth_info', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
            return False, None

    def _delete_current_account(self):
        """使用 API 删除当前账户
        Delete the current account using the API
        
        Returns:
            bool: 删除成功返回 True，失败返回 False
                  Returns True if deletion successful, False otherwise
        """
        try:
            # JavaScript 代码用于调用删除账户 API
            # JavaScript code to call delete account API
            delete_js = """
            function deleteAccount() {
                return new Promise((resolve, reject) => {
                    // 向 Cursor API 发送删除账户请求
                    // Send delete account request to Cursor API
                    fetch('https://www.cursor.com/api/dashboard/delete-account', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include'  // 包含认证 cookies
                    })
                    .then(response => {
                        if (response.status === 200) {
                            resolve('Account deleted successfully');
                        } else {
                            reject('Failed to delete account: ' + response.status);
                        }
                    })
                    .catch(error => {
                        reject('Error: ' + error);
                    });
                });
            }
            // 调用删除账户函数并返回结果
            // Call delete account function and return result
            return deleteAccount();
            """
            
            # 执行 JavaScript 代码删除账户
            # Execute JavaScript code to delete account
            result = self.browser.run_js(delete_js)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Delete account result: {result}{Style.RESET_ALL}")
            
            # 导航回认证页面
            # Navigate back to auth page
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('oauth.redirecting_to_authenticator_cursor_sh') if self.translator else 'Redirecting to authenticator.cursor.sh...'}{Style.RESET_ALL}")
            self.browser.get("https://authenticator.cursor.sh/sign-up")
            time.sleep(get_random_wait_time(self.config, 'page_load_wait'))
            
            return True
            
        except Exception as e:
            # 删除账户时发生错误
            # Error occurred while deleting account
            error_message = f'Failed to delete account: {str(e)}' if not self.translator else self.translator.get('oauth.failed_to_delete_account', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_message}{Style.RESET_ALL}")
            return False

def main(auth_type, translator=None):
    """处理 OAuth 认证的主函数
    Main function to handle OAuth authentication
    
    Args:
        auth_type (str): 认证类型 ('google' 或 'github')
                        Type of authentication ('google' or 'github')
        translator: 国际化翻译器实例
                   Translator instance for internationalization
    
    Returns:
        tuple: (success: bool, auth_info: dict or None)
               成功时返回认证信息，失败时返回 None
               Returns authentication info on success, None on failure
    """
    # 创建 OAuth 处理器实例
    # Create OAuth handler instance
    handler = OAuthHandler(translator, auth_type)
    
    if auth_type.lower() == 'google':
        # 开始 Google 认证流程
        # Start Google authentication process
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.google_start') if translator else 'Google start'}{Style.RESET_ALL}")
        success, auth_info = handler.handle_google_auth()
    elif auth_type.lower() == 'github':
        # 开始 GitHub 认证流程
        # Start GitHub authentication process
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.github_start') if translator else 'Github start'}{Style.RESET_ALL}")
        success, auth_info = handler.handle_github_auth()
    else:
        # 无效的认证类型
        # Invalid authentication type
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('oauth.invalid_authentication_type') if translator else 'Invalid authentication type'}{Style.RESET_ALL}")
        return False
        
    # 检查认证是否成功
    # Check if authentication was successful
    if success and auth_info:
        # 更新 Cursor 认证信息
        # Update Cursor authentication
        auth_manager = CursorAuth(translator)
        if auth_manager.update_auth(
            email=auth_info["email"],
            access_token=auth_info["token"],
            refresh_token=auth_info["token"],
            auth_type=auth_type
        ):
            # 认证更新成功
            # Authentication update successful
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('oauth.auth_update_success') if translator else 'Auth update success'}{Style.RESET_ALL}")
            # 认证成功后关闭浏览器
            # Close the browser after successful authentication
            if handler.browser:
                handler.browser.quit()
                print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('oauth.browser_closed') if translator else 'Browser closed'}{Style.RESET_ALL}")
            return True
        else:
            # 认证更新失败
            # Authentication update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('oauth.auth_update_failed') if translator else 'Auth update failed'}{Style.RESET_ALL}")
            
    # 认证失败或未获取到认证信息
    # Authentication failed or no authentication info obtained
    return False