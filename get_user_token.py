"""用户令牌获取和刷新模块 / User Token Retrieval and Refresh Module

该模块提供了获取和刷新 Cursor AI 用户令牌的功能，包括：
- 从 Cookie 中提取访问令牌
- 使用中国服务器 API 刷新令牌
- 处理令牌格式转换和验证
- 完善的错误处理和重试机制

主要功能 / Main Features:
1. 令牌刷新：通过外部 API 刷新过期的令牌
2. 令牌提取：从 WorkosCursorSessionToken Cookie 中提取有效令牌
3. 格式处理：处理 URL 编码和分隔符转换
4. 错误恢复：刷新失败时回退到传统提取方法

使用方法 / Usage:
```python
from get_user_token import get_token_from_cookie, refresh_token

# 从 Cookie 获取令牌
token = get_token_from_cookie(cookie_value)

# 刷新现有令牌
refreshed_token = refresh_token(token)
```

依赖模块 / Dependencies:
- requests: HTTP 请求处理
- colorama: 终端颜色输出
- config: 配置文件管理
"""

import requests
import json
import time
from colorama import Fore, Style
import os
from config import get_config

# 定义表情符号常量 / Define emoji constants
EMOJI = {
    'START': '🚀',     # 开始图标 / Start icon
    'OAUTH': '🔑',     # OAuth 图标 / OAuth icon
    'SUCCESS': '✅',   # 成功图标 / Success icon
    'ERROR': '❌',     # 错误图标 / Error icon
    'WAIT': '⏳',      # 等待图标 / Wait icon
    'INFO': 'ℹ️',      # 信息图标 / Info icon
    'WARNING': '⚠️'    # 警告图标 / Warning icon
}

def refresh_token(token, translator=None):
    """使用中国服务器 API 刷新令牌 / Refresh the token using the Chinese server API
    
    通过外部刷新服务器 API 来刷新过期的 Cursor 访问令牌。
    如果刷新失败，将返回原始令牌的提取部分。
    
    参数 / Args:
        token (str): 完整的 WorkosCursorSessionToken cookie 值
        translator: 可选的翻译器对象，用于多语言支持
        
    返回值 / Returns:
        str: 刷新后的访问令牌，如果刷新失败则返回原始令牌
    
    功能流程 / Process Flow:
    1. 从配置文件获取刷新服务器 URL
    2. 处理令牌的 URL 编码格式
    3. 向刷新服务器发送请求
    4. 解析响应并提取新的访问令牌
    5. 处理各种错误情况
    """
    try:
        # 获取配置信息 / Get configuration
        config = get_config(translator)
        # 从配置获取刷新服务器 URL 或使用默认值 / Get refresh_server URL from config or use default
        refresh_server = config.get('Token', 'refresh_server', fallback='https://token.cursorpro.com.cn')
        
        # 确保令牌正确进行 URL 编码 / Ensure the token is URL encoded properly
        if '%3A%3A' not in token and '::' in token:
            # 如果需要，将 :: 替换为 URL 编码版本 / Replace :: with URL encoded version if needed
            token = token.replace('::', '%3A%3A')
            
        # 向刷新服务器发送请求 / Make the request to the refresh server
        url = f"{refresh_server}/reftoken?token={token}"
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('token.refreshing') if translator else 'Refreshing token...'}{Style.RESET_ALL}")
        
        # 发送 HTTP GET 请求 / Send HTTP GET request
        response = requests.get(url, timeout=30)
        
        # 检查 HTTP 响应状态码 / Check HTTP response status code
        if response.status_code == 200:
            try:
                # 解析 JSON 响应 / Parse JSON response
                data = response.json()
                
                # 检查 API 响应是否成功 / Check if API response is successful
                if data.get('code') == 0 and data.get('msg') == "获取成功":
                    # 提取令牌和有效期信息 / Extract token and validity information
                    access_token = data.get('data', {}).get('accessToken')
                    days_left = data.get('data', {}).get('days_left', 0)
                    expire_time = data.get('data', {}).get('expire_time', 'Unknown')
                    
                    if access_token:
                        # 令牌刷新成功 / Token refresh successful
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('token.refresh_success', days=days_left, expire=expire_time) if translator else f'Token refreshed successfully! Valid for {days_left} days (expires: {expire_time})'}{Style.RESET_ALL}")
                        return access_token
                    else:
                        # 响应中没有访问令牌 / No access token in response
                        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('token.no_access_token') if translator else 'No access token in response'}{Style.RESET_ALL}")
                else:
                    # API 返回错误信息 / API returned error message
                    error_msg = data.get('msg', 'Unknown error')
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.refresh_failed', error=error_msg) if translator else f'Token refresh failed: {error_msg}'}{Style.RESET_ALL}")
            except json.JSONDecodeError:
                # JSON 解析失败 / JSON parsing failed
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.invalid_response') if translator else 'Invalid JSON response from refresh server'}{Style.RESET_ALL}")
        else:
            # HTTP 状态码错误 / HTTP status code error
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.server_error', status=response.status_code) if translator else f'Refresh server error: HTTP {response.status_code}'}{Style.RESET_ALL}")
    
    except requests.exceptions.Timeout:
        # 请求超时 / Request timeout
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.request_timeout') if translator else 'Request to refresh server timed out'}{Style.RESET_ALL}")
    except requests.exceptions.ConnectionError:
        # 连接错误 / Connection error
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.connection_error') if translator else 'Connection error to refresh server'}{Style.RESET_ALL}")
    except Exception as e:
        # 其他未预期的错误 / Other unexpected errors
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('token.unexpected_error', error=str(e)) if translator else f'Unexpected error during token refresh: {str(e)}'}{Style.RESET_ALL}")
    
    # 如果刷新失败，返回原始令牌的提取部分 / Return original token if refresh fails
    return token.split('%3A%3A')[-1] if '%3A%3A' in token else token.split('::')[-1] if '::' in token else token

def get_token_from_cookie(cookie_value):
    """
    从 Cookie 值中获取令牌，支持令牌刷新功能
    Get token from cookie value, with refresh capability
    
    Args:
        cookie_value (str): 包含令牌的 Cookie 值 / The cookie value containing the token
        
    Returns:
        str: 提取或刷新后的令牌 / The extracted or refreshed token
        
    功能流程 / Function Flow:
    1. 首先尝试刷新令牌 / First try to refresh the token
    2. 如果刷新失败，使用传统方法提取令牌 / If refresh fails, use traditional extraction method
    3. 支持 URL 编码和普通分隔符格式 / Support URL-encoded and normal separator formats
    """
    try:
        # 首先尝试刷新令牌 / Try to refresh the token first
        refreshed_token = refresh_token(cookie_value)
        if refreshed_token and refreshed_token != cookie_value:
            return refreshed_token
        
        # 如果刷新失败或返回相同值，回退到传统提取方法 / Fallback to traditional extraction if refresh fails or returns same value
        if '%3A%3A' in cookie_value:
            # 处理 URL 编码的分隔符 / Handle URL-encoded separator
            return cookie_value.split('%3A%3A')[-1]
        elif '::' in cookie_value:
            # 处理普通分隔符 / Handle normal separator
            return cookie_value.split('::')[-1]
        else:
            # 直接返回原值 / Return original value directly
            return cookie_value
    except Exception as e:
        # 处理 Cookie 时发生错误 / Error occurred while processing cookie
        print(f"{Fore.RED}{EMOJI['ERROR']} Error processing cookie: {str(e)}{Style.RESET_ALL}")
        return cookie_value