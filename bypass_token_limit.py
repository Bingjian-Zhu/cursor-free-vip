#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Token 限制绕过工具

这个脚本用于绕过 Cursor 编辑器的 Token 使用限制，通过修改 Cursor 的主要 JavaScript 文件
来实现无限制的 Token 使用。脚本会自动定位 Cursor 的安装路径，备份原始文件，
然后应用必要的修改来移除 Token 限制。

主要功能：
- 自动检测 Cursor 安装路径（支持 Windows、macOS、Linux）
- 修改 workbench.desktop.main.js 文件以绕过 Token 限制
- 创建原始文件的时间戳备份
- 替换界面元素（如将 "Upgrade to Pro" 按钮改为 GitHub 链接）
- 隐藏通知提示
- 显示 Pro 状态

支持的操作系统：
- Windows: 从配置文件读取 Cursor 路径
- macOS: /Applications/Cursor.app/Contents/Resources/app/
- Linux: 多个可能的安装路径，包括 AppImage 提取路径

使用方法：
1. 直接运行: python bypass_token_limit.py
2. 作为模块导入: from bypass_token_limit import run

注意事项：
- 需要对 Cursor 安装目录有写入权限
- 修改前会自动创建备份文件
- 建议在 Cursor 关闭状态下运行
- 每次 Cursor 更新后可能需要重新运行

作者: yeongpin
GitHub: https://github.com/yeongpin/cursor-free-vip
"""

import os
import shutil
import platform
import tempfile
import glob
from colorama import Fore, Style, init
import configparser
import sys
from config import get_config
from datetime import datetime

# 初始化 colorama 用于彩色终端输出
init()

# 定义表情符号常量，用于美化终端输出
EMOJI = {
    "FILE": "📄",      # 文件图标
    "BACKUP": "💾",    # 备份图标
    "SUCCESS": "✅",   # 成功图标
    "ERROR": "❌",     # 错误图标
    "INFO": "ℹ️",      # 信息图标
    "RESET": "🔄",     # 重置图标
    "WARNING": "⚠️",   # 警告图标
}

def get_user_documents_path():
    """
    获取用户文档文件夹路径
    
    这个函数根据不同的操作系统获取用户的文档目录路径。
    在 Windows 系统中，会尝试从注册表读取实际的文档路径，
    如果失败则使用默认路径。
    
    Returns:
        str: 用户文档文件夹的完整路径
        
    Note:
        - Windows: 从注册表读取或使用 ~/Documents
        - macOS: ~/Documents
        - Linux: 处理 sudo 用户情况，优先使用实际用户的文档目录
    """
    if sys.platform == "win32":
        try:
            # 尝试从 Windows 注册表读取文档路径
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:
                documents_path, _ = winreg.QueryValueEx(key, "Personal")
                return documents_path
        except Exception as e:
            # 注册表读取失败时的备用方案
            return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        # macOS 系统的文档路径
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # 获取实际用户的主目录（处理 sudo 执行的情况）
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            # 如果是通过 sudo 执行，使用原始用户的文档目录
            return os.path.join("/home", sudo_user, "Documents")
        # 普通情况下使用当前用户的文档目录
        return os.path.join(os.path.expanduser("~"), "Documents")
     

def get_workbench_cursor_path(translator=None) -> str:
    """
    获取 Cursor workbench.desktop.main.js 文件路径
    
    这个函数负责定位 Cursor 编辑器的主要 JavaScript 文件，该文件包含了
    需要修改的 Token 限制逻辑。函数会根据不同的操作系统和配置文件
    来确定正确的文件路径。
    
    Args:
        translator: 可选的翻译器对象，用于国际化支持
        
    Returns:
        str: workbench.desktop.main.js 文件的完整路径
        
    Raises:
        OSError: 当不支持的操作系统或找不到文件时抛出
        
    Note:
        - 支持从配置文件读取自定义路径
        - Linux 系统会检查多个可能的安装位置
        - 包括对 AppImage 提取路径的支持
    """
    system = platform.system()

    # 读取配置文件以获取自定义路径
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
    
    # 定义不同操作系统的 Cursor 安装路径映射
    paths_map = {
        "Darwin": {  # macOS 系统
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {  # Windows 系统
            "main": "out\\vs\\workbench\\workbench.desktop.main.js"
        },
        "Linux": {  # Linux 系统
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", "/usr/lib/cursor/app/"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }
    
    if system == "Linux":
        # 为 Linux 系统添加 AppImage 提取路径支持
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
            
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)

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


def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    修改 Cursor workbench.desktop.main.js 文件内容
    
    这个函数是脚本的核心功能，负责修改 Cursor 编辑器的主要 JavaScript 文件
    来绕过 Token 限制。函数会创建文件备份，然后应用一系列字符串替换
    来修改界面元素和功能逻辑。
    
    主要修改内容：
    - 将 "Upgrade to Pro" 按钮替换为 GitHub 链接
    - 修改 Token 限制逻辑，返回大数值（9,000,000）
    - 将 "Pro Trial" 显示为 "Pro"
    - 隐藏通知提示（Toast）
    - 在设置页面显示 Pro 状态
    
    Args:
        file_path (str): workbench.desktop.main.js 文件的完整路径
        translator: 可选的翻译器对象，用于国际化消息显示
        
    Returns:
        bool: 修改成功返回 True，失败返回 False
        
    Note:
        - 修改前会自动创建带时间戳的备份文件
        - 保持原始文件的权限和所有者信息
        - 使用临时文件确保操作的原子性
        - 支持不同操作系统的按钮替换模式
    """
    try:
        # 保存原始文件的权限信息，以便后续恢复
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode  # 文件权限模式
        original_uid = original_stat.st_uid    # 文件所有者 ID
        original_gid = original_stat.st_gid    # 文件组 ID

        # 创建临时文件用于安全地写入修改后的内容
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # 读取原始文件内容
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            # 定义需要替换的模式字典，每个模式对应一个特定的功能修改
            patterns = {
                # 通用按钮替换模式 - 将升级按钮替换为 GitHub 链接
                r'B(k,D(Ln,{title:"Upgrade to Pro",size:"small",get codicon(){return A.rocket},get onClick(){return t.pay}}),null)': r'B(k,D(Ln,{title:"yeongpin GitHub",size:"small",get codicon(){return A.github},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # Windows/Linux 系统的按钮替换模式
                r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)': r'M(x,I(as,{title:"yeongpin GitHub",size:"small",get codicon(){return $.github},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # macOS 系统的按钮替换模式
                r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)': r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)',
                
                # 将试用版标识替换为正式版
                r'<div>Pro Trial': r'<div>Pro',

                # 替换自动选择文本为绕过版本锁定
                r'py-1">Auto-select': r'py-1">Bypass-Version-Pin',
                
                # 核心功能：修改 Token 限制函数，返回大数值以绕过限制
                r'async getEffectiveTokenLimit(e){const n=e.modelName;if(!n)return 2e5;':r'async getEffectiveTokenLimit(e){return 9000000;const n=e.modelName;if(!n)return 9e5;',
                
                # 在设置页面显示 Pro 状态
                r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>.");': r'var DWr=ne("<div class=settings__item_description>You are currently signed in with <strong></strong>. <h1>Pro</h1>");',
                
                # 隐藏通知提示（Toast 消息）
                r'notifications-toasts': r'notifications-toasts hidden'
            }

            # 遍历所有替换模式，逐一应用到文件内容中
            for old_pattern, new_pattern in patterns.items():
                content = content.replace(old_pattern, new_pattern)

            # 将修改后的内容写入临时文件
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 创建原始文件的时间戳备份
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        shutil.copy2(file_path, backup_path)  # 复制文件并保持元数据
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")
        
        # 将临时文件移动到原始文件位置（原子操作）
        if os.path.exists(file_path):
            os.remove(file_path)  # 删除原始文件
        shutil.move(tmp_path, file_path)  # 移动临时文件到目标位置

        # 恢复原始文件的权限和所有者信息
        os.chmod(file_path, original_mode)  # 恢复文件权限
        if os.name != "nt":  # 非 Windows 系统需要恢复所有者信息
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        # 异常处理：显示错误信息并清理临时文件
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        # 清理可能存在的临时文件
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)  # 删除临时文件
            except:
                pass  # 忽略删除失败的情况
        return False
    
def run(translator=None):
    """
    主运行函数 - 执行 Token 限制绕过操作
    
    这个函数是脚本的主入口点，负责协调整个绕过过程。
    它会获取配置、显示界面、执行文件修改，并等待用户确认。
    
    Args:
        translator: 可选的翻译器对象，用于国际化支持
        
    Returns:
        bool: 操作成功返回 True，失败返回 False
        
    执行流程：
    1. 获取配置信息
    2. 显示操作标题
    3. 定位并修改 workbench.desktop.main.js 文件
    4. 等待用户按键确认
    """
    # 获取配置信息，如果配置无效则退出
    config = get_config(translator)
    if not config:
        return False
        
    # 显示操作标题和分隔线
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('bypass_token_limit.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # 执行核心操作：修改 workbench.desktop.main.js 文件
    modify_workbench_js(get_workbench_cursor_path(translator), translator)

    # 显示完成信息并等待用户确认
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('bypass_token_limit.press_enter')}...")

# 脚本主入口点 - 当作为独立程序运行时执行
if __name__ == "__main__":
    # 从主模块导入翻译器并运行
    from main import translator as main_translator
    run(main_translator)