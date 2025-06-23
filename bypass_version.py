# -*- coding: utf-8 -*-
"""
Cursor 版本绕过工具 (Cursor Version Bypass Tool)

功能说明：
    这个脚本用于绕过 Cursor 编辑器的版本检查，通过修改 product.json 文件中的版本号
    来解决某些功能需要特定版本才能使用的问题。

支持的操作系统：
    - Windows: 修改 %LOCALAPPDATA%/Programs/Cursor/resources/app/product.json
    - macOS: 修改 /Applications/Cursor.app/Contents/Resources/app/product.json
    - Linux: 支持多种安装路径，包括 AppImage 提取路径

使用方法：
    1. 直接运行脚本：
       python3 bypass_version.py
    
    2. 作为模块导入：
       from bypass_version import bypass_version
       bypass_version(translator)
    
    3. 在主程序中调用：
       通过主菜单选择相应选项

注意事项：
    - 运行前请关闭 Cursor 编辑器
    - 需要对 Cursor 安装目录有写入权限
    - 脚本会自动备份原始 product.json 文件
    - 仅在版本低于 0.46.0 时才会进行修改

作者: cursor-free-vip 项目组
GitHub: https://github.com/cursor-free-vip
"""

import os
import json
import shutil
import platform
import configparser
import time
from colorama import Fore, Style, init
import sys
import traceback
from utils import get_user_documents_path

# 初始化 colorama 用于彩色输出
init()

# 定义表情符号常量，用于美化输出
EMOJI = {
    'INFO': 'ℹ️',        # 信息
    'SUCCESS': '✅',     # 成功
    'ERROR': '❌',       # 错误
    'WARNING': '⚠️',     # 警告
    'FILE': '📄',        # 文件
    'BACKUP': '💾',      # 备份
    'RESET': '🔄',       # 重置
    'VERSION': '🏷️'      # 版本
}

def get_product_json_path(translator=None):
    """
    获取 Cursor 的 product.json 文件路径
    
    根据不同的操作系统和配置文件，自动定位 Cursor 的 product.json 文件。
    该文件包含了 Cursor 的版本信息和其他产品配置。
    
    Args:
        translator: 翻译器对象，用于多语言支持
        
    Returns:
        str: product.json 文件的完整路径
        
    Raises:
        OSError: 当文件不存在或操作系统不支持时抛出异常
    """
    system = platform.system()
    
    # 读取配置文件，获取自定义路径
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if system == "Windows":
        # Windows 系统：从 LOCALAPPDATA 环境变量获取路径
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            raise OSError(translator.get('bypass.localappdata_not_found') if translator else "LOCALAPPDATA environment variable not found")
        
        # 默认 Windows 安装路径
        product_json_path = os.path.join(localappdata, "Programs", "Cursor", "resources", "app", "product.json")
        
        # 检查配置文件中是否有自定义路径
        if 'WindowsPaths' in config and 'cursor_path' in config['WindowsPaths']:
            cursor_path = config.get('WindowsPaths', 'cursor_path')
            product_json_path = os.path.join(cursor_path, "product.json")
    
    elif system == "Darwin":  # macOS 系统
        # 默认 macOS 安装路径
        product_json_path = "/Applications/Cursor.app/Contents/Resources/app/product.json"
        # 检查配置文件中是否有自定义路径
        if config.has_section('MacPaths') and config.has_option('MacPaths', 'product_json_path'):
            product_json_path = config.get('MacPaths', 'product_json_path')
    
    elif system == "Linux":
        # Linux 系统：尝试多个常见的安装路径
        possible_paths = [
            "/opt/Cursor/resources/app/product.json",                    # 标准安装路径
            "/usr/share/cursor/resources/app/product.json",             # 系统级安装
            "/usr/lib/cursor/app/product.json"                          # 库文件路径
        ]
        
        # 添加 AppImage 提取后的路径
        extracted_usr_paths = os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app/product.json")
        if os.path.exists(extracted_usr_paths):
            possible_paths.append(extracted_usr_paths)
        
        # 遍历可能的路径，找到第一个存在的文件
        for path in possible_paths:
            if os.path.exists(path):
                product_json_path = path
                break
        else:
            # 如果所有路径都不存在，抛出异常
            raise OSError(translator.get('bypass.product_json_not_found') if translator else "product.json not found in common Linux paths")
    
    else:
        # 不支持的操作系统
        raise OSError(translator.get('bypass.unsupported_os', system=system) if translator else f"Unsupported operating system: {system}")
    
    # 最终检查文件是否存在
    if not os.path.exists(product_json_path):
        raise OSError(translator.get('bypass.file_not_found', path=product_json_path) if translator else f"File not found: {product_json_path}")
    
    return product_json_path

def compare_versions(version1, version2):
    """
    比较两个版本号字符串
    
    使用语义化版本号比较规则，支持形如 "1.2.3" 的版本号格式。
    比较时会将版本号按点分割，然后逐个数字进行比较。
    
    Args:
        version1 (str): 第一个版本号，如 "0.45.0"
        version2 (str): 第二个版本号，如 "0.46.0"
        
    Returns:
        int: 比较结果
            -1: version1 < version2
             0: version1 == version2
             1: version1 > version2
             
    Example:
        compare_versions("0.45.0", "0.46.0")  # 返回 -1
        compare_versions("0.46.0", "0.46.0")  # 返回 0
        compare_versions("0.47.0", "0.46.0")  # 返回 1
    """
    # 将版本号按点分割并转换为整数列表
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
    # 逐个比较版本号的每一部分
    for i in range(max(len(v1_parts), len(v2_parts))):
        # 如果某个版本号的部分较少，用 0 补齐
        v1 = v1_parts[i] if i < len(v1_parts) else 0
        v2 = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
    
    # 所有部分都相等
    return 0

def bypass_version(translator=None):
    """
    绕过 Cursor 版本检查的主函数
    
    通过修改 product.json 文件中的版本号来绕过 Cursor 的版本检查。
    该函数会自动检测当前版本，如果低于 0.46.0 则会将其修改为 0.48.7。
    
    执行流程：
    1. 获取 product.json 文件路径
    2. 检查文件权限
    3. 读取当前版本信息
    4. 比较版本号，决定是否需要修改
    5. 备份原始文件
    6. 修改版本号并保存
    
    Args:
        translator: 翻译器对象，用于多语言支持
        
    Returns:
        bool: 操作成功返回 True，失败返回 False
    """
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('bypass.starting') if translator else 'Starting Cursor version bypass...'}{Style.RESET_ALL}")
        
        # 获取 product.json 文件路径
        product_json_path = get_product_json_path(translator)
        print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('bypass.found_product_json', path=product_json_path) if translator else f'Found product.json: {product_json_path}'}{Style.RESET_ALL}")
        
        # 检查文件写入权限
        if not os.access(product_json_path, os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.no_write_permission', path=product_json_path) if translator else f'No write permission for file: {product_json_path}'}{Style.RESET_ALL}")
            return False
        
        # 读取 product.json 文件内容
        try:
            with open(product_json_path, "r", encoding="utf-8") as f:
                product_data = json.load(f)
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.read_failed', error=str(e)) if translator else f'Failed to read product.json: {str(e)}'}{Style.RESET_ALL}")
            return False
        
        # 获取当前版本号
        current_version = product_data.get("version", "0.0.0")
        print(f"{Fore.CYAN}{EMOJI['VERSION']} {translator.get('bypass.current_version', version=current_version) if translator else f'Current version: {current_version}'}{Style.RESET_ALL}")
        
        # 检查是否需要修改版本号（仅当版本低于 0.46.0 时）
        if compare_versions(current_version, "0.46.0") < 0:
            # 创建备份文件
            timestamp = time.strftime("%Y%m%d%H%M%S")
            backup_path = f"{product_json_path}.{timestamp}"
            shutil.copy2(product_json_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('bypass.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            
            # 修改版本号为目标版本
            new_version = "0.48.7"
            product_data["version"] = new_version
            
            # 保存修改后的 product.json 文件
            try:
                with open(product_json_path, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, indent=2)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.version_updated', old=current_version, new=new_version) if translator else f'Version updated from {current_version} to {new_version}'}{Style.RESET_ALL}")
                return True
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.write_failed', error=str(e)) if translator else f'Failed to write product.json: {str(e)}'}{Style.RESET_ALL}")
                return False
        else:
            # 版本已经足够新，无需修改
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.no_update_needed', version=current_version) if translator else f'No update needed. Current version {current_version} is already >= 0.46.0'}{Style.RESET_ALL}")
            return True
    
    except Exception as e:
        # 捕获并处理所有未预期的异常
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.bypass_failed', error=str(e)) if translator else f'Version bypass failed: {str(e)}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.stack_trace') if translator else 'Stack trace'}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def main(translator=None):
    """
    主函数入口
    
    提供一个简单的接口来调用版本绕过功能。
    
    Args:
        translator: 翻译器对象，用于多语言支持
        
    Returns:
        bool: 操作结果
    """
    return bypass_version(translator)

# 直接运行脚本时的入口点
if __name__ == "__main__":
    """
    当脚本被直接执行时调用主函数
    
    这允许用户直接运行此脚本来执行版本绕过操作，
    而不需要通过主程序界面。
    """
    main()