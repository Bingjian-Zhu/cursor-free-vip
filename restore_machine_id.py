"""机器 ID 恢复工具 / Machine ID Restore Tool

该模块用于恢复之前备份的 Cursor 机器 ID，包括：
- 从备份文件中恢复机器标识符
- 更新 storage.json 配置文件
- 更新 SQLite 数据库中的 ID 记录
- 更新系统级机器 ID（Windows/macOS）
- 恢复 machineId 文件

This module is used to restore previously backed up Cursor machine IDs, including:
- Restoring machine identifiers from backup files
- Updating storage.json configuration file
- Updating ID records in SQLite database
- Updating system-level machine IDs (Windows/macOS)
- Restoring machineId file
"""

# 标准库导入 / Standard library imports
import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import glob
import tempfile
from datetime import datetime
import configparser
import traceback
from typing import Tuple

# 第三方库导入 / Third-party library imports
from colorama import Fore, Style, init

# 本地模块导入 / Local module imports
from config import get_config
from reset_machine_manual import get_cursor_machine_id_path, get_user_documents_path

# 初始化 colorama 用于彩色终端输出 / Initialize colorama for colored terminal output
init()

# 定义表情符号常量用于美化输出 / Define emoji constants for beautifying output
EMOJI = {
    "FILE": "📄",      # 文件图标 / File icon
    "BACKUP": "💾",    # 备份图标 / Backup icon
    "SUCCESS": "✅",   # 成功图标 / Success icon
    "ERROR": "❌",     # 错误图标 / Error icon
    "INFO": "ℹ️",      # 信息图标 / Info icon
    "RESET": "🔄",     # 重置图标 / Reset icon
    "WARNING": "⚠️",   # 警告图标 / Warning icon
}

class ConfigError(Exception):
    """配置错误异常类 / Configuration error exception class
    
    当配置文件缺失、格式错误或配置项不完整时抛出此异常
    Raised when config file is missing, malformed, or incomplete
    """
    pass

class MachineIDRestorer:
    """机器 ID 恢复器类 / Machine ID Restorer Class
    
    负责恢复之前备份的 Cursor 机器 ID，支持多平台操作
    包括 Windows、macOS 和 Linux 系统的机器 ID 恢复功能
    
    Responsible for restoring previously backed up Cursor machine IDs, supporting multi-platform operations
    Including machine ID restore functionality for Windows, macOS and Linux systems
    """
    
    def __init__(self, translator=None):
        """初始化机器 ID 恢复器 / Initialize Machine ID Restorer
        
        读取配置文件并根据当前操作系统设置相应的文件路径
        包括 storage.json 和 SQLite 数据库的路径配置
        
        Args:
            translator: 翻译器对象，用于多语言支持 / Translator object for multi-language support
            
        Raises:
            FileNotFoundError: 配置文件不存在时抛出 / Raised when config file doesn't exist
            ConfigError: 配置文件格式错误或缺少必要配置项时抛出 / Raised when config is malformed or missing required sections
            EnvironmentError: 环境变量缺失时抛出 / Raised when required environment variables are missing
            NotImplementedError: 不支持的操作系统时抛出 / Raised when OS is not supported
        """
        self.translator = translator
        
        # 读取配置文件 / Read configuration file
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        config = configparser.ConfigParser()
        
        # 检查配置文件是否存在 / Check if config file exists
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        config.read(config_file, encoding='utf-8')
        
        # 根据操作系统获取相应的文件路径 / Get file paths according to operating system
        if sys.platform == "win32":  # Windows 系统 / Windows system
            # 检查 APPDATA 环境变量 / Check APPDATA environment variable
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA Environment Variable Not Set")
            
            # 检查 Windows 路径配置节是否存在 / Check if WindowsPaths config section exists
            if not config.has_section('WindowsPaths'):
                raise ConfigError("WindowsPaths section not found in config")
                
            # 获取 Windows 系统的文件路径 / Get file paths for Windows system
            self.db_path = config.get('WindowsPaths', 'storage_path')
            self.sqlite_path = config.get('WindowsPaths', 'sqlite_path')
            
        elif sys.platform == "darwin":  # macOS 系统 / macOS system
            # 检查 macOS 路径配置节是否存在 / Check if MacPaths config section exists
            if not config.has_section('MacPaths'):
                raise ConfigError("MacPaths section not found in config")
                
            # 获取 macOS 系统的文件路径 / Get file paths for macOS system
            self.db_path = config.get('MacPaths', 'storage_path')
            self.sqlite_path = config.get('MacPaths', 'sqlite_path')
            
        elif sys.platform == "linux":  # Linux 系统 / Linux system
            # 检查 Linux 路径配置节是否存在 / Check if LinuxPaths config section exists
            if not config.has_section('LinuxPaths'):
                raise ConfigError("LinuxPaths section not found in config")
                
            # 获取 Linux 系统的文件路径 / Get file paths for Linux system
            self.db_path = config.get('LinuxPaths', 'storage_path')
            self.sqlite_path = config.get('LinuxPaths', 'sqlite_path')
            
        else:
            # 不支持的操作系统 / Unsupported operating system
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")
    
    def find_backups(self):
        """查找可用的备份文件 / Find available backup files
        
        在 storage.json 文件所在目录中查找所有备份文件
        备份文件命名格式为：{原文件名}.bak.{时间戳}
        
        Search for all backup files in the directory where storage.json is located
        Backup file naming format: {original_filename}.bak.{timestamp}
        
        Returns:
            list: 按创建时间排序的备份文件路径列表（最新的在前）
                  List of backup file paths sorted by creation time (newest first)
        """
        # 获取数据库文件的目录和文件名 / Get directory and filename of database file
        db_dir = os.path.dirname(self.db_path)
        db_name = os.path.basename(self.db_path)
        
        # 查找格式为 {db_name}.bak.{timestamp} 的文件 / Find files with format {db_name}.bak.{timestamp}
        backup_pattern = f"{db_name}.bak.*"
        backups = glob.glob(os.path.join(db_dir, backup_pattern))
        
        # 按创建时间排序（最新的在前）/ Sort by creation time (newest first)
        backups.sort(key=os.path.getctime, reverse=True)
        
        return backups
    
    def list_backups(self):
        """列出所有可用备份 / List all available backups
        
        显示所有找到的备份文件，包括文件名、创建时间和文件大小
        如果没有找到备份文件，则显示警告信息
        
        Display all found backup files, including filename, creation time and file size
        If no backup files are found, display warning message
        
        Returns:
            list or None: 备份文件列表，如果没有备份则返回 None
                         List of backup files, or None if no backups found
        """
        # 查找所有备份文件 / Find all backup files
        backups = self.find_backups()
        
        # 如果没有找到备份文件 / If no backup files found
        if not backups:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('restore.no_backups_found')}{Style.RESET_ALL}")
            return None
        
        # 显示可用备份列表标题 / Display available backups list title
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('restore.available_backups')}:{Style.RESET_ALL}")
        
        # 遍历并显示每个备份文件的详细信息 / Iterate and display detailed info for each backup file
        for i, backup in enumerate(backups, 1):
            # 获取备份文件信息 / Get backup file information
            timestamp_str = backup.split('.')[-1]
            try:
                # 尝试解析时间戳（如果格式为 YYYYmmdd_HHMMSS）/ Try to parse timestamp (if format is YYYYmmdd_HHMMSS)
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                # 时间戳格式无法解析 / Timestamp format cannot be parsed
                date_str = "未知日期"
            
            # 获取文件大小 / Get file size
            size = os.path.getsize(backup)
            size_str = f"{size / 1024:.1f} KB"
            
            # 显示备份文件信息 / Display backup file information
            print(f"{i}. {Fore.GREEN}{os.path.basename(backup)}{Style.RESET_ALL} ({date_str}, {size_str})")
        
        return backups
    
    def select_backup(self):
        """让用户选择要恢复的备份 / Let user select backup to restore
        
        显示可用备份列表并让用户选择要恢复的备份文件
        用户可以输入数字选择备份，或输入 0 取消操作
        
        Display available backup list and let user select backup file to restore
        User can input number to select backup, or input 0 to cancel operation
        
        Returns:
            str or None: 选中的备份文件路径，如果取消则返回 None
                        Path of selected backup file, or None if cancelled
        """
        # 获取并显示备份列表 / Get and display backup list
        backups = self.list_backups()
        
        # 如果没有备份文件则直接返回 / Return directly if no backup files
        if not backups:
            return None
        
        # 循环等待用户输入有效选择 / Loop waiting for valid user input
        while True:
            try:
                # 提示用户选择备份 / Prompt user to select backup
                choice = input(f"{EMOJI['INFO']} {self.translator.get('restore.select_backup')} (1-{len(backups)}, 0 {self.translator.get('restore.to_cancel')}): ")
                
                # 用户选择取消操作 / User chooses to cancel operation
                if choice.strip() == '0':
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('restore.operation_cancelled')}{Style.RESET_ALL}")
                    return None
                
                # 验证用户输入的索引 / Validate user input index
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    return backups[index]
                else:
                    # 选择超出范围 / Selection out of range
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.invalid_selection')}{Style.RESET_ALL}")
            except ValueError:
                # 输入不是有效数字 / Input is not a valid number
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.please_enter_number')}{Style.RESET_ALL}")
    
    def extract_ids_from_backup(self, backup_path):
        """从备份文件中提取机器ID / Extract machine IDs from backup file
        
        读取备份的 JSON 文件并提取所有需要恢复的机器标识符
        包括设备ID、机器ID、macOS机器ID、SQM ID等
        
        Read backup JSON file and extract all machine identifiers that need to be restored
        Including device ID, machine ID, macOS machine ID, SQM ID, etc.
        
        Args:
            backup_path (str): 备份文件的完整路径 / Full path to backup file
            
        Returns:
            dict or None: 包含所有机器ID的字典，失败时返回 None
                         Dictionary containing all machine IDs, or None if failed
        """
        try:
            # 读取备份文件 / Read backup file
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            # 提取需要恢复的ID / Extract IDs that need to be restored
            ids = {
                "telemetry.devDeviceId": backup_data.get("telemetry.devDeviceId", ""),
                "telemetry.macMachineId": backup_data.get("telemetry.macMachineId", ""),
                "telemetry.machineId": backup_data.get("telemetry.machineId", ""),
                "telemetry.sqmId": backup_data.get("telemetry.sqmId", ""),
                "storage.serviceMachineId": backup_data.get("storage.serviceMachineId", 
                                                          backup_data.get("telemetry.devDeviceId", ""))
            }
            
            # 检查并警告缺失的ID / Check and warn about missing IDs
            for key, value in ids.items():
                if not value:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('restore.missing_id', id=key)}{Style.RESET_ALL}")
            
            return ids
        except Exception as e:
            # 读取备份文件失败 / Failed to read backup file
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.read_backup_failed', error=str(e))}{Style.RESET_ALL}")
            return None
    
    def update_current_file(self, ids):
        """更新当前的storage.json文件 / Update current storage.json file
        
        使用从备份中提取的机器ID更新当前的storage.json配置文件
        在更新前会先创建当前文件的备份以防止数据丢失
        
        Update current storage.json config file with machine IDs extracted from backup
        Create backup of current file before updating to prevent data loss
        
        Args:
            ids (dict): 包含要更新的机器ID的字典 / Dictionary containing machine IDs to update
            
        Returns:
            bool: 更新成功返回 True，失败返回 False / True if update successful, False if failed
        """
        try:
            # 检查当前文件是否存在 / Check if current file exists
            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.current_file_not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False
            
            # 读取当前文件 / Read current file
            with open(self.db_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)
            
            # 创建当前文件的备份 / Create backup of current file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.restore_bak.{timestamp}"
            shutil.copy2(self.db_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('restore.current_backup_created')}: {backup_path}{Style.RESET_ALL}")
            
            # 更新ID / Update IDs
            current_data.update(ids)
            
            # 保存更新后的文件 / Save updated file
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=4)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.storage_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            # 更新文件失败 / Failed to update file
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_sqlite_db(self, ids):
        """更新SQLite数据库中的ID / Update IDs in SQLite database
        
        将恢复的机器ID更新到Cursor的SQLite数据库中
        如果ItemTable表不存在会自动创建，使用REPLACE语句确保数据正确更新
        
        Update restored machine IDs to Cursor's SQLite database
        Automatically create ItemTable if it doesn't exist, use REPLACE to ensure data is updated correctly
        
        Args:
            ids (dict): 包含要更新的机器ID的字典 / Dictionary containing machine IDs to update
            
        Returns:
            bool: 更新成功返回 True，失败返回 False / True if update successful, False if failed
        """
        try:
            # 检查SQLite数据库文件是否存在 / Check if SQLite database file exists
            if not os.path.exists(self.sqlite_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.sqlite_not_found')}: {self.sqlite_path}{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('restore.updating_sqlite')}...{Style.RESET_ALL}")
            
            # 连接SQLite数据库 / Connect to SQLite database
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # 创建ItemTable表（如果不存在）/ Create ItemTable (if not exists)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 逐个更新每个键值对 / Update each key-value pair
            for key, value in ids.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('restore.updating_pair')}: {key}{Style.RESET_ALL}")
            
            # 提交事务并关闭连接 / Commit transaction and close connection
            conn.commit()
            conn.close()
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.sqlite_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            # SQLite数据库更新失败 / SQLite database update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.sqlite_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_machine_id_file(self, dev_device_id):
        """更新machineId文件 / Update machineId file
        
        将恢复的设备ID写入到Cursor的machineId文件中
        会自动创建目录结构，并在更新前备份现有文件
        
        Write restored device ID to Cursor's machineId file
        Automatically create directory structure and backup existing file before update
        
        Args:
            dev_device_id (str): 要写入的设备ID / Device ID to write
            
        Returns:
            bool: 更新成功返回 True，失败返回 False / True if update successful, False if failed
        """
        try:
            # 获取machineId文件路径 / Get machineId file path
            machine_id_path = get_cursor_machine_id_path(self.translator)
            
            # 创建目录（如果不存在）/ Create directory if not exists
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            
            # 备份当前文件（如果存在）/ Backup current file if exists
            if os.path.exists(machine_id_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{machine_id_path}.restore_bak.{timestamp}"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('restore.machine_id_backup_created')}: {backup_path}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('restore.backup_creation_failed', error=str(e))}{Style.RESET_ALL}")
            
            # 写入新的设备ID / Write new device ID
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(dev_device_id)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.machine_id_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            # machineId文件更新失败 / machineId file update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.machine_id_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_system_ids(self, ids):
        """更新系统级ID（特定于操作系统）/ Update system-level IDs (OS-specific)
        
        根据当前操作系统调用相应的系统ID更新方法
        Windows系统更新注册表中的机器GUID和ID
        macOS系统更新平台UUID
        
        Call appropriate system ID update method based on current OS
        Windows: Update machine GUID and ID in registry
        macOS: Update platform UUID
        
        Args:
            ids (dict): 包含要更新的系统ID的字典 / Dictionary containing system IDs to update
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('restore.updating_system_ids')}...{Style.RESET_ALL}")
            
            # 根据操作系统调用相应的更新方法 / Call appropriate update method based on OS
            if sys.platform.startswith("win"):
                self._update_windows_system_ids(ids)
            elif sys.platform == "darwin":
                self._update_macos_system_ids(ids)
            
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def _update_windows_system_ids(self, ids):
        """更新Windows系统ID / Update Windows system IDs
        
        更新Windows注册表中的机器GUID和SQMClient机器ID
        需要管理员权限才能修改注册表项
        
        Update machine GUID and SQMClient machine ID in Windows registry
        Requires administrator privileges to modify registry keys
        
        Args:
            ids (dict): 包含要更新的系统ID的字典 / Dictionary containing system IDs to update
        """
        try:
            import winreg
            
            # 更新MachineGuid / Update MachineGuid
            guid = ids.get("telemetry.devDeviceId", "")
            if guid:
                try:
                    # 打开注册表项 / Open registry key
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Microsoft\\Cryptography",
                        0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                    )
                    # 设置MachineGuid值 / Set MachineGuid value
                    winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, guid)
                    winreg.CloseKey(key)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.windows_machine_guid_updated')}{Style.RESET_ALL}")
                except PermissionError:
                    # 权限不足 / Insufficient permissions
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.permission_denied')}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            
            # 更新SQMClient MachineId / Update SQMClient MachineId
            sqm_id = ids.get("telemetry.sqmId", "")
            if sqm_id:
                try:
                    # 打开SQMClient注册表项 / Open SQMClient registry key
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\SQMClient",
                        0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                    )
                    # 设置MachineId值 / Set MachineId value
                    winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, sqm_id)
                    winreg.CloseKey(key)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.windows_machine_id_updated')}{Style.RESET_ALL}")
                except FileNotFoundError:
                    # SQMClient注册表项不存在 / SQMClient registry key not found
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('restore.sqm_client_key_not_found')}{Style.RESET_ALL}")
                except PermissionError:
                    # 权限不足 / Insufficient permissions
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.permission_denied')}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.update_windows_machine_id_failed', error=str(e))}{Style.RESET_ALL}")
        except Exception as e:
            # Windows系统ID更新失败 / Windows system IDs update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.update_windows_system_ids_failed', error=str(e))}{Style.RESET_ALL}")
    
    def _update_macos_system_ids(self, ids):
        """更新macOS系统ID / Update macOS system IDs
        
        更新macOS系统的平台UUID
        使用plutil命令修改系统配置文件，需要sudo权限
        
        Update macOS system platform UUID
        Use plutil command to modify system configuration file, requires sudo privileges
        
        Args:
            ids (dict): 包含要更新的系统ID的字典 / Dictionary containing system IDs to update
        """
        try:
            # macOS平台UUID配置文件路径 / macOS platform UUID configuration file path
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                mac_id = ids.get("telemetry.macMachineId", "")
                if mac_id:
                    # 使用plutil命令更新UUID / Use plutil command to update UUID
                    cmd = f'sudo plutil -replace "UUID" -string "{mac_id}" "{uuid_file}"'
                    result = os.system(cmd)
                    if result == 0:
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                    else:
                        # plutil命令执行失败 / plutil command execution failed
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            # macOS系统ID更新失败 / macOS system IDs update failed
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.update_macos_system_ids_failed', error=str(e))}{Style.RESET_ALL}")
    
    def restore_machine_ids(self):
        """恢复之前备份的机器ID / Restore previously backed up machine IDs
        
        完整的机器ID恢复流程，包括：
        1. 选择要恢复的备份文件
        2. 从备份中提取机器ID
        3. 显示要恢复的ID并确认
        4. 更新storage.json文件
        5. 更新SQLite数据库
        6. 更新machineId文件
        7. 更新系统级ID
        
        Complete machine ID restoration process including:
        1. Select backup file to restore
        2. Extract machine IDs from backup
        3. Display IDs to restore and confirm
        4. Update storage.json file
        5. Update SQLite database
        6. Update machineId file
        7. Update system-level IDs
        
        Returns:
            bool: 恢复成功返回 True，失败返回 False / True if restore successful, False if failed
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('restore.starting')}...{Style.RESET_ALL}")
            
            # 选择要恢复的备份 / Select backup to restore
            backup_path = self.select_backup()
            if not backup_path:
                return False
            
            # 从备份中提取ID / Extract IDs from backup
            ids = self.extract_ids_from_backup(backup_path)
            if not ids:
                return False
            
            # 显示将要恢复的ID / Display IDs to be restored
            print(f"\n{Fore.CYAN}{self.translator.get('restore.ids_to_restore')}:{Style.RESET_ALL}")
            for key, value in ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")
            
            # 确认恢复操作 / Confirm restore operation
            confirm = input(f"\n{EMOJI['WARNING']} {self.translator.get('restore.confirm')} (y/n): ")
            if confirm.lower() != 'y':
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('restore.operation_cancelled')}{Style.RESET_ALL}")
                return False
            
            # 更新当前storage.json文件 / Update current storage.json file
            if not self.update_current_file(ids):
                return False
            
            # 更新SQLite数据库 / Update SQLite database
            self.update_sqlite_db(ids)
            
            # 更新machineId文件 / Update machineId file
            self.update_machine_id_file(ids.get("telemetry.devDeviceId", ""))
            
            # 更新系统级ID / Update system-level IDs
            self.update_system_ids(ids)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('restore.success')}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            # 恢复过程中发生错误 / Error occurred during restore process
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('restore.process_error', error=str(e))}{Style.RESET_ALL}")
            return False

def run(translator=None):
    """恢复机器ID的主函数 / Main function for restoring machine IDs
    
    程序的主入口点，负责：
    1. 检查配置文件
    2. 显示程序标题
    3. 创建恢复器实例并执行恢复
    4. 等待用户确认退出
    
    Main entry point of the program, responsible for:
    1. Check configuration file
    2. Display program title
    3. Create restorer instance and execute restoration
    4. Wait for user confirmation to exit
    
    Args:
        translator: 翻译器实例，用于多语言支持 / Translator instance for multi-language support
        
    Returns:
        bool: 执行成功返回 True，失败返回 False / True if execution successful, False if failed
    """
    # 检查配置文件 / Check configuration file
    config = get_config(translator)
    if not config:
        return False
    
    # 显示程序标题 / Display program title
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('restore.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # 创建恢复器实例并执行恢复 / Create restorer instance and execute restoration
    restorer = MachineIDRestorer(translator)
    restorer.restore_machine_ids()
    
    # 等待用户确认退出 / Wait for user confirmation to exit
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('restore.press_enter')}...")

# 主程序入口 / Main program entry point
if __name__ == "__main__":
    # 导入主程序的翻译器实例 / Import translator instance from main program
    from main import translator as main_translator
    # 运行恢复程序 / Run restore program
    run(main_translator)