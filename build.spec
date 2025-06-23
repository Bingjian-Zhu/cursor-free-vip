# -*- mode: python ; coding: utf-8 -*-
"""
Cursor Free VIP PyInstaller 构建配置文件

这个文件用于配置 PyInstaller 打包参数，将 Python 项目打包成可执行文件。
支持 Windows、macOS 和 Linux 三个平台的自动化构建。

使用方法：
1. 确保已安装 PyInstaller: pip install pyinstaller
2. 在项目根目录运行: pyinstaller build.spec
3. 生成的可执行文件将位于 dist/ 目录下

环境变量：
- VERSION: 指定版本号（默认 1.0.0）
- TARGET_ARCH: 指定目标架构（可选）
"""

import os
import platform
from dotenv import load_dotenv

# 加载环境变量获取版本号
# 从 .env 文件中读取 VERSION 变量，如果不存在则使用默认值 '1.0.0'
load_dotenv()
version = os.getenv('VERSION', '1.0.0')

# 根据系统类型设置输出文件名的平台标识
# 自动检测当前运行的操作系统并设置相应的标识符
system = platform.system().lower()
if system == "windows":
    os_type = "windows"     # Windows 系统
elif system == "linux":
    os_type = "linux"       # Linux 系统
else:  # Darwin (macOS)
    os_type = "mac"         # macOS 系统

# 生成动态的输出文件名
# 格式：CursorFreeVIP_{版本号}_{平台}
# 例如：CursorFreeVIP_1.0.0_mac
output_name = f"CursorFreeVIP_{version}_{os_type}"

# PyInstaller 分析阶段配置
# 这个阶段会分析 Python 脚本的依赖关系
a = Analysis(
    ['main.py'],              # 主入口文件
    pathex=[],                # 额外的 Python 路径（此处为空）
    binaries=[],              # 需要包含的二进制文件（此处为空）
    
    # 需要包含的数据文件和目录
    # 格式：(源路径, 目标路径)
    datas=[
        ('locales', 'locales'),    # 多语言翻译文件目录
        ('quit_cursor.py', '.'),   # 退出 Cursor 功能模块
        ('utils.py', '.'),         # 工具函数模块
        ('.env', '.')              # 环境变量配置文件
    ],
    
    # 隐式导入的模块
    # PyInstaller 可能无法自动检测到的模块需要手动指定
    hiddenimports=[
        'quit_cursor',             # 退出 Cursor 模块
        'utils'                    # 工具函数模块
    ],
    
    hookspath=[],             # 自定义 hook 脚本路径
    hooksconfig={},           # hook 配置
    runtime_hooks=[],         # 运行时 hook
    excludes=[],              # 要排除的模块
    noarchive=False,          # 是否不创建归档文件
)

# 创建 Python 字节码归档文件
# 将所有 Python 模块编译成字节码并打包
pyz = PYZ(a.pure)

# 获取目标架构设置
# 可以通过环境变量 TARGET_ARCH 指定特定架构（如 arm64、x86_64）
# 如果未设置，PyInstaller 将使用当前系统的架构
target_arch = os.environ.get('TARGET_ARCH', None)

# 创建可执行文件
# 将所有组件打包成最终的可执行文件
exe = EXE(
    pyz,                                    # Python 字节码归档
    a.scripts,                              # 脚本文件
    a.binaries,                             # 二进制文件
    a.datas,                                # 数据文件
    [],                                     # 额外的文件（此处为空）
    
    # 可执行文件配置
    name=output_name,                       # 使用动态生成的文件名
    debug=False,                            # 不启用调试模式
    bootloader_ignore_signals=False,        # 不忽略信号处理
    strip=False,                            # 不剥离调试符号
    upx=False,                              # 不使用 UPX 压缩
    upx_exclude=[],                         # UPX 排除列表
    runtime_tmpdir=None,                    # 运行时临时目录
    
    # 界面和行为配置
    console=True,                           # 显示控制台窗口（命令行程序）
    disable_windowed_traceback=False,       # 不禁用窗口化回溯
    argv_emulation=True,                    # 启用参数模拟（对 macOS 有用）
    
    # 平台特定配置
    target_arch=target_arch,                # 目标架构（通过环境变量指定）
    codesign_identity=None,                 # macOS 代码签名身份（未设置）
    entitlements_file=None,                 # macOS 权限文件（未设置）
    icon=None                               # 应用程序图标（未设置）
)

"""
使用说明：

1. 基本打包命令：
   pyinstaller build.spec

2. 指定版本号：
   VERSION=2.0.0 pyinstaller build.spec

3. 指定目标架构（macOS）：
   TARGET_ARCH=arm64 pyinstaller build.spec
   TARGET_ARCH=x86_64 pyinstaller build.spec

4. 清理之前的构建：
   pyinstaller --clean build.spec

5. 输出文件位置：
   - 可执行文件：dist/CursorFreeVIP_{version}_{platform}
   - 构建文件：build/

注意事项：
- 确保所有依赖项都已安装（见 requirements.txt）
- 在 macOS 上可能需要安装 Xcode Command Line Tools
- Windows 上可能需要安装 Visual C++ 构建工具
- 首次打包可能需要较长时间下载依赖
"""