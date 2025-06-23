# -*- coding: utf-8 -*-
"""
Cursor 机器 ID 重置工具 / Cursor Machine ID Reset Tool

该脚本用于重置 Cursor 编辑器的机器标识符，包括：
- 设备 ID (devDeviceId)
- 机器 ID (machineId) 
- Mac 机器 ID (macMachineId)
- SQM ID (sqmId)
- 服务机器 ID (serviceMachineId)

功能特性：
1. 跨平台支持 (Windows, macOS, Linux)
2. 自动备份原始文件
3. 修改 Cursor 相关配置文件
4. 更新 SQLite 数据库
5. 修补 Cursor 核心文件以绕过限制
6. 版本检查和兼容性处理

使用方法：
1. 直接运行: python reset_machine_manual.py
2. 作为模块导入: from reset_machine_manual import run; run(translator)

注意事项：
- 运行前请确保 Cursor 已完全关闭
- 某些操作可能需要管理员权限
- 建议在运行前备份重要数据
"""

import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import tempfile
import glob
from colorama import Fore, Style, init
from typing import Tuple
import configparser
import traceback
from config import get_config
from datetime import datetime

# 初始化 colorama 用于彩色终端输出 / Initialize colorama for colored terminal output
init()

# 定义表情符号常量用于美化输出 / Define emoji constants for beautified output
EMOJI = {
    "FILE": "📄",      # 文件图标 / File icon
    "BACKUP": "💾",    # 备份图标 / Backup icon
    "SUCCESS": "✅",   # 成功图标 / Success icon
    "ERROR": "❌",     # 错误图标 / Error icon
    "INFO": "ℹ️",      # 信息图标 / Info icon
    "RESET": "🔄",     # 重置图标 / Reset icon
    "WARNING": "⚠️",   # 警告图标 / Warning icon
}

def get_user_documents_path():
    """获取用户文档文件夹路径 / Get user Documents folder path
    
    根据不同操作系统获取用户文档目录的正确路径
    
    Returns:
        str: 用户文档文件夹的绝对路径 / Absolute path to user's Documents folder
    """
    if sys.platform == "win32":
        try:
            # 尝试从 Windows 注册表获取文档路径 / Try to get Documents path from Windows registry
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            # 注册表读取失败时的备用方案 / Fallback when registry reading fails
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        # macOS 系统的文档路径 / Documents path for macOS
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # 获取实际用户的主目录（处理 sudo 情况）/ Get actual user's home directory (handle sudo case)
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")
     

def get_cursor_paths(translator=None) -> Tuple[str, str]:
    """获取 Cursor 相关路径 / Get Cursor related paths
    
    获取 Cursor 编辑器的 package.json 和 main.js 文件路径
    支持跨平台路径检测和配置文件管理
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        Tuple[str, str]: (package.json 路径, main.js 路径) / (package.json path, main.js path)
        
    Raises:
        OSError: 当找不到 Cursor 安装路径或文件时 / When Cursor installation path or files not found
    """
    system = platform.system()
    
    # 读取配置文件 / Read config file
    config = configparser.ConfigParser()
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    
    # 如果配置目录不存在则创建 / Create config directory if it doesn't exist
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # 不同系统的默认路径 / Default paths for different systems
    default_paths = {
        "Darwin": "/Applications/Cursor.app/Contents/Resources/app",  # macOS 路径
        "Windows": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),  # Windows 路径
        "Linux": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", os.path.expanduser("~/.local/share/cursor/resources/app"), "/usr/lib/cursor/app/"]  # Linux 多个可能路径
    }
    
    if system == "Linux":
        # 查找解压的 AppImage 文件中的正确 usr 结构 / Look for extracted AppImage with correct usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        # 同时检查当前目录中的解压文件 / Also check current directory for extraction without home path prefix
        current_dir_paths = glob.glob("squashfs-root/usr/share/cursor/resources/app")
        
        # 将找到的路径添加到 Linux 路径列表中 / Add any found paths to the Linux paths list
        default_paths["Linux"].extend(extracted_usr_paths)
        default_paths["Linux"].extend(current_dir_paths)
        
        # 打印调试信息 / Print debug information
        print(f"{Fore.CYAN}{EMOJI['INFO']} Available paths found:{Style.RESET_ALL}")
        for path in default_paths["Linux"]:
            if os.path.exists(path):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {path} (exists){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {path} (not found){Style.RESET_ALL}")
    
    
    # 如果配置文件不存在，则使用默认路径创建 / If config doesn't exist, create it with default paths
    if not os.path.exists(config_file):
        for section in ['MacPaths', 'WindowsPaths', 'LinuxPaths']:
            if not config.has_section(section):
                config.add_section(section)
        
        if system == "Darwin":
            config.set('MacPaths', 'cursor_path', default_paths["Darwin"])
        elif system == "Windows":
            config.set('WindowsPaths', 'cursor_path', default_paths["Windows"])
        elif system == "Linux":
            # 对于 Linux，尝试找到第一个存在的路径 / For Linux, try to find the first existing path
            for path in default_paths["Linux"]:
                if os.path.exists(path):
                    config.set('LinuxPaths', 'cursor_path', path)
                    break
            else:
                # 如果没有路径存在，使用第一个作为默认值 / If no path exists, use the first one as default
                config.set('LinuxPaths', 'cursor_path', default_paths["Linux"][0])
        
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(config_file, encoding='utf-8')
    
    # 根据系统获取路径 / Get path based on system
    if system == "Darwin":
        section = 'MacPaths'
    elif system == "Windows":
        section = 'WindowsPaths'
    elif system == "Linux":
        section = 'LinuxPaths'
    else:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")
    
    if not config.has_section(section) or not config.has_option(section, 'cursor_path'):
        raise OSError(translator.get('reset.path_not_configured') if translator else "未配置 Cursor 路徑")
    
    base_path = config.get(section, 'cursor_path')
    
    # 对于 Linux，如果配置的路径不存在，尝试找到第一个存在的路径 / For Linux, try to find the first existing path if the configured one doesn't exist
    if system == "Linux" and not os.path.exists(base_path):
        for path in default_paths["Linux"]:
            if os.path.exists(path):
                base_path = path
                # 用找到的路径更新配置 / Update config with the found path
                config.set(section, 'cursor_path', path)
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                break
    
    if not os.path.exists(base_path):
        raise OSError(translator.get('reset.path_not_found', path=base_path) if translator else f"找不到 Cursor 路徑: {base_path}")
    
    pkg_path = os.path.join(base_path, "package.json")
    main_path = os.path.join(base_path, "out/main.js")
    
    # 检查文件是否存在 / Check if files exist
    if not os.path.exists(pkg_path):
        raise OSError(translator.get('reset.package_not_found', path=pkg_path) if translator else f"找不到 package.json: {pkg_path}")
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.main_not_found', path=main_path) if translator else f"找不到 main.js: {main_path}")
    
    return (pkg_path, main_path)

def get_cursor_machine_id_path(translator=None) -> str:
    """获取 Cursor 机器 ID 路径 / Get Cursor machine ID path
    
    获取 Cursor 编辑器的 machineId 文件路径
    该文件存储了设备的唯一标识符
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        str: machineId 文件的完整路径 / Full path to machineId file
        
    Raises:
        OSError: 当找不到 machineId 文件时 / When machineId file not found
    """
    # 读取配置文件 / Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if sys.platform == "win32":  # Windows 系统
        if not config.has_section('WindowsPaths'):
            config.add_section('WindowsPaths')
            config.set('WindowsPaths', 'machine_id_path', 
                os.path.join(os.getenv("APPDATA"), "Cursor", "machineId"))
        return config.get('WindowsPaths', 'machine_id_path')
        
    elif sys.platform == "linux":  # Linux 系统
        if not config.has_section('LinuxPaths'):
            config.add_section('LinuxPaths')
            config.set('LinuxPaths', 'machine_id_path',
                os.path.expanduser("~/.config/cursor/machineid"))
        return config.get('LinuxPaths', 'machine_id_path')
        
    elif sys.platform == "darwin":  # macOS 系统
        if not config.has_section('MacPaths'):
            config.add_section('MacPaths')
            config.set('MacPaths', 'machine_id_path',
                os.path.expanduser("~/Library/Application Support/Cursor/machineId"))
        return config.get('MacPaths', 'machine_id_path')
        
    else:
        raise OSError(f"不支持的操作系统 / Unsupported operating system: {sys.platform}")

    # 保存配置文件的任何更改 / Save any changes to config file
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)

def get_workbench_cursor_path(translator=None) -> str:
    """获取 Cursor workbench.desktop.main.js 路径 / Get Cursor workbench.desktop.main.js path
    
    获取 Cursor 编辑器的 workbench.desktop.main.js 文件路径
    该文件包含了工作台的主要逻辑，是修改 UI 的关键文件
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        str: workbench.desktop.main.js 文件的完整路径 / Full path to workbench.desktop.main.js file
        
    Raises:
        OSError: 当找不到 workbench.desktop.main.js 文件时 / When workbench.desktop.main.js file not found
    """
    system = platform.system()

    # 读取配置文件 / Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
    
    paths_map = {
        "Darwin": {  # macOS 系统路径
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {  # Windows 系统路径
            "main": "out\\vs\\workbench\\workbench.desktop.main.js"
        },
        "Linux": {  # Linux 系统多个可能路径
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", "/usr/lib/cursor/app/"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }
    
    if system == "Linux":
        # 查找解压的 AppImage 文件中的正确 usr 结构 / Look for extracted AppImage with correct usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        # 同时检查当前目录中的解压文件 / Also check current directory for extraction without home path prefix
        current_dir_paths = glob.glob("squashfs-root/usr/share/cursor/resources/app")
        
        # 将找到的路径添加到 Linux 路径列表中 / Add any found paths to the Linux paths list
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)
        paths_map["Linux"]["bases"].extend(current_dir_paths)

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            print(f"{Fore.CYAN}{EMOJI['INFO']} Checking path: {main_path}{Style.RESET_ALL}")
            if os.path.exists(main_path):
                return main_path

    if system == "Windows":
        base_path = config.get('WindowsPaths', 'cursor_path')
    elif system == "Darwin":
        base_path = paths_map[system]["base"]
        if config.has_section('MacPaths') and config.has_option('MacPaths', 'cursor_path'):
            base_path = config.get('MacPaths', 'cursor_path')
    else:  # Linux
        # For Linux, we've already checked all bases in the loop above
        # If we're here, it means none of the bases worked, so we'll use the first one
        base_path = paths_map[system]["bases"][0]
        if config.has_section('LinuxPaths') and config.has_option('LinuxPaths', 'cursor_path'):
            base_path = config.get('LinuxPaths', 'cursor_path')

    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"未找到 Cursor main.js 文件: {main_path}")
        
    return main_path

def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """版本号检查 / Version number check
    
    检查给定的版本号是否在指定的最小和最大版本范围内
    支持标准的三段式版本号格式（如 1.2.3）
    
    Args:
        version: 要检查的版本号 / Version to check
        min_version: 最小版本要求，如果为空则不检查最小版本 / Minimum version requirement, if empty no minimum check
        max_version: 最大版本要求，如果为空则不检查最大版本 / Maximum version requirement, if empty no maximum check
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 如果版本号在指定范围内则返回 True，否则返回 False / True if version is within range, False otherwise
    """
    version_pattern = r"^\d+\.\d+\.\d+$"  # 版本号格式正则表达式 / Version number format regex
    try:
        if not re.match(version_pattern, version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            """将版本号字符串解析为元组 / Parse version string to tuple"""
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)  # 解析当前版本号 / Parse current version

        # 检查最小版本要求 / Check minimum version requirement
        if min_version and current < parse_version(min_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_low', version=version, min_version=min_version)}{Style.RESET_ALL}")
            return False

        # 检查最大版本要求 / Check maximum version requirement
        if max_version and current > parse_version(max_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_high', version=version, max_version=max_version)}{Style.RESET_ALL}")
            return False

        return True  # 版本号在允许范围内 / Version is within allowed range

    except Exception as e:
        # 版本检查过程中发生异常 / Exception occurred during version check
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e))}{Style.RESET_ALL}")
        return False

def check_cursor_version(translator) -> bool:
    """检查 Cursor 版本 / Check Cursor version
    
    读取 Cursor 的 package.json 文件并验证版本号
    确保 Cursor 版本符合最低要求
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 如果版本检查通过则返回 True，否则返回 False / True if version check passes, False otherwise
    """
    try:
        # 获取 package.json 路径 / Get package.json path
        pkg_path, _ = get_cursor_paths(translator)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.reading_package_json', path=pkg_path)}{Style.RESET_ALL}")
        
        try:
            # 尝试使用 UTF-8 编码读取文件 / Try to read file with UTF-8 encoding
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError:
            # 如果 UTF-8 读取失败，尝试其他编码 / If UTF-8 reading fails, try other encodings
            with open(pkg_path, "r", encoding="latin-1") as f:
                data = json.load(f)
                
        # 验证 JSON 数据是否为字典对象 / Verify JSON data is a dictionary object
        if not isinstance(data, dict):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
            return False
            
        # 检查是否包含版本字段 / Check if version field exists
        if "version" not in data:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_version_field')}{Style.RESET_ALL}")
            return False
            
        # 获取并验证版本号字符串 / Get and validate version string
        version = str(data["version"]).strip()
        if not version:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_field_empty')}{Style.RESET_ALL}")
            return False
            
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.found_version', version=version)}{Style.RESET_ALL}")
        
        # 检查版本号格式 / Check version format
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False
            
        # 比较版本号 / Compare versions
        try:
            current = tuple(map(int, version.split(".")))  # 解析当前版本号 / Parse current version
            min_ver = (0, 45, 0)  # 最低版本要求 / Minimum version requirement
            
            if current >= min_ver:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_check_passed', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.version_too_low', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return False
        except ValueError as e:
            # 版本号解析错误 / Version parsing error
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_parse_error', error=str(e))}{Style.RESET_ALL}")
            return False
            
    except FileNotFoundError as e:
        # package.json 文件未找到 / package.json file not found
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path)}{Style.RESET_ALL}")
        return False
    except json.JSONDecodeError as e:
        # JSON 解析错误 / JSON parsing error
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """修改 workbench.desktop.main.js 文件内容 / Modify workbench.desktop.main.js file content
    
    通过替换特定的代码模式来修改 Cursor 的 UI 界面
    包括替换"Upgrade to Pro"按钮、Badge、Token Limit、Pro 标识和 Toast 通知
    
    Args:
        file_path: workbench.desktop.main.js 文件的完整路径 / Full path to workbench.desktop.main.js file
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 如果修改成功则返回 True，否则返回 False / True if modification succeeds, False otherwise
    """
    try:
        # 保存原始文件权限 / Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # 创建临时文件 / Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # 读取原始内容 / Read original content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            # 定义需要替换的代码模式 / Define code patterns to replace
            patterns = {
                # 通用按钮替换模式 - 将"Upgrade to Pro"按钮替换为 GitHub 链接 / Universal button replacement - Replace "Upgrade to Pro" button with GitHub link
                r'B(k,D(Ln,{title:"Upgrade to Pro",size:"small",get codicon(){return A.rocket},get onClick(){return t.pay}}),null)': r'B(k,D(Ln,{title:"yeongpin GitHub",size:"small",get codicon(){return A.github},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Windows/Linux/Mac 通用按钮替换模式 / Windows/Linux/Mac universal button replacement pattern
                r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)': r'M(x,I(as,{title:"yeongpin GitHub",size:"small",get codicon(){return $.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Badge 替换 - 将"Pro Trial"替换为"Pro" / Badge replacement - Replace "Pro Trial" with "Pro"
                r'<div>Pro Trial': r'<div>Pro',

                # 自动选择文本替换 / Auto-select text replacement
                r'py-1">Auto-select': r'py-1">Bypass-Version-Pin',
                
                # Token 限制替换 - 提高 Token 限制 / Token limit replacement - Increase token limit
                r'async getEffectiveTokenLimit(e){const n=e.modelName;if(!n)return 2e5;':r'async getEffectiveTokenLimit(e){return 9000000;const n=e.modelName;if(!n)return 9e5;',
                
                # Pro 标识替换 - 在设置页面显示 Pro 状态 / Pro identifier replacement - Show Pro status in settings page
                r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>.");': r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>. <h1>Pro</h1>");',
                
                # Toast 通知替换 - 隐藏通知 Toast / Toast notification replacement - Hide notification toasts
                r'notifications-toasts': r'notifications-toasts hidden'
            }

            # 使用定义的模式进行内容替换 / Use defined patterns to replace content
            for old_pattern, new_pattern in patterns.items():
                content = content.replace(old_pattern, new_pattern)

            # 将修改后的内容写入临时文件 / Write modified content to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 创建带时间戳的原始文件备份 / Backup original file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")
        
        # 将临时文件移动到原始位置 / Move temporary file to original position
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(tmp_path, file_path)

        # 恢复原始文件权限 / Restore original permissions
        os.chmod(file_path, original_mode)
        if os.name != "nt":  # 非 Windows 系统 / Not Windows
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        # 修改文件时发生异常 / Exception occurred while modifying file
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)  # 清理临时文件 / Clean up temporary file
            except:
                pass
        return False

def modify_main_js(main_path: str, translator) -> bool:
    """修改 main.js 文件 / Modify main.js file
    
    通过正则表达式替换 getMachineId 和 getMacMachineId 函数的实现
    移除机器 ID 的获取逻辑，直接返回默认值
    
    Args:
        main_path: main.js 文件的完整路径 / Full path to main.js file
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 如果修改成功则返回 True，否则返回 False / True if modification succeeds, False otherwise
    """
    try:
        # 保存原始文件权限 / Save original file permissions
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # 创建临时文件进行修改 / Create temporary file for modification
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            # 定义正则表达式模式用于替换机器 ID 函数 / Define regex patterns for replacing machine ID functions
            patterns = {
                # 替换 getMachineId 函数，移除机器 ID 获取逻辑 / Replace getMachineId function, remove machine ID retrieval logic
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                # 替换 getMacMachineId 函数，移除 Mac 机器 ID 获取逻辑 / Replace getMacMachineId function, remove Mac machine ID retrieval logic
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            # 使用正则表达式进行模式替换 / Use regex for pattern replacement
            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            # 将修改后的内容写入临时文件 / Write modified content to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 创建带时间戳的备份文件 / Create backup file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{main_path}.old.{timestamp}"
        shutil.copy2(main_path, backup_path)
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")
        
        # 将临时文件移动到原始位置 / Move temporary file to original position
        shutil.move(tmp_path, main_path)

        # 恢复原始文件权限 / Restore original file permissions
        os.chmod(main_path, original_mode)
        if os.name != "nt":  # 非 Windows 系统 / Not Windows
            os.chown(main_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        # 修改文件时发生异常 / Exception occurred while modifying file
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)  # 清理临时文件 / Clean up temporary file
        return False

def patch_cursor_get_machine_id(translator) -> bool:
    """为 Cursor 的 getMachineId 函数打补丁 / Patch Cursor getMachineId function
    
    协调整个打补丁流程，包括获取路径、检查权限、验证版本、备份文件和修改 main.js
    这是修改 Cursor 机器 ID 获取逻辑的核心函数
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 如果打补丁成功则返回 True，否则返回 False / True if patching succeeds, False otherwise
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching')}...{Style.RESET_ALL}")
        
        # 获取 Cursor 相关文件路径 / Get Cursor related file paths
        pkg_path, main_path = get_cursor_paths(translator)
        
        # 检查文件权限 / Check file permissions
        for file_path in [pkg_path, main_path]:
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_found', path=file_path)}{Style.RESET_ALL}")
                return False
            if not os.access(file_path, os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=file_path)}{Style.RESET_ALL}")
                return False

        # 获取版本号 / Get version number
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.current_version', version=version)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_version_failed', error=str(e))}{Style.RESET_ALL}")
            return False

        # 检查版本兼容性 / Check version compatibility
        if not version_check(version, min_version="0.45.0", translator=translator):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_not_supported')}{Style.RESET_ALL}")
            return False

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.version_check_passed')}{Style.RESET_ALL}")

        # 备份原始文件 / Backup original file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{main_path}.bak.{timestamp}"
        if not os.path.exists(backup_path):
            shutil.copy2(main_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")

        # 修改文件内容 / Modify file content
        if not modify_main_js(main_path, translator):
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        # 打补丁过程中发生异常 / Exception occurred during patching
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
        return False

class MachineIDResetter:
    """Cursor 机器 ID 重置器 / Cursor Machine ID Resetter
    
    用于重置 Cursor 编辑器的机器 ID，包括清理存储文件和数据库记录
    支持 Windows、macOS 和 Linux 三个平台的路径配置
    
    Attributes:
        translator: 翻译器对象，用于多语言支持
        db_path: 存储文件路径 (storage.json)
        sqlite_path: SQLite 数据库文件路径 (state.vscdb)
    """
    
    def __init__(self, translator=None):
        """初始化机器 ID 重置器 / Initialize Machine ID Resetter
        
        Args:
            translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
            
        Raises:
            FileNotFoundError: 当配置文件不存在时抛出
            EnvironmentError: 当环境变量未设置时抛出
        """
        self.translator = translator

        # 读取配置文件 / Read configuration file
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        config.read(config_file, encoding='utf-8')

        # 检查操作系统并设置相应路径 / Check operating system and set corresponding paths
        if sys.platform == "win32":  # Windows 系统 / Windows system
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA Environment Variable Not Set")
            
            # 如果配置文件中没有 Windows 路径配置，则创建默认配置 / Create default config if Windows paths not found
            if not config.has_section('WindowsPaths'):
                config.add_section('WindowsPaths')
                config.set('WindowsPaths', 'storage_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "storage.json"
                ))
                config.set('WindowsPaths', 'sqlite_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "state.vscdb"
                ))
                
            # 从配置文件获取 Windows 平台的文件路径 / Get Windows platform file paths from config
            self.db_path = config.get('WindowsPaths', 'storage_path')
            self.sqlite_path = config.get('WindowsPaths', 'sqlite_path')
            
        elif sys.platform == "darwin":  # macOS 系统 / macOS system
            # 如果配置文件中没有 macOS 路径配置，则创建默认配置 / Create default config if macOS paths not found
            if not config.has_section('MacPaths'):
                config.add_section('MacPaths')
                config.set('MacPaths', 'storage_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
                )))
                config.set('MacPaths', 'sqlite_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
                )))
                
            # 从配置文件获取 macOS 平台的文件路径 / Get macOS platform file paths from config
            self.db_path = config.get('MacPaths', 'storage_path')
            self.sqlite_path = config.get('MacPaths', 'sqlite_path')
            
        elif sys.platform == "linux":  # Linux 系统 / Linux system
            # 如果配置文件中没有 Linux 路径配置，则创建默认配置 / Create default config if Linux paths not found
            if not config.has_section('LinuxPaths'):
                config.add_section('LinuxPaths')
                # 获取实际用户的主目录（处理 sudo 情况）/ Get actual user's home directory (handle sudo case)
                sudo_user = os.environ.get('SUDO_USER')
                actual_home = f"/home/{sudo_user}" if sudo_user else os.path.expanduser("~")
                
                config.set('LinuxPaths', 'storage_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/cursor/User/globalStorage/storage.json"
                )))
                config.set('LinuxPaths', 'sqlite_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/cursor/User/globalStorage/state.vscdb"
                )))
                
            # 从配置文件获取 Linux 平台的文件路径 / Get Linux platform file paths from config
            self.db_path = config.get('LinuxPaths', 'storage_path')
            self.sqlite_path = config.get('LinuxPaths', 'sqlite_path')
            
        else:
            # 不支持的操作系统 / Unsupported operating system
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")

        # 保存配置文件的任何更改 / Save any changes to config file
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def generate_new_ids(self):
        """生成新的机器 ID / Generate new machine ID
        
        生成一个新的 UUID 作为设备 ID，用于重置 Cursor 的机器标识
        这个方法会创建一个全新的随机 UUID 来替换原有的机器 ID
        
        Returns:
            str: 新生成的设备 ID (UUID 格式)
        """
        # 生成新的 UUID 作为设备 ID / Generate new UUID as device ID
        dev_device_id = str(uuid.uuid4())

        # 生成新的 machineId（64 位十六进制字符）/ Generate new machineId (64 characters of hexadecimal)
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()

        # 生成新的 macMachineId（128 位十六进制字符）/ Generate new macMachineId (128 characters of hexadecimal)
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()

        # 生成新的 sqmId（大写 UUID 格式）/ Generate new sqmId (uppercase UUID format)
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

        # 更新机器 ID 文件 / Update machine ID file
        self.update_machine_id_file(dev_device_id)

        # 返回所有新生成的 ID 字典 / Return dictionary of all newly generated IDs
        return {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id,  # 添加存储服务机器 ID / Add storage.serviceMachineId
        }

    def update_sqlite_db(self, new_ids):
        """更新 SQLite 数据库中的机器 ID / Update machine ID in SQLite database
        
        将新生成的机器 ID 更新到 Cursor 的 SQLite 数据库中
        如果表不存在会自动创建，使用 REPLACE 语句确保数据正确更新
        
        Args:
            new_ids (dict): 包含新机器 ID 的字典
            
        Raises:
            sqlite3.Error: 数据库操作失败时抛出
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            # 连接到 SQLite 数据库 / Connect to SQLite database
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # 创建表（如果不存在）/ Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # 准备更新数据 / Prepare update data
            updates = [
                (key, value) for key, value in new_ids.items()
            ]

            # 逐个更新每个键值对 / Update each key-value pair
            for key, value in updates:
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")

            # 提交事务并关闭连接 / Commit transaction and close connection
            conn.commit()
            conn.close()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            # 数据库操作失败 / Database operation failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_system_ids(self, new_ids):
        """更新系统级别的 ID / Update system-level IDs
        
        根据不同操作系统更新相应的系统级机器标识符
        Windows: 更新 MachineGuid 和 MachineId
        macOS: 更新平台 UUID
        Linux: 暂不支持系统级 ID 更新
        
        Args:
            new_ids (dict): 包含新机器 ID 的字典
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids')}...{Style.RESET_ALL}")
            
            # 根据操作系统执行相应的更新操作 / Execute corresponding update operations based on OS
            if sys.platform.startswith("win"):
                # Windows 系统：更新注册表中的机器 GUID 和 ID / Windows: Update MachineGuid and MachineId in registry
                self._update_windows_machine_guid()
                self._update_windows_machine_id()
            elif sys.platform == "darwin":
                # macOS 系统：更新平台 UUID / macOS: Update platform UUID
                self._update_macos_platform_uuid(new_ids)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            # 系统 ID 更新失败 / System IDs update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def _update_windows_machine_guid(self):
        """更新 Windows 系统的 MachineGuid / Update Windows MachineGuid
        
        在 Windows 注册表中更新机器 GUID，位于 HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography
        这个 GUID 是 Windows 系统用于标识机器的唯一标识符
        
        Raises:
            PermissionError: 当没有足够权限访问注册表时抛出
            Exception: 其他注册表操作异常
        """
        try:
            import winreg
            # 打开注册表项 / Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Cryptography",
                0,
                winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
            )
            # 生成新的 GUID / Generate new GUID
            new_guid = str(uuid.uuid4())
            # 设置注册表值 / Set registry value
            winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_guid_updated')}{Style.RESET_ALL}")
        except PermissionError as e:
            # 权限不足 / Permission denied
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied', error=str(e))}{Style.RESET_ALL}")
            raise
        except Exception as e:
            # 其他异常 / Other exceptions
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            raise
    
    def _update_windows_machine_id(self):
        """更新 Windows 系统的 SQMClient 注册表中的 MachineId / Update Windows MachineId in SQMClient registry
        
        在 Windows 注册表中更新 SQM (Software Quality Metrics) 客户端的机器 ID
        位于 HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\SQMClient
        如果注册表项不存在会自动创建
        
        Raises:
            PermissionError: 当没有足够权限访问注册表时抛出
            Exception: 其他注册表操作异常
        """
        try:
            import winreg
            # 1. 生成新的 GUID（大写格式）/ Generate new GUID (uppercase format)
            new_guid = "{" + str(uuid.uuid4()).upper() + "}"
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.new_machine_id')}: {new_guid}{Style.RESET_ALL}")
            
            # 2. 打开注册表项 / Open the registry key
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\SQMClient",
                    0,
                    winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                )
            except FileNotFoundError:
                # 如果注册表项不存在，则创建它 / If the key does not exist, create it
                key = winreg.CreateKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\SQMClient"
                )
            
            # 3. 设置 MachineId 值 / Set MachineId value
            winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_id_updated')}{Style.RESET_ALL}")
            return True
            
        except PermissionError:
            # 权限不足，需要管理员权限 / Permission denied, administrator privileges required
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            # 其他异常 / Other exceptions
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_id_failed', error=str(e))}{Style.RESET_ALL}")
            return False
                    

    def _update_macos_platform_uuid(self, new_ids):
        """更新 macOS 系统的平台 UUID / Update macOS Platform UUID
        
        更新 macOS 系统配置中的平台 UUID，位于系统配置文件
        /var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist
        使用 plutil 命令修改 plist 文件中的 UUID 值
        
        Args:
            new_ids (dict): 包含新机器 ID 的字典
            
        Raises:
            Exception: 当 plutil 命令执行失败或文件操作异常时抛出
        """
        try:
            # macOS 平台 UUID 配置文件路径 / macOS platform UUID config file path
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                # 使用 sudo 执行 plutil 命令更新 UUID / Use sudo to execute plutil command to update UUID
                cmd = f'sudo plutil -replace "UUID" -string "{new_ids["telemetry.macMachineId"]}" "{uuid_file}"'
                result = os.system(cmd)
                if result == 0:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                else:
                    # plutil 命令执行失败 / plutil command execution failed
                    raise Exception(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            # macOS 平台 UUID 更新失败 / macOS platform UUID update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_platform_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def reset_machine_ids(self):
        """重置机器 ID 并备份原始文件 / Reset machine ID and backup original file
        
        这是重置机器 ID 的主要方法，包括以下步骤：
        1. 检查存储文件是否存在和可访问
        2. 读取并备份原始文件
        3. 生成新的机器 ID
        4. 更新存储文件和数据库
        5. 更新系统级 ID（如果支持）
        
        Returns:
            bool: 重置成功返回 True，失败返回 False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking')}...{Style.RESET_ALL}")

            # 检查存储文件是否存在 / Check if storage file exists
            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False

            # 检查文件权限 / Check file permissions
            if not os.access(self.db_path, os.R_OK | os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission')}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.reading')}...{Style.RESET_ALL}")
            # 读取原始配置文件 / Read original configuration file
            with open(self.db_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 创建带时间戳的备份文件 / Create timestamped backup file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.bak.{timestamp}"
            print(f"{Fore.YELLOW}{EMOJI['BACKUP']} {self.translator.get('reset.creating_backup')}: {backup_path}{Style.RESET_ALL}")
            shutil.copy2(self.db_path, backup_path)

            # 生成新的机器 ID / Generate new machine IDs
            print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating')}...{Style.RESET_ALL}")
            new_ids = self.generate_new_ids()

            # 更新配置文件内容 / Update configuration file content
            config.update(new_ids)

            # 保存更新后的配置文件 / Save updated configuration file
            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.saving_json')}...{Style.RESET_ALL}")
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # 更新 SQLite 数据库 / Update SQLite database
            self.update_sqlite_db(new_ids)

            # 更新系统级 ID / Update system IDs
            self.update_system_ids(new_ids)


            # 修改 workbench.desktop.main.js 文件 / Modify workbench.desktop.main.js file
            workbench_path = get_workbench_cursor_path(self.translator)
            modify_workbench_js(workbench_path, self.translator)

            # 检查 Cursor 版本并执行相应操作 / Check Cursor version and perform corresponding actions
            greater_than_0_45 = check_cursor_version(self.translator)
            if greater_than_0_45:
                # 版本 >= 0.45.0，需要打补丁 / Version >= 0.45.0, patching required
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.detecting_version')} >= 0.45.0，{self.translator.get('reset.patching_getmachineid')}{Style.RESET_ALL}")
                patch_cursor_get_machine_id(self.translator)
            else:
                # 版本 < 0.45.0，无需打补丁 / Version < 0.45.0, no patching needed
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_less_than_0_45')}{Style.RESET_ALL}")

            # 显示成功信息和新生成的 ID / Display success message and newly generated IDs
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success')}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id')}:{Style.RESET_ALL}")
            for key, value in new_ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

            return True

        except PermissionError as e:
            # 权限错误，需要管理员权限 / Permission error, administrator privileges required
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_error', error=str(e))}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            # 其他异常，重置过程失败 / Other exceptions, reset process failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.process_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_machine_id_file(self, machine_id: str) -> bool:
        """更新机器 ID 文件 / Update machineId file with new machine_id
        
        将新的机器 ID 写入到 Cursor 的机器 ID 文件中
        如果文件已存在会先创建备份，如果目录不存在会自动创建
        
        Args:
            machine_id (str): 要写入的新机器 ID / New machine ID to write
            
        Returns:
            bool: 成功返回 True，失败返回 False / True if successful, False otherwise
        """
        try:
            # 获取机器 ID 文件路径 / Get the machineId file path
            machine_id_path = get_cursor_machine_id_path()
            
            # 如果目录不存在则创建 / Create directory if it doesn't exist
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)

            # 如果文件存在则创建备份 / Create backup if file exists
            if os.path.exists(machine_id_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{machine_id_path}.backup.{timestamp}"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created at: {backup_path}'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_creation_failed', error=str(e)) if self.translator else f'Could not create backup: {str(e)}'}{Style.RESET_ALL}")

            # 将新的机器 ID 写入文件 / Write new machine ID to file
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(machine_id)

            # 显示更新成功信息 / Display update success message
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.update_success') if self.translator else 'Successfully updated machineId file'}{Style.RESET_ALL}")
            return True

        except Exception as e:
            # 处理文件更新异常 / Handle file update exceptions
            error_msg = f"Failed to update machineId file: {str(e)}"
            if self.translator:
                error_msg = self.translator.get('reset.update_failed', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return False

def run(translator=None):
    """运行机器 ID 重置程序 / Run machine ID reset program
    
    主函数，负责执行完整的机器 ID 重置流程
    包括配置检查、显示标题、执行重置操作和等待用户确认
    
    Args:
        translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
        
    Returns:
        bool: 配置检查失败时返回 False / Returns False if config check fails
    """
    # 获取配置信息 / Get configuration
    config = get_config(translator)
    if not config:
        return False
        
    # 显示程序标题和分隔线 / Display program title and separator
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # 创建重置器实例并执行重置操作 / Create resetter instance and perform reset
    resetter = MachineIDResetter(translator)  # Correctly pass translator
    resetter.reset_machine_ids()

    # 显示结束分隔线并等待用户按键 / Display end separator and wait for user input
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")

# 主程序入口 / Main program entry point
if __name__ == "__main__":
    # 从主模块导入翻译器 / Import translator from main module
    from main import translator as main_translator
    # 运行重置程序 / Run reset program
    run(main_translator)
