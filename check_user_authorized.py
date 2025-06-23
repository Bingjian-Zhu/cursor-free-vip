# -*- coding: utf-8 -*-
"""
Cursor 用户授权检查工具 (Cursor User Authorization Checker)

功能说明：
    这个脚本用于验证 Cursor 用户的授权状态，通过调用 Cursor API 来检查用户的 token 是否有效。
    支持从数据库获取 token 或手动输入 token 进行验证。

主要功能：
    1. Token 验证：检查用户提供的 token 是否有效
    2. API 调用：使用 Cursor 官方 API 验证授权状态
    3. 校验和生成：生成符合 Cursor 要求的请求校验和
    4. 多种 Token 来源：支持从数据库、环境变量或手动输入获取 token
    5. JWT 格式检查：对 JWT 格式的 token 进行基本验证

使用方法：
    1. 直接运行脚本：
       python3 check_user_authorized.py
    
    2. 作为模块导入：
       from check_user_authorized import check_user_authorized
       is_authorized = check_user_authorized(token, translator)
    
    3. 在主程序中调用：
       通过主菜单选择相应选项

支持的 Token 来源：
    - 数据库：从 cursor_acc_info.py 模块获取
    - 环境变量：从 CURSOR_TOKEN 环境变量获取
    - 手动输入：用户直接输入 token

注意事项：
    - 需要网络连接以访问 Cursor API
    - Token 应该是有效的 Cursor 授权令牌
    - 支持 JWT 格式的 token 验证
    - 包含完整的错误处理和超时机制

作者: cursor-free-vip 项目组
GitHub: https://github.com/cursor-free-vip
"""

import os
import requests
import time
import hashlib
import base64
import struct
from colorama import Fore, Style, init

# 初始化 colorama 用于彩色输出
init()

# 定义表情符号常量，用于美化输出
EMOJI = {
    "SUCCESS": "✅",    # 成功
    "ERROR": "❌",      # 错误
    "INFO": "ℹ️",       # 信息
    "WARNING": "⚠️",    # 警告
    "KEY": "🔑",        # 密钥
    "CHECK": "🔍"       # 检查
}

def generate_hashed64_hex(input_str: str, salt: str = '') -> str:
    """
    生成 SHA-256 哈希值并返回十六进制字符串
    
    将输入字符串与盐值组合后生成 SHA-256 哈希，用于生成机器标识符。
    这是 Cursor 校验和算法的重要组成部分。
    
    Args:
        input_str (str): 输入字符串，通常是 token
        salt (str, optional): 盐值，用于增加哈希的唯一性。默认为空字符串
        
    Returns:
        str: SHA-256 哈希的十六进制字符串表示（64字符）
        
    Example:
        generate_hashed64_hex("token123", "machineId")
        # 返回: "a1b2c3d4e5f6..."
    """
    hash_obj = hashlib.sha256()
    hash_obj.update((input_str + salt).encode('utf-8'))
    return hash_obj.hexdigest()

def obfuscate_bytes(byte_array: bytearray) -> bytearray:
    """
    使用特定算法对字节数组进行混淆处理
    
    这个函数实现了与 Cursor 客户端 utils.js 中相同的字节混淆算法。
    通过异或运算和位置偏移来混淆字节数据，用于生成校验和。
    
    算法步骤：
    1. 初始化混淆因子 t = 165
    2. 对每个字节进行异或运算和位置偏移
    3. 更新混淆因子为当前处理的字节值
    4. 确保结果在 0-255 范围内
    
    Args:
        byte_array (bytearray): 需要混淆的字节数组
        
    Returns:
        bytearray: 混淆后的字节数组
        
    Note:
        这个算法必须与 Cursor 客户端保持一致，否则校验和验证会失败
    """
    t = 165  # 初始混淆因子
    for r in range(len(byte_array)):
        # 对当前字节进行异或运算，加上位置偏移，并确保在字节范围内
        byte_array[r] = ((byte_array[r] ^ t) + (r % 256)) & 0xFF
        # 更新混淆因子为当前字节值
        t = byte_array[r]
    return byte_array

def generate_cursor_checksum(token: str, translator=None) -> str:
    """
    生成 Cursor API 请求所需的校验和
    
    这个函数实现了 Cursor 客户端的校验和生成算法，用于验证 API 请求的合法性。
    校验和包含时间戳、机器标识符等信息，必须与服务端算法保持一致。
    
    算法流程：
    1. 清理 token 字符串
    2. 生成 machineId 和 macMachineId 哈希
    3. 获取当前时间戳并转换为字节数组
    4. 对时间戳字节进行混淆处理
    5. 将混淆后的字节编码为 base64
    6. 组合最终的校验和字符串
    
    Args:
        token (str): 用户的授权 token
        translator: 翻译器对象，用于多语言支持
        
    Returns:
        str: 生成的校验和字符串，格式为 "base64_encoded_timestamp + machineId/macMachineId"
             如果生成失败则返回空字符串
             
    Example:
        checksum = generate_cursor_checksum("user_token")
        # 返回: "AbCdEf123456...a1b2c3.../d4e5f6..."
    """
    try:
        # 清理 token，移除首尾空白字符
        clean_token = token.strip()
        
        # 生成机器标识符哈希
        machine_id = generate_hashed64_hex(clean_token, 'machineId')
        mac_machine_id = generate_hashed64_hex(clean_token, 'macMachineId')
        
        # 获取当前时间戳（毫秒）并转换为特定格式
        timestamp = int(time.time() * 1000) // 1000000
        # 将时间戳打包为大端序 8 字节，然后取最后 6 字节
        byte_array = bytearray(struct.pack('>Q', timestamp)[-6:])
        
        # 对时间戳字节进行混淆处理
        obfuscated_bytes = obfuscate_bytes(byte_array)
        # 将混淆后的字节编码为 base64
        encoded_checksum = base64.b64encode(obfuscated_bytes).decode('utf-8')
        
        # 组合最终的校验和：base64编码的时间戳 + machineId/macMachineId
        return f"{encoded_checksum}{machine_id}/{mac_machine_id}"
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.error_generating_checksum', error=str(e)) if translator else f'Error generating checksum: {str(e)}'}{Style.RESET_ALL}")
        return ""

def check_user_authorized(token: str, translator=None) -> bool:
    """
    检查用户是否使用给定的 token 获得授权
    
    这个函数是主要的授权检查入口，通过调用 Cursor 的 DashboardService API
    来验证用户的授权状态。它会处理 token 的清理、格式验证，并发送请求
    到 Cursor 服务器进行验证。
    
    验证流程：
    1. 清理和验证 token 格式
    2. 生成请求校验和
    3. 构造 API 请求头
    4. 调用 DashboardService API
    5. 根据响应状态判断授权结果
    
    Args:
        token (str): 授权 token，支持多种格式：
                    - 完整格式："prefix%3A%3Atoken" 或 "prefix::token"
                    - 纯 token 格式："eyJ..."
        translator: 可选的翻译器对象，用于国际化支持
    
    Returns:
        bool: True 表示用户已授权，False 表示未授权或验证失败
        
    Note:
        - 支持从环境变量或数据库获取 token
        - 对 JWT 格式的 token 有特殊处理逻辑
        - 网络异常时会有降级处理机制
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['CHECK']} {translator.get('auth_check.checking_authorization') if translator else 'Checking authorization...'}{Style.RESET_ALL}")
        
        # 清理 token：处理不同的 token 格式
        if token and '%3A%3A' in token:
            # 处理 URL 编码的分隔符格式
            token = token.split('%3A%3A')[1]
        elif token and '::' in token:
            # 处理普通的双冒号分隔符格式
            token = token.split('::')[1]
        
        # 移除首尾空白字符
        token = token.strip()
        
        # 基本的 token 长度验证
        if not token or len(token) < 10:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.invalid_token') if translator else 'Invalid token'}{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_length', length=len(token)) if translator else f'Token length: {len(token)} characters'}{Style.RESET_ALL}")
        
        # 尝试使用 DashboardService API 获取使用信息
        try:
            # 生成请求校验和
            checksum = generate_cursor_checksum(token, translator)
            
            # 创建请求头，模拟真实的 Cursor 客户端
            headers = {
                'accept-encoding': 'gzip',  # 支持 gzip 压缩
                'authorization': f'Bearer {token}',  # Bearer token 授权
                'connect-protocol-version': '1',  # Connect 协议版本
                'content-type': 'application/proto',  # Protobuf 内容类型
                'user-agent': 'connect-es/1.6.1',  # 客户端标识
                'x-cursor-checksum': checksum,  # 自定义校验和
                'x-cursor-client-version': '0.48.7',  # Cursor 客户端版本
                'x-cursor-timezone': 'Asia/Shanghai',  # 时区信息
                'x-ghost-mode': 'false',  # 幽灵模式标识
                'Host': 'api2.cursor.sh'  # 主机头
            }
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.checking_usage_information') if translator else 'Checking usage information...'}{Style.RESET_ALL}")
            
            # 发送 API 请求 - 此端点不需要请求体
            usage_response = requests.post(
                'https://api2.cursor.sh/aiserver.v1.DashboardService/GetUsageBasedPremiumRequests',
                headers=headers,
                data=b'',  # 空请求体
                timeout=10  # 10秒超时
            )
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.usage_response', response=usage_response.status_code) if translator else f'Usage response status: {usage_response.status_code}'}{Style.RESET_ALL}")
            
            # 根据响应状态码判断授权结果
            if usage_response.status_code == 200:
                # 200 状态码表示请求成功，用户已授权
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.user_authorized') if translator else 'User is authorized'}{Style.RESET_ALL}")
                return True
            elif usage_response.status_code == 401 or usage_response.status_code == 403:
                # 401/403 状态码表示未授权
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.user_unauthorized') if translator else 'User is unauthorized'}{Style.RESET_ALL}")
                return False
            else:
                # 其他状态码的处理
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.unexpected_status_code', code=usage_response.status_code) if translator else f'Unexpected status code: {usage_response.status_code}'}{Style.RESET_ALL}")
                
                # 如果 token 看起来像有效的 JWT，则认为它是有效的
                if token.startswith('eyJ') and '.' in token and len(token) > 100:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check returned an unexpected status code. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                    return True
                
                return False
        except Exception as e:
            # API 调用异常处理
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} Error checking usage: {str(e)}{Style.RESET_ALL}")
            
            # 即使 API 检查失败，如果 token 看起来像有效的 JWT，也认为它是有效的
            if token.startswith('eyJ') and '.' in token and len(token) > 100:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.jwt_token_warning') if translator else 'Token appears to be in JWT format, but API check failed. The token might be valid but API access is restricted.'}{Style.RESET_ALL}")
                return True
            
            return False
            
    except requests.exceptions.Timeout:
        # 请求超时异常
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.request_timeout') if translator else 'Request timed out'}{Style.RESET_ALL}")
        return False
    except requests.exceptions.ConnectionError:
        # 网络连接异常
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.connection_error') if translator else 'Connection error'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        # 其他未预期的异常
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.check_error', error=str(e)) if translator else f'Error checking authorization: {str(e)}'}{Style.RESET_ALL}")
        return False

def run(translator=None):
    """
    主运行函数，用于从 main.py 调用
    
    这个函数提供了完整的用户交互流程，支持多种 token 获取方式：
    1. 从数据库自动获取（默认）
    2. 手动输入
    3. 从环境变量获取
    
    Args:
        translator: 可选的翻译器对象，用于国际化支持
        
    Returns:
        bool: True 表示授权成功，False 表示授权失败或操作取消
        
    Note:
        - 支持用户中断操作（Ctrl+C）
        - 会尝试导入 cursor_acc_info.py 模块获取 token
        - 包含完整的错误处理和用户提示
    """
    try:
        # 询问用户是否从数据库获取 token 或手动输入
        choice = input(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.token_source') if translator else 'Get token from database or input manually? (d/m, default: d): '}{Style.RESET_ALL}").strip().lower()
        
        token = None
        
        # 如果用户选择数据库或使用默认选项
        if not choice or choice == 'd':
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth_check.getting_token_from_db') if translator else 'Getting token from database...'}{Style.RESET_ALL}")
            
            try:
                # 从 cursor_acc_info.py 导入函数
                from cursor_acc_info import get_token
                
                # 使用 get_token 函数获取 token
                token = get_token()
                
                if token:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.token_found_in_db') if translator else 'Token found in database'}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.token_not_found_in_db') if translator else 'Token not found in database'}{Style.RESET_ALL}")
            except ImportError:
                # cursor_acc_info.py 模块不存在
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.cursor_acc_info_not_found') if translator else 'cursor_acc_info.py not found'}{Style.RESET_ALL}")
            except Exception as e:
                # 从数据库获取 token 时发生错误
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.error_getting_token_from_db', error=str(e)) if translator else f'Error getting token from database: {str(e)}'}{Style.RESET_ALL}")
        
        # 如果数据库中未找到 token 或用户选择手动输入
        if not token:
            # 尝试从环境变量获取 token
            token = os.environ.get('CURSOR_TOKEN')
            
            # 如果环境变量中也没有，则要求用户输入
            if not token:
                token = input(f"{Fore.CYAN}{EMOJI['KEY']} {translator.get('auth_check.enter_token') if translator else 'Enter your Cursor token: '}{Style.RESET_ALL}")
        
        # 执行授权检查
        is_authorized = check_user_authorized(token, translator)
        
        # 显示最终结果
        if is_authorized:
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth_check.authorization_successful') if translator else 'Authorization successful!'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.authorization_failed') if translator else 'Authorization failed!'}{Style.RESET_ALL}")
        
        return is_authorized
        
    except KeyboardInterrupt:
        # 用户中断操作（Ctrl+C）
        print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('auth_check.operation_cancelled') if translator else 'Operation cancelled by user'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        # 其他未预期的异常
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth_check.unexpected_error', error=str(e)) if translator else f'Unexpected error: {str(e)}'}{Style.RESET_ALL}")
        return False

def main(translator=None):
    """
    主函数，用于检查用户授权
    
    这是脚本的主入口点，直接调用 run 函数执行授权检查。
    
    Args:
        translator: 可选的翻译器对象，用于国际化支持
        
    Returns:
        bool: 授权检查的结果
    """
    return run(translator)

# 脚本作为独立程序运行时的入口点
if __name__ == "__main__":
    main()