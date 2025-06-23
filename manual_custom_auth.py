"""Manual Custom Auth for Cursor AI / Cursor AI 手动自定义认证
This script allows users to manually input access token and email to authenticate with Cursor AI.
该脚本允许用户手动输入访问令牌和邮箱来认证 Cursor AI。

功能说明 / Features:
1. 手动输入 Cursor 访问令牌 / Manual input of Cursor access token
2. 自动生成随机邮箱或手动输入邮箱 / Auto-generate random email or manual input
3. 选择认证类型（Auth_0、Google、GitHub）/ Select authentication type
4. 验证令牌有效性 / Verify token validity
5. 更新 Cursor 认证数据库 / Update Cursor authentication database

使用方法 / Usage:
1. 直接运行脚本：python manual_custom_auth.py
2. 或从其他模块导入：from manual_custom_auth import main
3. 按照提示输入令牌、邮箱和认证类型

依赖模块 / Dependencies:
- colorama: 终端颜色输出
- cursor_auth: Cursor 认证管理
- check_user_authorized: 令牌验证（可选）
"""

import os
import sys
import random
import string
from colorama import Fore, Style, init
from cursor_auth import CursorAuth

# 初始化 colorama 用于终端颜色输出 / Initialize colorama for colored terminal output
init(autoreset=True)

# 定义表情符号和颜色常量 / Define emoji and color constants
EMOJI = {
    'DB': '🗄️',        # 数据库图标 / Database icon
    'UPDATE': '🔄',    # 更新图标 / Update icon
    'SUCCESS': '✅',   # 成功图标 / Success icon
    'ERROR': '❌',     # 错误图标 / Error icon
    'WARN': '⚠️',      # 警告图标 / Warning icon
    'INFO': 'ℹ️',      # 信息图标 / Info icon
    'FILE': '📄',      # 文件图标 / File icon
    'KEY': '🔐'        # 密钥图标 / Key icon
}

def generate_random_email():
    """生成随机的 Cursor 邮箱地址 / Generate a random Cursor email address
    
    Returns:
        str: 格式为 cursor_xxxxxxxx@cursor.ai 的随机邮箱地址
             Random email address in format cursor_xxxxxxxx@cursor.ai
    """
    # 生成8位随机字符串（小写字母+数字）/ Generate 8-character random string (lowercase letters + digits)
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # 返回格式化的邮箱地址 / Return formatted email address
    return f"cursor_{random_string}@cursor.ai"

def main(translator=None):
    """处理手动认证的主函数 / Main function to handle manual authentication
    
    Args:
        translator: 翻译器对象，用于多语言支持（可选）
                   Translator object for multi-language support (optional)
    
    Returns:
        bool: 认证是否成功 / Whether authentication was successful
    
    功能流程 / Process Flow:
    1. 获取用户输入的令牌 / Get user input token
    2. 验证令牌有效性 / Verify token validity
    3. 获取或生成邮箱地址 / Get or generate email address
    4. 选择认证类型 / Select authentication type
    5. 确认信息并更新数据库 / Confirm info and update database
    """
    # 打印程序标题和分隔线 / Print program title and separator
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Manual Cursor Authentication{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # 步骤1：从用户获取令牌 / Step 1: Get token from user
    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('manual_auth.token_prompt') if translator else 'Enter your Cursor token (access_token/refresh_token):'}{Style.RESET_ALL}")
    token = input(f"{Fore.CYAN}> {Style.RESET_ALL}").strip()
    
    # 检查令牌是否为空 / Check if token is empty
    if not token:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.token_required') if translator else 'Token is required'}{Style.RESET_ALL}")
        return False
    
    # 步骤2：验证令牌有效性 / Step 2: Verify token validity
    try:
        # 导入令牌验证模块 / Import token verification module
        from check_user_authorized import check_user_authorized
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('manual_auth.verifying_token') if translator else 'Verifying token validity...'}{Style.RESET_ALL}")
        
        # 调用验证函数检查令牌 / Call verification function to check token
        is_valid = check_user_authorized(token, translator)
        
        # 如果令牌无效，终止认证流程 / If token is invalid, abort authentication
        if not is_valid:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.invalid_token') if translator else 'Invalid token. Authentication aborted.'}{Style.RESET_ALL}")
            return False
            
        # 令牌验证成功 / Token verification successful
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('manual_auth.token_verified') if translator else 'Token verified successfully!'}{Style.RESET_ALL}")
    except ImportError:
        # 验证模块不存在，跳过验证 / Verification module not found, skip verification
        print(f"{Fore.YELLOW}{EMOJI['WARN']} {translator.get('manual_auth.token_verification_skipped') if translator else 'Token verification skipped (check_user_authorized.py not found)'}{Style.RESET_ALL}")
    except Exception as e:
        # 验证过程中发生错误 / Error occurred during verification
        print(f"{Fore.YELLOW}{EMOJI['WARN']} {translator.get('manual_auth.token_verification_error', error=str(e)) if translator else f'Error verifying token: {str(e)}'}{Style.RESET_ALL}")
        
        # 询问用户是否继续 / Ask user if they want to continue despite verification error
        continue_anyway = input(f"{Fore.YELLOW}{translator.get('manual_auth.continue_anyway') if translator else 'Continue anyway? (y/N): '}{Style.RESET_ALL}").strip().lower()
        if continue_anyway not in ["y", "yes"]:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.operation_cancelled') if translator else 'Operation cancelled'}{Style.RESET_ALL}")
            return False
    
    # 步骤3：获取邮箱地址（或生成随机邮箱）/ Step 3: Get email (or generate random one)
    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('manual_auth.email_prompt') if translator else 'Enter email (leave blank for random email):'}{Style.RESET_ALL}")
    email = input(f"{Fore.CYAN}> {Style.RESET_ALL}").strip()
    
    # 如果用户未输入邮箱，自动生成随机邮箱 / If user didn't enter email, auto-generate random email
    if not email:
        email = generate_random_email()
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('manual_auth.random_email_generated', email=email) if translator else f'Random email generated: {email}'}{Style.RESET_ALL}")
    
    # 步骤4：选择认证类型 / Step 4: Get auth type
    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('manual_auth.auth_type_prompt') if translator else 'Select authentication type:'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}1. {translator.get('manual_auth.auth_type_auth0') if translator else 'Auth_0 (Default)'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}2. {translator.get('manual_auth.auth_type_google') if translator else 'Google'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}3. {translator.get('manual_auth.auth_type_github') if translator else 'GitHub'}{Style.RESET_ALL}")
    
    # 获取用户选择 / Get user choice
    auth_choice = input(f"{Fore.CYAN}> {Style.RESET_ALL}").strip()
    
    # 根据用户选择设置认证类型 / Set auth type based on user choice
    if auth_choice == "2":
        auth_type = "Google"
    elif auth_choice == "3":
        auth_type = "GitHub"
    else:
        auth_type = "Auth_0"  # 默认选择 / Default choice
    
    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('manual_auth.auth_type_selected', type=auth_type) if translator else f'Selected authentication type: {auth_type}'}{Style.RESET_ALL}")
    
    # 步骤5：确认信息后继续 / Step 5: Confirm before proceeding
    print(f"\n{Fore.YELLOW}{EMOJI['WARN']} {translator.get('manual_auth.confirm_prompt') if translator else 'Please confirm the following information:'}{Style.RESET_ALL}")
    # 显示令牌的前10位和后10位（保护隐私）/ Display first 10 and last 10 characters of token (privacy protection)
    print(f"{Fore.CYAN}Token: {token[:10]}...{token[-10:] if len(token) > 20 else token[10:]}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Email: {email}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Auth Type: {auth_type}{Style.RESET_ALL}")
    
    # 获取用户确认 / Get user confirmation
    confirm = input(f"\n{Fore.YELLOW}{translator.get('manual_auth.proceed_prompt') if translator else 'Proceed? (y/N): '}{Style.RESET_ALL}").strip().lower()
    
    # 如果用户不确认，取消操作 / If user doesn't confirm, cancel operation
    if confirm not in ["y", "yes"]:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.operation_cancelled') if translator else 'Operation cancelled'}{Style.RESET_ALL}")
        return False
    
    # 步骤6：初始化 CursorAuth 并更新数据库 / Step 6: Initialize CursorAuth and update the database
    print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('manual_auth.updating_database') if translator else 'Updating Cursor authentication database...'}{Style.RESET_ALL}")
    
    try:
        # 创建 CursorAuth 实例 / Create CursorAuth instance
        cursor_auth = CursorAuth(translator)
        # 更新认证信息到数据库 / Update authentication info to database
        result = cursor_auth.update_auth(
            email=email,
            access_token=token,
            refresh_token=token,  # 使用相同的令牌作为刷新令牌 / Use same token as refresh token
            auth_type=auth_type
        )
        
        # 检查更新结果 / Check update result
        if result:
            print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('manual_auth.auth_updated_successfully') if translator else 'Authentication information updated successfully!'}{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.auth_update_failed') if translator else 'Failed to update authentication information'}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        # 处理更新过程中的异常 / Handle exceptions during update process
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('manual_auth.error', error=str(e)) if translator else f'Error: {str(e)}'}{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    # 当脚本直接运行时的入口点 / Entry point when script is run directly
    # 强制使用 None 作为翻译器参数（使用英文界面）/ Force to run with None translator (English interface)
    main(None)