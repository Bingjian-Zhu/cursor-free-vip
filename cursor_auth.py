"""Cursor 认证管理模块 / Cursor Authentication Management Module

该模块提供了 Cursor AI 认证信息的数据库管理功能，包括：
- 连接和操作 Cursor 的 SQLite 数据库
- 更新认证令牌、邮箱和认证类型
- 跨平台支持（Windows、macOS、Linux）
- 事务安全的数据库操作

主要功能 / Main Features:
1. 自动检测操作系统并获取正确的数据库路径
2. 安全的数据库连接和权限检查
3. 事务性的认证信息更新
4. 完善的错误处理和日志记录

使用方法 / Usage:
```python
from cursor_auth import CursorAuth

# 创建认证管理实例
cursor_auth = CursorAuth(translator=None)

# 更新认证信息
result = cursor_auth.update_auth(
    email="user@example.com",
    access_token="your_access_token",
    refresh_token="your_refresh_token",
    auth_type="Google"
)
```

依赖模块 / Dependencies:
- sqlite3: SQLite 数据库操作
- colorama: 终端颜色输出
- config: 配置文件管理
"""

import sqlite3
import os
import sys
from colorama import Fore, Style, init
from config import get_config

# 初始化 colorama 用于终端颜色输出 / Initialize colorama for colored terminal output
init()

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

class CursorAuth:
    """Cursor 认证管理类 / Cursor Authentication Management Class
    
    该类负责管理 Cursor AI 的认证信息，包括连接数据库、更新认证令牌等功能。
    支持跨平台操作（Windows、macOS、Linux）。
    
    属性 / Attributes:
        translator: 翻译器实例，用于多语言支持
        db_path: SQLite 数据库文件路径
        conn: 数据库连接对象
    """
    
    def __init__(self, translator=None):
        """初始化 CursorAuth 实例 / Initialize CursorAuth instance
        
        参数 / Args:
            translator: 翻译器实例，用于多语言消息显示
        
        功能 / Functions:
        1. 加载配置文件
        2. 根据操作系统获取数据库路径
        3. 验证数据库文件和权限
        4. 建立数据库连接
        """
        self.translator = translator
        
        # 获取配置信息 / Get configuration
        config = get_config(translator)
        if not config:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.config_error') if self.translator else 'Failed to load configuration'}{Style.RESET_ALL}")
            sys.exit(1)
            
        # 根据操作系统获取数据库路径 / Get path based on operating system
        try:
            if sys.platform == "win32":  # Windows 系统
                if not config.has_section('WindowsPaths'):
                    raise ValueError("Windows paths not configured")
                self.db_path = config.get('WindowsPaths', 'sqlite_path')
                
            elif sys.platform == 'linux':  # Linux 系统
                if not config.has_section('LinuxPaths'):
                    raise ValueError("Linux paths not configured")
                self.db_path = config.get('LinuxPaths', 'sqlite_path')
                
            elif sys.platform == 'darwin':  # macOS 系统
                if not config.has_section('MacPaths'):
                    raise ValueError("macOS paths not configured")
                self.db_path = config.get('MacPaths', 'sqlite_path')
                
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.unsupported_platform') if self.translator else 'Unsupported platform'}{Style.RESET_ALL}")
                sys.exit(1)
                
            # 验证数据库目录是否存在 / Verify if the database directory exists
            if not os.path.exists(os.path.dirname(self.db_path)):
                raise FileNotFoundError(f"Database directory not found: {os.path.dirname(self.db_path)}")
                
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.path_error', error=str(e)) if self.translator else f'Error getting database path: {str(e)}'}{Style.RESET_ALL}")
            sys.exit(1)

        # 检查数据库文件是否存在 / Check if the database file exists
        if not os.path.exists(self.db_path):
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_not_found', path=self.db_path) if self.translator else f'Database not found: {self.db_path}'}{Style.RESET_ALL}")
            return

        # 检查文件权限 / Check file permissions
        if not os.access(self.db_path, os.R_OK | os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_permission_error') if self.translator else 'Database permission error'}{Style.RESET_ALL}")
            return

        # 尝试连接数据库 / Try to connect to the database
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('auth.connected_to_database') if self.translator else 'Connected to database'}{Style.RESET_ALL}")
        except sqlite3.Error as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_connection_error', error=str(e)) if self.translator else f'Database connection error: {str(e)}'}{Style.RESET_ALL}")
            return

    def update_auth(self, email=None, access_token=None, refresh_token=None, auth_type="Auth_0"):
        """更新 Cursor 认证信息 / Update Cursor authentication information
        
        参数 / Args:
            email (str, optional): 用户邮箱地址
            access_token (str, optional): 访问令牌
            refresh_token (str, optional): 刷新令牌
            auth_type (str): 认证类型，默认为 "Auth_0"
        
        返回值 / Returns:
            bool: 更新成功返回 True，失败返回 False
        
        功能 / Functions:
        1. 确保数据库目录和文件存在
        2. 创建或连接到 SQLite 数据库
        3. 使用事务安全地更新认证信息
        4. 处理各种异常情况
        """
        conn = None
        try:
            # 确保目录存在并设置正确的权限 / Ensure the directory exists and set the correct permissions
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
            
            # 如果数据库文件不存在，创建新的数据库 / If the database file does not exist, create a new one
            if not os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # 创建 ItemTable 表用于存储键值对 / Create ItemTable for storing key-value pairs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ItemTable (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                conn.commit()
                # 在非 Windows 系统上设置文件权限 / Set file permissions on non-Windows systems
                if sys.platform != "win32":
                    os.chmod(self.db_path, 0o644)
                conn.close()

            # 重新连接到数据库 / Reconnect to the database
            conn = sqlite3.connect(self.db_path)
            print(f"{EMOJI['INFO']} {Fore.GREEN} {self.translator.get('auth.connected_to_database') if self.translator else 'Connected to database'}{Style.RESET_ALL}")
            cursor = conn.cursor()
            
            # 添加超时和其他优化设置 / Add timeout and other optimization settings
            conn.execute("PRAGMA busy_timeout = 5000")      # 设置忙碌超时为5秒
            conn.execute("PRAGMA journal_mode = WAL")        # 启用 WAL 模式提高并发性能
            conn.execute("PRAGMA synchronous = NORMAL")      # 设置同步模式为正常
            
            # 设置要更新的键值对 / Set the key-value pairs to update
            updates = []

            # 始终更新认证类型 / Always update authentication type
            updates.append(("cursorAuth/cachedSignUpType", auth_type))

            # 根据提供的参数添加更新项 / Add update items based on provided parameters
            if email is not None:
                updates.append(("cursorAuth/cachedEmail", email))
            if access_token is not None:
                updates.append(("cursorAuth/accessToken", access_token))
            if refresh_token is not None:
                updates.append(("cursorAuth/refreshToken", refresh_token))
                

            # 使用事务确保数据完整性 / Use transactions to ensure data integrity
            cursor.execute("BEGIN TRANSACTION")
            try:
                for key, value in updates:
                    # 检查键是否存在 / Check if the key exists
                    cursor.execute("SELECT COUNT(*) FROM ItemTable WHERE key = ?", (key,))
                    if cursor.fetchone()[0] == 0:
                        # 键不存在，插入新记录 / Key doesn't exist, insert new record
                        cursor.execute("""
                            INSERT INTO ItemTable (key, value) 
                            VALUES (?, ?)
                        """, (key, value))
                    else:
                        # 键存在，更新现有记录 / Key exists, update existing record
                        cursor.execute("""
                            UPDATE ItemTable SET value = ?
                            WHERE key = ?
                        """, (value, key))
                    print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('auth.updating_pair') if self.translator else 'Updating key-value pair:'} {key.split('/')[-1]}...{Style.RESET_ALL}")
                
                # 提交事务 / Commit transaction
                cursor.execute("COMMIT")
                print(f"{EMOJI['SUCCESS']} {Fore.GREEN}{self.translator.get('auth.database_updated_successfully') if self.translator else 'Database updated successfully'}{Style.RESET_ALL}")
                return True
                
            except Exception as e:
                # 发生错误时回滚事务 / Rollback transaction on error
                cursor.execute("ROLLBACK")
                raise e

        except sqlite3.Error as e:
            # 处理 SQLite 数据库错误 / Handle SQLite database errors
            print(f"\n{EMOJI['ERROR']} {Fore.RED} {self.translator.get('auth.database_error', error=str(e)) if self.translator else f'Database error: {str(e)}'}{Style.RESET_ALL}")
            return False
        except Exception as e:
            # 处理其他异常 / Handle other exceptions
            print(f"\n{EMOJI['ERROR']} {Fore.RED} {self.translator.get('auth.an_error_occurred', error=str(e)) if self.translator else f'An error occurred: {str(e)}'}{Style.RESET_ALL}")
            return False
        finally:
            # 确保数据库连接被关闭 / Ensure database connection is closed
            if conn:
                conn.close()
                print(f"{EMOJI['DB']} {Fore.CYAN} {self.translator.get('auth.database_connection_closed') if self.translator else 'Database connection closed'}{Style.RESET_ALL}")