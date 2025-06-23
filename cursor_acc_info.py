import os
"""Cursor 账户信息查询模块 / Cursor Account Information Query Module

该模块提供了查询 Cursor AI 账户信息的功能，包括：
- 获取用户使用量统计（Premium 和 Basic 模式）
- 查询订阅信息和账户状态
- 从多个来源提取访问令牌
- 跨平台支持（Windows、macOS、Linux）

主要功能 / Main Features:
1. 使用量查询：获取 GPT-4 和 GPT-3.5 的使用统计
2. 订阅信息：查询 Stripe 订阅详情
3. 令牌提取：从存储文件、SQLite 数据库、会话文件中获取令牌
4. 多平台支持：自动检测操作系统并使用相应路径

使用方法 / Usage:
```python
from cursor_acc_info import UsageManager, get_token_from_config

# 获取令牌
token = get_token_from_config()

# 查询使用量
usage_info = UsageManager.get_usage(token)

# 查询订阅信息
subscription_info = UsageManager.get_stripe_profile(token)
```

依赖模块 / Dependencies:
- requests: HTTP 请求处理
- sqlite3: SQLite 数据库操作
- colorama: 终端颜色输出
- config: 配置文件管理
"""

import sys
import json
import requests
import sqlite3
from typing import Dict, Optional
import platform
from colorama import Fore, Style, init
import logging
import re
import os  # 添加缺失的 os 模块导入

# 初始化 colorama 用于终端颜色输出 / Initialize colorama for colored terminal output
init()

# 设置日志记录器 / Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义表情符号常量 / Define emoji constants
EMOJI = {
    "USER": "👤",        # 用户图标 / User icon
    "USAGE": "📊",       # 使用量图标 / Usage icon
    "PREMIUM": "⭐",     # 高级版图标 / Premium icon
    "BASIC": "📝",       # 基础版图标 / Basic icon
    "SUBSCRIPTION": "💳", # 订阅图标 / Subscription icon
    "INFO": "ℹ️",        # 信息图标 / Info icon
    "ERROR": "❌",       # 错误图标 / Error icon
    "SUCCESS": "✅",     # 成功图标 / Success icon
    "WARNING": "⚠️",     # 警告图标 / Warning icon
    "TIME": "🕒"         # 时间图标 / Time icon
}

class Config:
    """配置类 / Configuration Class
    
    存储 Cursor API 相关的配置信息，包括应用名称和 HTTP 请求头。
    
    属性 / Attributes:
        NAME_LOWER: 小写应用名称
        NAME_CAPITALIZE: 首字母大写应用名称
        BASE_HEADERS: 基础 HTTP 请求头
    """
    NAME_LOWER = "cursor"                    # 小写应用名称 / Lowercase app name
    NAME_CAPITALIZE = "Cursor"               # 首字母大写应用名称 / Capitalized app name
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

class UsageManager:
    """使用量管理器 / Usage Manager
    
    负责查询 Cursor AI 的使用量统计和订阅信息。
    提供静态方法来获取代理设置、使用量数据和订阅详情。
    
    主要方法 / Main Methods:
    - get_proxy(): 获取代理设置
    - get_usage(): 获取使用量统计
    - get_stripe_profile(): 获取订阅信息
    """
    
    @staticmethod
    def get_proxy():
        """获取代理设置 / Get proxy settings
        
        从环境变量中读取 HTTP 代理配置。
        
        返回值 / Returns:
            dict: 代理配置字典，如果未设置代理则返回 None
        """
        # 从环境变量获取代理设置 / Get proxy settings from environment variables
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy:
            return {"http": proxy, "https": proxy}
        return None
    
    @staticmethod
    def get_usage(token: str) -> Optional[Dict]:
        """获取使用量统计 / Get usage statistics
        
        查询用户的 GPT-4 (Premium) 和 GPT-3.5 (Basic) 使用量。
        
        参数 / Args:
            token (str): 访问令牌
        
        返回值 / Returns:
            dict: 包含使用量信息的字典，失败时返回 None
                - premium_usage: GPT-4 已使用次数
                - max_premium_usage: GPT-4 最大使用次数
                - basic_usage: GPT-3.5 已使用次数
                - max_basic_usage: GPT-3.5 最大使用次数（通常为无限制）
        """
        url = f"https://www.{Config.NAME_LOWER}.com/api/usage"
        headers = Config.BASE_HEADERS.copy()
        # 构建认证 Cookie / Build authentication cookie
        headers.update({"Cookie": f"Workos{Config.NAME_CAPITALIZE}SessionToken=user_01OOOOOOOOOOOOOOOOOOOOOOOO%3A%3A{token}"})
        try:
            # 获取代理设置并发送请求 / Get proxy settings and send request
            proxies = UsageManager.get_proxy()
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            response.raise_for_status()
            data = response.json()
            
            # 获取 Premium (GPT-4) 使用量和限制 / Get Premium (GPT-4) usage and limit
            gpt4_data = data.get("gpt-4", {})
            premium_usage = gpt4_data.get("numRequestsTotal", 0)
            max_premium_usage = gpt4_data.get("maxRequestUsage", 999)
            
            # 获取 Basic (GPT-3.5) 使用量，限制设为无限制 / Get Basic (GPT-3.5) usage, set limit to "No Limit"
            gpt35_data = data.get("gpt-3.5-turbo", {})
            basic_usage = gpt35_data.get("numRequestsTotal", 0)
            
            return {
                'premium_usage': premium_usage, 
                'max_premium_usage': max_premium_usage, 
                'basic_usage': basic_usage, 
                'max_basic_usage': "No Limit"  # 基础版限制设为无限制 / Set Basic limit to "No Limit"
            }
        except requests.RequestException as e:
            # 仅记录网络请求错误 / Only log network request errors
            logger.error(f"Get usage info failed: {str(e)}")
            return None
        except Exception as e:
            # 捕获所有其他异常 / Catch all other exceptions
            logger.error(f"Get usage info failed: {str(e)}")
            return None

    @staticmethod
    def get_stripe_profile(token: str) -> Optional[Dict]:
        """获取用户订阅信息 / Get user subscription information
        
        查询用户的 Stripe 订阅详情，包括订阅状态、计划类型等。
        
        参数 / Args:
            token (str): 访问令牌
        
        返回值 / Returns:
            dict: 包含订阅信息的字典，失败时返回 None
        """
        url = f"https://api2.{Config.NAME_LOWER}.sh/auth/full_stripe_profile"
        headers = Config.BASE_HEADERS.copy()
        # 使用 Bearer 令牌认证 / Use Bearer token authentication
        headers.update({"Authorization": f"Bearer {token}"})
        try:
            # 获取代理设置并发送请求 / Get proxy settings and send request
            proxies = UsageManager.get_proxy()
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # 记录订阅信息获取失败 / Log subscription info retrieval failure
            logger.error(f"Get subscription info failed: {str(e)}")
            return None

def get_token_from_config():
    """从配置文件获取路径信息 / Get path information from config file
    
    根据操作系统类型从配置文件中获取 Cursor 相关文件的路径。
    
    返回值 / Returns:
        dict: 包含路径信息的字典，失败时返回 None
            - storage_path: 存储文件路径
            - sqlite_path: SQLite 数据库路径
            - session_path: 会话存储路径
    """
    try:
        # 导入配置模块并获取配置 / Import config module and get configuration
        from config import get_config
        config = get_config()
        if not config:
            return None
            
        # 检测操作系统类型 / Detect operating system type
        system = platform.system()
        if system == "Windows" and config.has_section('WindowsPaths'):
            # Windows 系统路径配置 / Windows system path configuration
            return {
                'storage_path': config.get('WindowsPaths', 'storage_path'),
                'sqlite_path': config.get('WindowsPaths', 'sqlite_path'),
                'session_path': os.path.join(os.getenv("APPDATA"), "Cursor", "Session Storage")
            }
        elif system == "Darwin" and config.has_section('MacPaths'):  # macOS 系统
            # macOS 系统路径配置 / macOS system path configuration
            return {
                'storage_path': config.get('MacPaths', 'storage_path'),
                'sqlite_path': config.get('MacPaths', 'sqlite_path'),
                'session_path': os.path.expanduser("~/Library/Application Support/Cursor/Session Storage")
            }
        elif system == "Linux" and config.has_section('LinuxPaths'):
            # Linux 系统路径配置 / Linux system path configuration
            return {
                'storage_path': config.get('LinuxPaths', 'storage_path'),
                'sqlite_path': config.get('LinuxPaths', 'sqlite_path'),
                'session_path': os.path.expanduser("~/.config/Cursor/Session Storage")
            }
    except Exception as e:
        # 记录配置路径获取失败 / Log config path retrieval failure
        logger.error(f"Get config path failed: {str(e)}")
    
    return None

def get_token_from_storage(storage_path):
    """从 storage.json 文件中提取访问令牌 / Extract access token from storage.json file
    
    从 Cursor 的存储文件中查找并提取访问令牌。
    
    参数 / Args:
        storage_path (str): storage.json 文件的路径
    
    返回值 / Returns:
        str: 提取的访问令牌，失败时返回 None
    """
    # 检查文件是否存在 / Check if file exists
    if not os.path.exists(storage_path):
        return None
        
    try:
        # 读取并解析 JSON 文件 / Read and parse JSON file
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 尝试获取标准的访问令牌键 / Try to get standard access token key
            if 'cursorAuth/accessToken' in data:
                return data['cursorAuth/accessToken']
            
            # 尝试其他可能的令牌键 / Try other possible token keys
            for key in data:
                if 'token' in key.lower() and isinstance(data[key], str) and len(data[key]) > 20:
                    return data[key]
    except Exception as e:
        # 记录从存储文件获取令牌失败 / Log token retrieval failure from storage file
        logger.error(f"get token from storage.json failed: {str(e)}")
    
    return None

def get_token_from_sqlite(sqlite_path):
    """从 SQLite 数据库中提取访问令牌 / Extract access token from SQLite database
    
    从 Cursor 的 SQLite 数据库中查询并解析访问令牌。
    
    参数 / Args:
        sqlite_path (str): SQLite 数据库文件的路径
    
    返回值 / Returns:
        str: 提取的访问令牌，失败时返回 None
    """
    # 检查数据库文件是否存在 / Check if database file exists
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        # 连接 SQLite 数据库 / Connect to SQLite database
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        # 查询包含 token 的键值对 / Query key-value pairs containing token
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%token%'")
        rows = cursor.fetchall()
        conn.close()
        
        # 遍历查询结果 / Iterate through query results
        for row in rows:
            try:
                value = row[0]
                # 检查是否为有效的令牌字符串 / Check if it's a valid token string
                if isinstance(value, str) and len(value) > 20:
                    return value
                # 尝试解析 JSON 格式的值 / Try to parse JSON format value
                data = json.loads(value)
                if isinstance(data, dict) and 'token' in data:
                    return data['token']
            except:
                # 忽略解析失败的记录 / Ignore records that fail to parse
                continue
    except Exception as e:
        # 记录从 SQLite 获取令牌失败 / Log token retrieval failure from SQLite
        logger.error(f"get token from sqlite failed: {str(e)}")
    
    return None

def get_token_from_session(session_path):
    """从会话日志文件中提取访问令牌 / Extract access token from session log files
    
    从 Cursor 的会话存储目录中搜索日志文件并提取访问令牌。
    
    参数 / Args:
        session_path (str): 会话存储目录的路径
    
    返回值 / Returns:
        str: 提取的访问令牌，失败时返回 None
    """
    # 检查会话目录是否存在 / Check if session directory exists
    if not os.path.exists(session_path):
        return None
        
    try:
        # 尝试查找所有可能的会话文件 / Try to find all possible session files
        for file in os.listdir(session_path):
            if file.endswith('.log'):
                file_path = os.path.join(session_path, file)
                try:
                    # 以二进制模式读取文件并解码 / Read file in binary mode and decode
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        # 使用正则表达式查找令牌模式 / Use regex to find token pattern
                        token_match = re.search(r'"token":"([^"]+)"', content)
                        if token_match:
                            return token_match.group(1)
                except:
                    # 忽略无法读取的文件 / Ignore files that cannot be read
                    continue
    except Exception as e:
        # 记录从会话文件获取令牌失败 / Log token retrieval failure from session files
        logger.error(f"get token from session failed: {str(e)}")
    
    return None

def get_token():
    """获取 Cursor 访问令牌 / Get Cursor access token
    
    按优先级从多个位置尝试获取访问令牌：
    1. storage.json 文件
    2. SQLite 数据库
    3. 会话日志文件
    
    返回值 / Returns:
        str: 访问令牌，失败时返回 None
    """
    # 从配置获取路径信息 / Get path information from config
    paths = get_token_from_config()
    if not paths:
        return None
    
    # 按优先级尝试从不同位置获取令牌 / Try to get token from different locations by priority
    token = get_token_from_storage(paths['storage_path'])
    if token:
        return token
        
    token = get_token_from_sqlite(paths['sqlite_path'])
    if token:
        return token
        
    token = get_token_from_session(paths['session_path'])
    if token:
        return token
    
    return None

def format_subscription_type(subscription_data: Dict) -> str:
    """格式化订阅类型信息 / Format subscription type information
    
    将 API 返回的订阅数据格式化为可读的订阅类型字符串。
    
    参数 / Args:
        subscription_data (dict): 订阅数据字典
    
    返回值 / Returns:
        str: 格式化的订阅类型字符串
    """
    if not subscription_data:
        return "Free"
    
    # 处理新版 API 响应格式 / Handle new API response format
    if "membershipType" in subscription_data:
        membership_type = subscription_data.get("membershipType", "").lower()
        subscription_status = subscription_data.get("subscriptionStatus", "").lower()
        
        if subscription_status == "active":
            # 根据会员类型返回相应标签 / Return corresponding label based on membership type
            if membership_type == "pro":
                return "Pro"
            elif membership_type == "free_trial":
                return "Free Trial"
            elif membership_type == "pro_trial":
                return "Pro Trial"
            elif membership_type == "team":
                return "Team"
            elif membership_type == "enterprise":
                return "Enterprise"
            elif membership_type:
                return membership_type.capitalize()
            else:
                return "Active Subscription"
        elif subscription_status:
            return f"{membership_type.capitalize()} ({subscription_status})"
    
    # 兼容旧版 API 响应格式 / Compatible with old API response format
    subscription = subscription_data.get("subscription")
    if subscription:
        plan = subscription.get("plan", {}).get("nickname", "Unknown")
        status = subscription.get("status", "unknown")
        
        if status == "active":
            # 根据计划名称识别订阅类型 / Identify subscription type based on plan name
            if "pro" in plan.lower():
                return "Pro"
            elif "pro_trial" in plan.lower():
                return "Pro Trial"
            elif "free_trial" in plan.lower():
                return "Free Trial"
            elif "team" in plan.lower():
                return "Team"
            elif "enterprise" in plan.lower():
                return "Enterprise"
            else:
                return plan
        else:
            return f"{plan} ({status})"
    
    return "Free"

def get_email_from_storage(storage_path):
    """从 storage.json 文件中提取邮箱地址 / Extract email address from storage.json file
    
    从 Cursor 的存储文件中查找并提取用户邮箱地址。
    
    参数 / Args:
        storage_path (str): storage.json 文件的路径
    
    返回值 / Returns:
        str: 提取的邮箱地址，失败时返回 None
    """
    # 检查文件是否存在 / Check if file exists
    if not os.path.exists(storage_path):
        return None
        
    try:
        # 读取并解析 JSON 文件 / Read and parse JSON file
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 尝试获取标准的邮箱键 / Try to get standard email key
            if 'cursorAuth/cachedEmail' in data:
                return data['cursorAuth/cachedEmail']
            
            # 尝试其他可能的邮箱键 / Try other possible email keys
            for key in data:
                if 'email' in key.lower() and isinstance(data[key], str) and '@' in data[key]:
                    return data[key]
    except Exception as e:
        # 记录从存储文件获取邮箱失败 / Log email retrieval failure from storage file
        logger.error(f"get email from storage.json failed: {str(e)}")
    
    return None

def get_email_from_sqlite(sqlite_path):
    """从 SQLite 数据库中提取邮箱地址 / Extract email address from SQLite database
    
    从 Cursor 的 SQLite 数据库中查询并解析用户邮箱地址。
    
    参数 / Args:
        sqlite_path (str): SQLite 数据库文件的路径
    
    返回值 / Returns:
        str: 提取的邮箱地址，失败时返回 None
    """
    # 检查数据库文件是否存在 / Check if database file exists
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        # 连接 SQLite 数据库 / Connect to SQLite database
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        # 查询包含邮箱或认证信息的记录 / Query records containing email or auth info
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%email%' OR key LIKE '%cursorAuth%'")
        rows = cursor.fetchall()
        conn.close()
        
        # 遍历查询结果 / Iterate through query results
        for row in rows:
            try:
                value = row[0]
                # 如果是字符串且包含 @，可能是邮箱 / If it's a string and contains @, it might be an email
                if isinstance(value, str) and '@' in value:
                    return value
                
                # 尝试解析 JSON 格式的值 / Try to parse JSON format value
                try:
                    data = json.loads(value)
                    if isinstance(data, dict):
                        # 检查是否有邮箱字段 / Check if there's an email field
                        if 'email' in data:
                            return data['email']
                        # 检查是否有缓存邮箱字段 / Check if there's a cachedEmail field
                        if 'cachedEmail' in data:
                            return data['cachedEmail']
                except:
                    # 忽略 JSON 解析失败 / Ignore JSON parsing failures
                    pass
            except:
                # 忽略处理失败的记录 / Ignore records that fail to process
                continue
    except Exception as e:
        # 记录从 SQLite 获取邮箱失败 / Log email retrieval failure from SQLite
        logger.error(f"get email from sqlite failed: {str(e)}")
    
    return None

def display_account_info(translator=None):
    """显示账户信息 / Display account information
    
    获取并显示 Cursor 账户的详细信息，包括邮箱、订阅状态和使用情况。
    
    参数 / Args:
        translator: 翻译器对象，用于多语言支持
    """
    # 显示标题分隔线 / Display title separator
    print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['USER']} {translator.get('account_info.title') if translator else 'Cursor Account Information'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    
    # 获取访问令牌 / Get access token
    token = get_token()
    if not token:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.token_not_found') if translator else 'Token not found. Please login to Cursor first.'}{Style.RESET_ALL}")
        return
    
    # 获取路径信息 / Get path information
    paths = get_token_from_config()
    if not paths:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.config_not_found') if translator else 'Configuration not found.'}{Style.RESET_ALL}")
        return
    
    # 从多个来源获取邮箱信息 / Get email info from multiple sources
    email = get_email_from_storage(paths['storage_path'])
    
    # 如果存储中未找到，尝试从 SQLite 获取 / If not found in storage, try from SQLite
    if not email:
        email = get_email_from_sqlite(paths['sqlite_path'])
    
    # 获取订阅信息 / Get subscription information
    try:
        subscription_info = UsageManager.get_stripe_profile(token)
    except Exception as e:
        logger.error(f"Get subscription info failed: {str(e)}")
        subscription_info = None
    
    # 如果存储和数据库中都未找到邮箱，尝试从订阅信息获取 / If not found in storage and SQLite, try from subscription info
    if not email and subscription_info:
        # 尝试从订阅信息中获取邮箱 / Try to get email from subscription info
        if 'customer' in subscription_info and 'email' in subscription_info['customer']:
            email = subscription_info['customer']['email']
    
    # 获取使用情况信息，静默处理错误 / Get usage info, silently handle errors
    try:
        usage_info = UsageManager.get_usage(token)
    except Exception as e:
        logger.error(f"Get usage info failed: {str(e)}")
        usage_info = None
    
    # 准备左右两侧的信息显示 / Prepare left and right info display
    left_info = []
    right_info = []
    
    # 左侧显示账户信息 / Left side shows account info
    if email:
        left_info.append(f"{Fore.GREEN}{EMOJI['USER']} {translator.get('account_info.email') if translator else 'Email'}: {Fore.WHITE}{email}{Style.RESET_ALL}")
    else:
        left_info.append(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('account_info.email_not_found') if translator else 'Email not found'}{Style.RESET_ALL}")
    
    # 添加空行（已注释） / Add empty line (commented)
    # left_info.append("")
    
    # 显示订阅类型 / Show subscription type
    if subscription_info:
        subscription_type = format_subscription_type(subscription_info)
        left_info.append(f"{Fore.GREEN}{EMOJI['SUBSCRIPTION']} {translator.get('account_info.subscription') if translator else 'Subscription'}: {Fore.WHITE}{subscription_type}{Style.RESET_ALL}")
        
        # 显示剩余试用天数 / Show remaining trial days
        days_remaining = subscription_info.get("daysRemainingOnTrial")
        if days_remaining is not None and days_remaining > 0:
            left_info.append(f"{Fore.GREEN}{EMOJI['TIME']} {translator.get('account_info.trial_remaining') if translator else 'Remaining Pro Trial'}: {Fore.WHITE}{days_remaining} {translator.get('account_info.days') if translator else 'days'}{Style.RESET_ALL}")
    else:
        left_info.append(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('account_info.subscription_not_found') if translator else 'Subscription information not found'}{Style.RESET_ALL}")
    
    # 右侧显示使用情况信息（仅在可用时） / Right side shows usage info (only if available)
    if usage_info:
        right_info.append(f"{Fore.GREEN}{EMOJI['USAGE']} {translator.get('account_info.usage') if translator else 'Usage Statistics'}:{Style.RESET_ALL}")
        
        # 高级使用量（快速响应） / Premium usage (Fast Response)
        premium_usage = usage_info.get('premium_usage', 0)
        max_premium_usage = usage_info.get('max_premium_usage', "No Limit")
        
        # 确保值不为 None / Make sure the value is not None
        if premium_usage is None:
            premium_usage = 0
        
        # 处理"无限制"情况 / Handle "No Limit" case
        if isinstance(max_premium_usage, str) and max_premium_usage == "No Limit":
            premium_color = Fore.GREEN  # 无限制时使用绿色 / Use green when there is no limit
            premium_display = f"{premium_usage}/{max_premium_usage}"
        else:
            # 当值为数字时计算百分比 / Calculate percentage when the value is a number
            if max_premium_usage is None or max_premium_usage == 0:
                max_premium_usage = 999
                premium_percentage = 0
            else:
                premium_percentage = (premium_usage / max_premium_usage) * 100
            
            # 根据使用百分比选择颜色 / Select color based on usage percentage
            premium_color = Fore.GREEN
            if premium_percentage > 70:
                premium_color = Fore.YELLOW
            if premium_percentage > 90:
                premium_color = Fore.RED
            
            premium_display = f"{premium_usage}/{max_premium_usage} ({premium_percentage:.1f}%)"
        
        right_info.append(f"{Fore.YELLOW}{EMOJI['PREMIUM']} {translator.get('account_info.premium_usage') if translator else 'Fast Response'}: {premium_color}{premium_display}{Style.RESET_ALL}")
        
        # 基础使用量（慢速响应） / Basic usage (Slow Response)
        basic_usage = usage_info.get('basic_usage', 0)
        max_basic_usage = usage_info.get('max_basic_usage', "No Limit")
        
        # 确保值不为 None / Make sure the value is not None
        if basic_usage is None:
            basic_usage = 0
        
        # 处理"无限制"情况 / Handle "No Limit" case
        if isinstance(max_basic_usage, str) and max_basic_usage == "No Limit":
            basic_color = Fore.GREEN  # 无限制时使用绿色 / Use green when there is no limit
            basic_display = f"{basic_usage}/{max_basic_usage}"
        else:
            # 当值为数字时计算百分比 / Calculate percentage when the value is a number
            if max_basic_usage is None or max_basic_usage == 0:
                max_basic_usage = 999
                basic_percentage = 0
            else:
                basic_percentage = (basic_usage / max_basic_usage) * 100
            
            # 根据使用百分比选择颜色 / Select color based on usage percentage
            basic_color = Fore.GREEN
            if basic_percentage > 70:
                basic_color = Fore.YELLOW
            if basic_percentage > 90:
                basic_color = Fore.RED
            
            basic_display = f"{basic_usage}/{max_basic_usage} ({basic_percentage:.1f}%)"
        
        right_info.append(f"{Fore.BLUE}{EMOJI['BASIC']} {translator.get('account_info.basic_usage') if translator else 'Slow Response'}: {basic_color}{basic_display}{Style.RESET_ALL}")
    else:
        # 如果获取使用信息失败，仅在日志中记录，不在界面显示 / If get usage info failed, only log, not show in interface
        # 可以选择不显示任何使用信息，或显示简单提示 / Can choose to not show any usage info, or show a simple prompt
        # right_info.append(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('account_info.usage_unavailable') if translator else 'Usage information unavailable'}{Style.RESET_ALL}")
        pass  # 不显示任何使用信息 / Not show any usage info
    
    # 计算左侧信息的最大显示宽度 / Calculate the maximum display width of left info
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def get_display_width(s):
        """计算字符串的显示宽度，考虑中文字符和表情符号 / Calculate the display width of a string, considering Chinese characters and emojis"""
        # 移除 ANSI 颜色代码 / Remove ANSI color codes
        clean_s = ansi_escape.sub('', s)
        width = 0
        for c in clean_s:
            # 中文字符和某些表情符号占用两个字符宽度 / Chinese characters and some emojis occupy two character widths
            if ord(c) > 127:
                width += 2
            else:
                width += 1
        return width
    
    max_left_width = 0
    for item in left_info:
        width = get_display_width(item)
        max_left_width = max(max_left_width, width)
    
    # 设置右侧信息的起始位置 / Set the starting position of right info
    fixed_spacing = 4  # 固定间距 / Fixed spacing
    right_start = max_left_width + fixed_spacing
    
    # 计算右侧信息所需的空格数 / Calculate the number of spaces needed for right info
    spaces_list = []
    for i in range(len(left_info)):
        if i < len(left_info):
            left_item = left_info[i]
            left_width = get_display_width(left_item)
            spaces = right_start - left_width
            spaces_list.append(spaces)
    
    # 打印信息 / Print info
    max_rows = max(len(left_info), len(right_info))
    
    for i in range(max_rows):
        # 打印左侧信息 / Print left info
        if i < len(left_info):
            left_item = left_info[i]
            print(left_item, end='')
            
            # 使用预计算的空格数 / Use pre-calculated spaces
            spaces = spaces_list[i]
        else:
            # 如果左侧没有项目，只打印空格 / If left side has no items, print only spaces
            spaces = right_start
            print('', end='')
        
        # 打印右侧信息 / Print right info
        if i < len(right_info):
            print(' ' * spaces + right_info[i])
        else:
            print()  # 换行 / Change line
    
    print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")

def main(translator=None):
    """主函数 / Main function
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
    """
    try:
        display_account_info(translator)
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.error') if translator else 'Error'}: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()