# main.py
# Cursor Free VIP 主程序入口文件
# 功能：提供一个交互式菜单界面，允许用户选择运行不同的 Cursor 相关功能脚本
# 作者：yeongpin
# 项目地址：https://github.com/yeongpin/cursor-free-vip

# 导入标准库模块
import os          # 操作系统接口模块，用于文件和目录操作
import sys         # 系统相关的参数和函数
import json        # JSON 数据处理模块
import locale      # 本地化支持模块
import platform    # 平台识别模块
import requests    # HTTP 请求库
import subprocess  # 子进程管理模块
import shutil      # 高级文件操作模块
import re          # 正则表达式模块

# 导入项目自定义模块
from logo import print_logo, version                    # Logo 显示和版本信息
from colorama import Fore, Style, init                  # 终端颜色输出库
from config import get_config, force_update_config      # 配置文件管理
from utils import get_user_documents_path               # 工具函数  

# 阿拉伯语文本支持模块（可选导入）
# 用于正确显示阿拉伯语文本的双向文本算法
try:
    import arabic_reshaper      # 阿拉伯语文本重塑库
    from bidi.algorithm import get_display  # 双向文本显示算法
except ImportError:
    # 如果未安装阿拉伯语支持库，设置为 None
    arabic_reshaper = None
    get_display = None

# Windows 系统特定模块导入
# 仅在 Windows 系统上导入 Windows API 相关模块
if platform.system() == 'Windows':
    import ctypes                # Windows API 调用库
    from ctypes import windll    # Windows 动态链接库接口

# 初始化 colorama 库，启用跨平台终端颜色支持
init()

# 表情符号常量定义
# 用于在终端界面中提供视觉提示和美化显示效果
EMOJI = {
    "FILE": "📄",        # 文件相关操作
    "BACKUP": "💾",      # 备份相关操作
    "SUCCESS": "✅",     # 成功状态提示
    "ERROR": "❌",       # 错误状态提示
    "INFO": "ℹ️",        # 信息提示
    "RESET": "🔄",       # 重置相关操作
    "MENU": "📋",        # 菜单显示
    "ARROW": "➜",        # 箭头指示符
    "LANG": "🌐",        # 语言相关设置
    "UPDATE": "🔄",      # 更新相关操作
    "ADMIN": "🔐",       # 管理员权限提示
    "AIRDROP": "💰",     # 空投相关（未使用）
    "ROCKET": "🚀",      # 火箭图标（未使用）
    "STAR": "⭐",        # 星星图标
    "SUN": "🌟",         # 太阳图标
    "CONTRIBUTE": "🤝",  # 贡献者相关
    "SETTINGS": "⚙️"     # 设置相关操作
}

# ==================== 工具函数定义 ====================

def is_frozen():
    """
    检查脚本是否作为打包的可执行文件运行
    
    Returns:
        bool: 如果是打包的可执行文件返回 True，否则返回 False
    
    说明:
        使用 PyInstaller 等工具打包后，sys.frozen 属性会被设置为 True
    """
    return getattr(sys, 'frozen', False)

def is_admin():
    """
    检查脚本是否以管理员权限运行（仅限 Windows 系统）
    
    Returns:
        bool: Windows 系统下有管理员权限返回 True，非 Windows 系统始终返回 True
    
    说明:
        - Windows: 通过 Windows API 检查当前用户是否具有管理员权限
        - 非 Windows: 为避免改变行为，始终返回 True
    """
    if platform.system() == 'Windows':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    # 非 Windows 系统始终返回 True，避免改变程序行为
    return True

def run_as_admin():
    """
    以管理员权限重新启动当前脚本（仅限 Windows 系统）
    
    Returns:
        bool: 成功请求管理员权限返回 True，失败或非 Windows 系统返回 False
    
    说明:
        - 仅在 Windows 系统上有效
        - 使用 Windows ShellExecute API 的 "runas" 动词请求权限提升
        - 成功后当前进程应该退出，新的管理员进程将启动
    """
    if platform.system() != 'Windows':
        return False
        
    try:
        args = [sys.executable] + sys.argv
        
        # 通过 ShellExecute 请求权限提升
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} 正在请求管理员权限...{Style.RESET_ALL}")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", args[0], " ".join('"' + arg + '"' for arg in args[1:]), None, 1)
        return True
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} 请求管理员权限失败: {e}{Style.RESET_ALL}")
        return False

# ==================== 国际化翻译类 ====================

class Translator:
    """
    多语言翻译管理类
    
    功能:
        - 自动检测系统语言
        - 加载多语言翻译文件
        - 提供翻译文本获取接口
        - 支持阿拉伯语等特殊语言的文本处理
        - 管理语言配置的持久化存储
    
    支持的语言:
        en(英语), zh_cn(简体中文), zh_tw(繁体中文), vi(越南语), 
        ru(俄语), tr(土耳其语), bg(保加利亚语), ar(阿拉伯语),
        nl(荷兰语), de(德语), fr(法语), pt(葡萄牙语), it(意大利语),
        ja(日语), es(西班牙语)
    """
    
    def __init__(self):
        """
        初始化翻译器
        
        初始化流程:
            1. 初始化翻译字典
            2. 加载配置文件
            3. 设置语言缓存目录
            4. 确定当前语言（配置文件 > 系统检测）
            5. 加载所有可用的翻译文件
        """
        self.translations = {}  # 存储所有语言的翻译数据
        self.config = get_config()  # 获取程序配置
        
        # 创建语言缓存目录（如果不存在）
        if self.config and self.config.has_section('Language'):
            self.language_cache_dir = self.config.get('Language', 'language_cache_dir')
            os.makedirs(self.language_cache_dir, exist_ok=True)
        else:
            self.language_cache_dir = None
        
        # 从配置文件设置备用语言，默认为英语
        self.fallback_language = 'en'
        if self.config and self.config.has_section('Language') and self.config.has_option('Language', 'fallback_language'):
            self.fallback_language = self.config.get('Language', 'fallback_language')
        
        # 确定当前使用的语言
        # 优先级：配置文件中保存的语言 > 系统语言检测
        if self.config and self.config.has_section('Language') and self.config.has_option('Language', 'current_language'):
            saved_language = self.config.get('Language', 'current_language')
            if saved_language and saved_language.strip():
                self.current_language = saved_language
            else:
                # 配置文件中没有有效语言，检测系统语言并保存
                self.current_language = self.detect_system_language()
                # 将检测到的语言保存到配置文件
                if self.config.has_section('Language'):
                    self.config.set('Language', 'current_language', self.current_language)
                    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
                    config_file = os.path.join(config_dir, "config.ini")
                    with open(config_file, 'w', encoding='utf-8') as f:
                        self.config.write(f)
        else:
            # 配置文件中没有语言设置，直接检测系统语言
            self.current_language = self.detect_system_language()
        
        # 加载所有可用的翻译文件
        self.load_translations()
    
    def detect_system_language(self):
        """
        检测系统语言并返回对应的语言代码
        
        Returns:
            str: 语言代码（如 'en', 'zh_cn', 'zh_tw' 等）
        
        说明:
            根据操作系统类型调用不同的语言检测方法
            - Windows: 通过键盘布局检测
            - Unix/Linux/macOS: 通过系统区域设置检测
        """
        try:
            system = platform.system()
            
            if system == 'Windows':
                return self._detect_windows_language()
            else:
                return self._detect_unix_language()
                
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} 系统语言检测失败: {e}{Style.RESET_ALL}")
            return 'en'
    
    def _detect_windows_language(self):
        """
        检测 Windows 系统的语言设置
        
        Returns:
            str: 语言代码
        
        说明:
            通过获取当前窗口的键盘布局来判断系统语言
            使用 Windows API 获取键盘布局 ID，然后映射到对应的语言代码
        """
        try:
            # 确保在 Windows 系统上运行
            if platform.system() != 'Windows':
                return 'en'
                
            # 获取键盘布局信息
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()  # 获取前台窗口句柄
            threadid = user32.GetWindowThreadProcessId(hwnd, 0)  # 获取线程 ID
            layout_id = user32.GetKeyboardLayout(threadid) & 0xFFFF  # 获取键盘布局 ID
            
            # 将语言 ID 映射到语言代码（兼容 Python 3.9 的 if-elif 结构）
            if layout_id == 0x0409:
                return 'en'      # 英语
            elif layout_id == 0x0404:
                return 'zh_tw'   # 繁体中文
            elif layout_id == 0x0804:
                return 'zh_cn'   # 简体中文
            elif layout_id == 0x0422:
                return 'vi'      # 越南语
            elif layout_id == 0x0419:
                return 'ru'      # 俄语
            elif layout_id == 0x0415:
                return 'tr'      # 土耳其语
            elif layout_id == 0x0402:
                return 'bg'      # 保加利亚语
            elif layout_id == 0x0401:
                return 'ar'      # 阿拉伯语
            else:
                return 'en'       # 默认返回英语
        except:
            # 如果 Windows 检测失败，回退到 Unix 方法
            return self._detect_unix_language()
    
    def _detect_unix_language(self):
        """
        检测 Unix 类系统（Linux、macOS）的语言设置
        
        Returns:
            str: 语言代码
        
        说明:
            通过系统区域设置（locale）来检测语言
            如果区域设置检测失败，会尝试从 LANG 环境变量获取语言信息
        """
        try:
            # 获取系统区域设置
            locale.setlocale(locale.LC_ALL, '')
            system_locale = locale.getlocale()[0]
            if not system_locale:
                return 'en'
            
            system_locale = system_locale.lower()
            
            # 将区域设置映射到语言代码（兼容 Python 3.9 的 if-elif 结构）
            if system_locale.startswith('zh_tw') or system_locale.startswith('zh_hk'):
                return 'zh_tw'  # 繁体中文
            elif system_locale.startswith('zh_cn'):
                return 'zh_cn'  # 简体中文
            elif system_locale.startswith('en'):
                return 'en'     # 英语
            elif system_locale.startswith('vi'):
                return 'vi'     # 越南语
            elif system_locale.startswith('nl'):
                return 'nl'     # 荷兰语
            elif system_locale.startswith('de'):
                return 'de'     # 德语
            elif system_locale.startswith('fr'):
                return 'fr'     # 法语
            elif system_locale.startswith('pt'):
                return 'pt'     # 葡萄牙语
            elif system_locale.startswith('ru'):
                return 'ru'     # 俄语
            elif system_locale.startswith('tr'):
                return 'tr'     # 土耳其语
            elif system_locale.startswith('bg'):
                return 'bg'     # 保加利亚语
            elif system_locale.startswith('ar'):
                return 'ar'     # 阿拉伯语
            else:
                # 如果区域设置无法识别，尝试从 LANG 环境变量获取语言信息
                env_lang = os.getenv('LANG', '').lower()
                if 'tw' in env_lang or 'hk' in env_lang:
                    return 'zh_tw'  # 繁体中文
                elif 'cn' in env_lang:
                    return 'zh_cn'  # 简体中文
                elif 'vi' in env_lang:
                    return 'vi'     # 越南语
                elif 'nl' in env_lang:
                    return 'nl'     # 荷兰语
                elif 'de' in env_lang:
                    return 'de'     # 德语
                elif 'fr' in env_lang:
                    return 'fr'     # 法语
                elif 'pt' in env_lang:
                    return 'pt'     # 葡萄牙语
                elif 'ru' in env_lang:
                    return 'ru'     # 俄语
                elif 'tr' in env_lang:
                    return 'tr'     # 土耳其语
                elif 'bg' in env_lang:
                    return 'bg'     # 保加利亚语
                elif 'ar' in env_lang:
                    return 'ar'     # 阿拉伯语
                else:
                    return 'en'     # 默认返回英语
        except:
            return 'en'  # 异常情况下返回英语
    
    def download_language_file(self, lang_code):
        """
        下载语言文件（兼容性方法，现已废弃）
        
        Args:
            lang_code (str): 语言代码
        
        Returns:
            bool: 始终返回 False，因为语言文件现已集成到程序包中
        
        说明:
            此方法保留用于向后兼容，现在语言文件已集成到程序包中，无需下载
        """
        print(f"{Fore.YELLOW}{EMOJI['INFO']} 语言文件已集成到程序包中，无需下载。{Style.RESET_ALL}")
        return False
            
    def load_translations(self):
        """
        从集成的程序包中加载所有可用的翻译文件
        
        说明:
            按优先级顺序搜索翻译文件：
            1. PyInstaller 打包后的临时目录（_MEIPASS）
            2. 脚本所在目录的 locales 子目录
            3. 当前工作目录的 locales 子目录
        """
        try:
            # 记录成功加载的语言
            loaded_languages = set()
            
            # 定义可能的翻译文件路径
            locales_paths = []
            
            # 首先检查 PyInstaller 打包后的临时目录
            if hasattr(sys, '_MEIPASS'):
                locales_paths.append(os.path.join(sys._MEIPASS, 'locales'))
            
            # 检查脚本目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            locales_paths.append(os.path.join(script_dir, 'locales'))
            
            # 检查当前工作目录
            locales_paths.append(os.path.join(os.getcwd(), 'locales'))
            
            # 遍历所有可能的路径，加载翻译文件
            for locales_dir in locales_paths:
                if os.path.exists(locales_dir) and os.path.isdir(locales_dir):
                    for file in os.listdir(locales_dir):
                        if file.endswith('.json'):
                            lang_code = file[:-5]  # 移除 .json 扩展名获取语言代码
                            try:
                                with open(os.path.join(locales_dir, file), 'r', encoding='utf-8') as f:
                                    self.translations[lang_code] = json.load(f)
                                    loaded_languages.add(lang_code)
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                print(f"{Fore.RED}{EMOJI['ERROR']} 加载翻译文件 {file} 失败: {e}{Style.RESET_ALL}")
                                continue

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} 翻译文件加载失败: {e}{Style.RESET_ALL}")
            # 创建最基本的英语翻译以确保程序基本功能
            self.translations['en'] = {"menu": {"title": "Menu", "exit": "Exit", "invalid_choice": "Invalid choice"}}
    
    def process_arabic_text(self, text):
        """
        处理阿拉伯语文本以正确显示
        
        Args:
            text (str): 需要处理的阿拉伯语文本
        
        Returns:
            str: 处理后的阿拉伯语文本，支持从右到左显示
        
        说明:
            1. 使用 arabic_reshaper 重塑阿拉伯语文本
            2. 应用双向文本算法（BiDi）确保正确的文本方向
            3. 如果处理失败，返回原始文本
        """
        try:
            # 重塑阿拉伯语文本
            reshaped_text = arabic_reshaper.reshape(text)
            # 应用双向文本算法
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} 阿拉伯语文本处理失败: {e}{Style.RESET_ALL}")
            return text
    
    def get(self, key, fallback=None, **kwargs):
        """
        获取翻译文本，支持回退语言和格式化
        
        Args:
            key (str): 翻译键，支持点分隔的嵌套键（如 'menu.title'）
            fallback (str, optional): 当翻译不存在时的回退文本
            **kwargs: 用于格式化翻译文本的参数
        
        Returns:
            str: 翻译后的文本
        
        说明:
            1. 首先尝试当前语言的翻译
            2. 如果当前语言没有对应翻译，尝试回退语言
            3. 如果都没有，返回提供的回退文本或键本身
            4. 支持阿拉伯语文本的特殊处理
            5. 支持使用 kwargs 进行文本格式化
        """
        try:
            # 按点分割键以导航嵌套字典
            keys = key.split('.')
            
            # 首先尝试当前语言
            current_dict = self.translations.get(self.current_language, {})
            for k in keys:
                if isinstance(current_dict, dict) and k in current_dict:
                    current_dict = current_dict[k]
                else:
                    current_dict = None
                    break
            
            # 如果在当前语言中找到，格式化并返回
            if current_dict is not None:
                text = str(current_dict)
                if kwargs:
                    text = text.format(**kwargs)
                
                # 如果是阿拉伯语，进行特殊处理
                if self.current_language == 'ar':
                    text = self.process_arabic_text(text)
                
                return text
            
            # 尝试回退语言
            if self.fallback_language and self.fallback_language != self.current_language:
                fallback_dict = self.translations.get(self.fallback_language, {})
                for k in keys:
                    if isinstance(fallback_dict, dict) and k in fallback_dict:
                        fallback_dict = fallback_dict[k]
                    else:
                        fallback_dict = None
                        break
                
                if fallback_dict is not None:
                    text = str(fallback_dict)
                    if kwargs:
                        text = text.format(**kwargs)
                    return text
            
            # 返回提供的回退文本或键本身
            return fallback if fallback is not None else key
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} 翻译键 '{key}' 出错: {e}{Style.RESET_ALL}")
            return fallback if fallback is not None else key
    
    def _get_translation(self, lang_code, key):
        """Get translation for a specific language"""
        try:
            keys = key.split('.')
            value = self.translations.get(lang_code, {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, key)
                else:
                    return key
            return value
        except Exception:
            return key
    
    def set_language(self, lang_code):
        """
        设置当前语言
        
        Args:
            lang_code (str): 语言代码（如 'en', 'zh', 'ar' 等）
        
        Returns:
            bool: 设置成功返回 True，语言不存在返回 False
        
        说明:
            只有在翻译字典中存在对应语言时才会设置成功
        """
        if lang_code in self.translations:
            self.current_language = lang_code
            return True
        return False

    def get_available_languages(self):
        """
        获取所有可用语言代码列表
        
        Returns:
            list: 包含所有已加载语言代码的列表
        
        说明:
            返回当前已成功加载翻译文件的所有语言代码
        """
        # Get currently loaded languages
        available_languages = list(self.translations.keys())
        
        # Sort languages alphabetically for better display
        return sorted(available_languages)

# Create translator instance
translator = Translator()

def print_menu():
    """
    打印主菜单和账户信息
    
    功能:
        - 显示程序标题和分隔线
        - 如果有账户信息，显示账户详情
        - 以双列布局显示所有菜单选项
        - 自动计算列宽以保持对齐
        - 使用颜色和表情符号增强视觉效果
    
    菜单选项包括:
        - 基本操作：退出、重置机器、注册/登出 Cursor
        - 配置选项：语言选择、自动更新设置
        - 高级功能：OAuth 认证、版本限制绕过、令牌限制绕过
        - 系统管理：完全重置、配置打印、机器 ID 恢复
        - 其他：贡献者信息、Google 文件删除
    """
    try:
        config = get_config()
        if config.getboolean('Utils', 'enabled_account_info'):
            import cursor_acc_info
            cursor_acc_info.display_account_info(translator)
    except Exception as e:
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.account_info_error', error=str(e))}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")
    
    # Get terminal width
    try:
        terminal_width = shutil.get_terminal_size().columns
    except:
        terminal_width = 80  # Default width
    
    # Define all menu items
    menu_items = {
        0: f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}",
        1: f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}",
        2: f"{Fore.GREEN}2{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}",
        3: f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}",
        4: f"{Fore.GREEN}4{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}",
        5: f"{Fore.GREEN}5{Style.RESET_ALL}. {EMOJI['SUN']} {translator.get('menu.register_google')}",
        6: f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['STAR']} {translator.get('menu.register_github')}",
        7: f"{Fore.GREEN}7{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}",
        8: f"{Fore.GREEN}8{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.totally_reset')}",
        9: f"{Fore.GREEN}9{Style.RESET_ALL}. {EMOJI['CONTRIBUTE']} {translator.get('menu.contribute')}",
        10: f"{Fore.GREEN}10{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.config')}",
        11: f"{Fore.GREEN}11{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.bypass_version_check')}",
        12: f"{Fore.GREEN}12{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.check_user_authorized')}",
        13: f"{Fore.GREEN}13{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.bypass_token_limit')}",
        14: f"{Fore.GREEN}14{Style.RESET_ALL}. {EMOJI['BACKUP']}  {translator.get('menu.restore_machine_id')}",
        15: f"{Fore.GREEN}15{Style.RESET_ALL}. {EMOJI['ERROR']}  {translator.get('menu.delete_google_account')}",
        16: f"{Fore.GREEN}16{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.select_chrome_profile')}",
        17: f"{Fore.GREEN}17{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.manual_custom_auth')}"
    }
    
    # Automatically calculate the number of menu items in the left and right columns
    total_items = len(menu_items)
    left_column_count = (total_items + 1) // 2  # The number of options displayed on the left (rounded up)
    
    # Build left and right columns of menus
    sorted_indices = sorted(menu_items.keys())
    left_menu = [menu_items[i] for i in sorted_indices[:left_column_count]]
    right_menu = [menu_items[i] for i in sorted_indices[left_column_count:]]
    
    # Calculate the maximum display width of left menu items
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def get_display_width(s):
        """Calculate the display width of a string, considering Chinese characters and emojis"""
        # Remove ANSI color codes
        clean_s = ansi_escape.sub('', s)
        width = 0
        for c in clean_s:
            # Chinese characters and some emojis occupy two character widths
            if ord(c) > 127:
                width += 2
            else:
                width += 1
        return width
    
    max_left_width = 0
    for item in left_menu:
        width = get_display_width(item)
        max_left_width = max(max_left_width, width)
    
    # Set the starting position of right menu
    fixed_spacing = 4  # Fixed spacing
    right_start = max_left_width + fixed_spacing
    
    # Calculate the number of spaces needed for right menu items
    spaces_list = []
    for i in range(len(left_menu)):
        if i < len(left_menu):
            left_item = left_menu[i]
            left_width = get_display_width(left_item)
            spaces = right_start - left_width
            spaces_list.append(spaces)
    
    # Print menu items
    max_rows = max(len(left_menu), len(right_menu))
    
    for i in range(max_rows):
        # Print left menu items
        if i < len(left_menu):
            left_item = left_menu[i]
            print(left_item, end='')
            
            # Use pre-calculated spaces
            spaces = spaces_list[i]
        else:
            # If left side has no items, print only spaces
            spaces = right_start
            print('', end='')
        
        # Print right menu items
        if i < len(right_menu):
            print(' ' * spaces + right_menu[i])
        else:
            print()  # Change line
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")

def select_language():
    """
    允许用户选择界面语言
    
    功能:
        1. 显示所有可用的语言选项
        2. 允许用户通过数字选择语言
        3. 保存语言选择到配置文件
        4. 立即应用新的语言设置
    
    返回值:
        bool: 语言选择成功返回 True，失败返回 False
    """
    print(f"\n{Fore.CYAN}{EMOJI['LANG']} {translator.get('menu.select_language')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    
    # 获取可用语言列表
    languages = translator.get_available_languages()
    languages_count = len(languages)
    
    # 显示所有可用语言及其索引
    for i, lang in enumerate(languages):
        lang_name = translator.get(f"languages.{lang}", fallback=lang)
        print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {lang_name}")
    
    try:
        # 在提示中使用实际的语言数量
        choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{languages_count-1}')}: {Style.RESET_ALL}")
        
        if choice.isdigit() and 0 <= int(choice) < languages_count:
            selected_language = languages[int(choice)]
            translator.set_language(selected_language)
            
            # 保存选择的语言到配置文件
            config = get_config()
            if config and config.has_section('Language'):
                config.set('Language', 'current_language', selected_language)
                
                # 获取配置文件路径
                config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
                config_file = os.path.join(config_dir, "config.ini")
                
                # 写入更新后的配置
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('menu.language_config_saved', language=translator.get(f'languages.{selected_language}', fallback=selected_language))}{Style.RESET_ALL}")
            
            return True
        else:
            # 显示带有正确范围的无效选择消息
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.lang_invalid_choice', lang_choices=f'0-{languages_count-1}')}{Style.RESET_ALL}")
            return False
    except (ValueError, IndexError) as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.lang_invalid_choice', lang_choices=f'0-{languages_count-1}')}{Style.RESET_ALL}")
        return False

def check_latest_version():
    """
    检查最新版本并提示用户更新
    
    功能:
        1. 从 GitHub API 获取最新版本信息
        2. 如果 GitHub API 失败，使用备用 API
        3. 比较当前版本与最新版本
        4. 显示更新日志（如果可用）
        5. 提供自动更新选项
        6. 支持跨平台更新脚本执行
    
    API 端点:
        - 主要：GitHub API (api.github.com)
        - 备用：自定义 API (pinnumber.rr.nu)
    
    更新流程:
        1. 下载安装脚本
        2. 根据平台执行相应的安装命令
        3. 退出当前程序以完成更新
    
    错误处理:
        - 网络请求超时和失败
        - JSON 解析错误
        - 安装脚本下载和执行失败
    """
    try:
        print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('updater.checking')}{Style.RESET_ALL}")
        
        # First try GitHub API
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CursorFreeVIP-Updater'
        }
        
        latest_version = None
        github_error = None
        
        # Try GitHub API first
        try:
            github_response = requests.get(
                "https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest",
                headers=headers,
                timeout=10
            )
            
            # Check if rate limit exceeded
            if github_response.status_code == 403 and "rate limit exceeded" in github_response.text.lower():
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.rate_limit_exceeded', fallback='GitHub API rate limit exceeded. Trying backup API...')}{Style.RESET_ALL}")
                raise Exception("Rate limit exceeded")
                
            # Check if response is successful
            if github_response.status_code != 200:
                raise Exception(f"GitHub API returned status code {github_response.status_code}")
                
            github_data = github_response.json()
            if "tag_name" not in github_data:
                raise Exception("No version tag found in GitHub response")
                
            latest_version = github_data["tag_name"].lstrip('v')
            
        except Exception as e:
            github_error = str(e)
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.github_api_failed', fallback='GitHub API failed, trying backup API...')}{Style.RESET_ALL}")
            
            # If GitHub API fails, try backup API
            try:
                backup_headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'CursorFreeVIP-Updater'
                }
                backup_response = requests.get(
                    "https://pinnumber.rr.nu/badges/release/yeongpin/cursor-free-vip",
                    headers=backup_headers,
                    timeout=10
                )
                
                # Check if response is successful
                if backup_response.status_code != 200:
                    raise Exception(f"Backup API returned status code {backup_response.status_code}")
                    
                backup_data = backup_response.json()
                if "message" not in backup_data:
                    raise Exception("No version tag found in backup API response")
                    
                latest_version = backup_data["message"].lstrip('v')
                
            except Exception as backup_e:
                # If both APIs fail, raise the original GitHub error
                raise Exception(f"Both APIs failed. GitHub error: {github_error}, Backup error: {str(backup_e)}")
        
        # Validate version format
        if not latest_version:
            raise Exception("Invalid version format received")
        
        # Parse versions for proper comparison
        def parse_version(version_str):
            """Parse version string into tuple for proper comparison"""
            try:
                return tuple(map(int, version_str.split('.')))
            except ValueError:
                # Fallback to string comparison if parsing fails
                return version_str
                
        current_version_tuple = parse_version(version)
        latest_version_tuple = parse_version(latest_version)
        
        # Compare versions properly
        is_newer_version_available = False
        if isinstance(current_version_tuple, tuple) and isinstance(latest_version_tuple, tuple):
            is_newer_version_available = current_version_tuple < latest_version_tuple
        else:
            # Fallback to string comparison
            is_newer_version_available = version != latest_version
        
        if is_newer_version_available:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.new_version_available', current=version, latest=latest_version)}{Style.RESET_ALL}")
            
            # get and show changelog
            try:
                changelog_url = "https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/CHANGELOG.md"
                changelog_response = requests.get(changelog_url, timeout=10)
                
                if changelog_response.status_code == 200:
                    changelog_content = changelog_response.text
                    
                    # get latest version changelog
                    latest_version_pattern = f"## v{latest_version}"
                    changelog_sections = changelog_content.split("## v")
                    
                    latest_changes = None
                    for section in changelog_sections:
                        if section.startswith(latest_version):
                            latest_changes = section
                            break
                    
                    if latest_changes:
                        print(f"\n{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{translator.get('updater.changelog_title')}:{Style.RESET_ALL}")
                        
                        # show changelog content (max 10 lines)
                        changes_lines = latest_changes.strip().split('\n')
                        for i, line in enumerate(changes_lines[1:11]):  # skip version number line, max 10 lines
                            if line.strip():
                                print(f"{Fore.WHITE}{line.strip()}{Style.RESET_ALL}")
                        
                        # if changelog more than 10 lines, show ellipsis
                        if len(changes_lines) > 11:
                            print(f"{Fore.WHITE}...{Style.RESET_ALL}")
                        
                        print(f"{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
            except Exception as changelog_error:
                # get changelog failed
                pass
            
            # Ask user if they want to update
            while True:
                choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('updater.update_confirm', choices='Y/n')}: {Style.RESET_ALL}").lower()
                if choice in ['', 'y', 'yes']:
                    break
                elif choice in ['n', 'no']:
                    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.update_skipped')}{Style.RESET_ALL}")
                    return
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            
            try:
                # Execute update command based on platform
                if platform.system() == 'Windows':
                    update_command = 'irm https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.ps1 | iex'
                    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', update_command], check=True)
                else:
                    # For Linux/Mac, download and execute the install script
                    install_script_url = 'https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.sh'
                    
                    # First verify the script exists
                    script_response = requests.get(install_script_url, timeout=5)
                    if script_response.status_code != 200:
                        raise Exception("Installation script not found")
                        
                    # Save and execute the script
                    with open('install.sh', 'wb') as f:
                        f.write(script_response.content)
                    
                    os.chmod('install.sh', 0o755)  # Make executable
                    subprocess.run(['./install.sh'], check=True)
                    
                    # Clean up
                    if os.path.exists('install.sh'):
                        os.remove('install.sh')
                
                print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.updating')}{Style.RESET_ALL}")
                sys.exit(0)
                
            except Exception as update_error:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.update_failed', error=str(update_error))}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.manual_update_required')}{Style.RESET_ALL}")
                return
        else:
            # If current version is newer or equal to latest version
            if current_version_tuple > latest_version_tuple:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.development_version', current=version, latest=latest_version)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.up_to_date')}{Style.RESET_ALL}")
            
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.network_error', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.check_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return

def main():
    """
    程序主函数 - Cursor Free VIP 工具的入口点
    
    功能:
        1. 检查 Windows 系统的管理员权限
        2. 初始化配置和翻译系统
        3. 检查程序更新
        4. 显示主菜单并处理用户选择
        5. 提供完整的 Cursor 管理功能
    
    主要功能模块:
        - 基本操作：退出、重置机器、注册/登出 Cursor
        - 语言设置：多语言界面支持
        - OAuth 认证：Google 和 GitHub 认证
        - 高级功能：版本限制绕过、令牌限制绕过
        - 系统管理：完全重置、配置管理、机器 ID 恢复
        - 其他工具：贡献者信息、Google 文件清理
    
    错误处理:
        - 捕获键盘中断（Ctrl+C）
        - 处理意外异常
        - Windows 管理员权限检查和提升
    
    程序流程:
        1. 权限检查（Windows）
        2. 配置初始化
        3. 更新检查
        4. 主菜单循环
        5. 用户选择处理
        6. 优雅退出
    """
    # Check for admin privileges if running as executable on Windows only
    if platform.system() == 'Windows' and is_frozen() and not is_admin():
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} {translator.get('menu.admin_required')}{Style.RESET_ALL}")
        if run_as_admin():
            sys.exit(0)  # Exit after requesting admin privileges
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.admin_required_continue')}{Style.RESET_ALL}")
    
    print_logo()
    
    # Initialize configuration
    config = get_config(translator)
    if not config:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.config_init_failed')}{Style.RESET_ALL}")
        return
    force_update_config(translator)

    if config.getboolean('Utils', 'enabled_update_check'):
        check_latest_version()  # Add version check before showing menu
    print_menu()
    
    while True:
        try:
            choice_num = 17
            choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{choice_num}')}: {Style.RESET_ALL}")

            # Menu choice handling using if-elif (Python 3.9 compatible)
            if choice == "0":
                """
                ❌ 退出程序 
                """
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.exit')}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                return
            elif choice == "1":
                """
                🔄 重置机器ID
                """
                import reset_machine_manual
                reset_machine_manual.run(translator)
                print_menu()   
            elif choice == "2":
                """
                ✅ 使用自定义邮箱注册Cursor
                """
                import cursor_register_manual
                cursor_register_manual.main(translator)
                print_menu()    
            elif choice == "3":
                """
                ❌ 关闭Cursor应用
                """
                import quit_cursor
                quit_cursor.quit_cursor(translator)
                print_menu()
            elif choice == "4":
                """
                🌐 更改语言
                """
                if select_language():
                    print_menu()
                continue
            elif choice == "5":
                """
                🌟 使用自己的Google账户注册
                """
                from oauth_auth import main as oauth_main
                oauth_main('google',translator)
                print_menu()
            elif choice == "6":
                """
                ⭐ 使用自己的GitHub账户注册
                """
                from oauth_auth import main as oauth_main
                oauth_main('github',translator)
                print_menu()
            elif choice == "7":
                """
                🔄 禁用 Cursor 自动更新
                """
                import disable_auto_update
                disable_auto_update.run(translator)
                print_menu()
            elif choice == "8":
                """
                🔄 完全重置 Cursor
                """
                import totally_reset_cursor
                totally_reset_cursor.run(translator)
                # print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.fixed_soon')}{Style.RESET_ALL}")
                print_menu()
            elif choice == "9":
                """
                🤝 贡献项目
                """
                import logo
                print(logo.CURSOR_CONTRIBUTORS)
                print_menu()
            elif choice == "10":
                """
                ⚙️  显示配置
                """
                from config import print_config
                print_config(get_config(), translator)
                print_menu()
            elif choice == "11":
                """
                🔄  绕过 Cursor 版本检查
                """
                import bypass_version
                bypass_version.main(translator)
                print_menu()
            elif choice == "12":
                """
                🔄  检查用户授权
                """
                import check_user_authorized
                check_user_authorized.main(translator)
                print_menu()
            elif choice == "13":
                """
                🔄  绕过 Token 限制
                """
                import bypass_token_limit
                bypass_token_limit.run(translator)
                print_menu()
            elif choice == "14":
                """
                💾  从备份恢复机器ID
                """
                import restore_machine_id
                restore_machine_id.run(translator)
                print_menu()
            elif choice == "15":
                """
                ❌  删除 Cursor Google 账号
                """
                import delete_cursor_google
                delete_cursor_google.main(translator)
                print_menu()
            elif choice == "16":
                """
                ⚙️  选择Chrome配置文件
                """
                from oauth_auth import OAuthHandler
                oauth = OAuthHandler(translator)
                oauth._select_profile()
                print_menu()
            elif choice == "17":
                """
                🔄  手动自定义验证
                """
                import manual_custom_auth
                manual_custom_auth.main(translator)
                print_menu()
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
                print_menu()

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']}  {translator.get('menu.program_terminated')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error_occurred', error=str(e))}{Style.RESET_ALL}")
            print_menu()

# 程序入口点
if __name__ == "__main__":
    """
    程序启动入口
    
    说明:
        当脚本直接运行时（而非被导入时），执行主函数
        这是 Python 程序的标准入口点模式
    """
    main()