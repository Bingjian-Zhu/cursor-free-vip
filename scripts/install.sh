#!/bin/bash

# Cursor Free VIP 自动安装脚本
# 该脚本用于自动下载并安装 Cursor Free VIP 工具
# 支持 macOS (Intel/ARM64) 和 Linux (x64/ARM64) 系统

# 颜色定义 - 用于美化终端输出
RED='\033[0;31m'     # 红色 - 错误信息
GREEN='\033[0;32m'   # 绿色 - 成功信息
YELLOW='\033[1;33m'  # 黄色 - 警告信息
BLUE='\033[0;34m'    # 蓝色 - 普通信息
CYAN='\033[0;36m'    # 青色 - 提示信息
NC='\033[0m'         # 无颜色 - 重置颜色

# 打印程序 Logo
# 显示 ASCII 艺术字形式的 "CURSOR PRO" 标题
print_logo() {
    echo -e "${CYAN}"
    cat << "EOF"
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
EOF
    echo -e "${NC}"
}

# 获取下载文件夹路径
# 根据不同操作系统返回合适的下载目录
# macOS: ~/Downloads
# Linux: 优先使用 XDG_DOWNLOAD_DIR，否则使用 ~/Downloads
get_downloads_dir() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS 系统使用标准下载目录
        echo "$HOME/Downloads"
    else
        # Linux 系统检查用户目录配置
        if [ -f "$HOME/.config/user-dirs.dirs" ]; then
            . "$HOME/.config/user-dirs.dirs"
            echo "${XDG_DOWNLOAD_DIR:-$HOME/Downloads}"
        else
            echo "$HOME/Downloads"
        fi
    fi
}

# 获取最新版本号
# 通过 GitHub API 获取最新发布版本的标签
get_latest_version() {
    echo -e "${CYAN}ℹ️ Checking latest version...${NC}"
    
    # 调用 GitHub API 获取最新发布信息
    latest_release=$(curl -s https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest) || {
        echo -e "${RED}❌ Cannot get latest version information${NC}"
        exit 1
    }
    
    # 从 JSON 响应中提取版本号，移除 'v' 前缀
    VERSION=$(echo "$latest_release" | grep -o '"tag_name": ".*"' | cut -d'"' -f4 | tr -d 'v')
    if [ -z "$VERSION" ]; then
        echo -e "${RED}❌ Failed to parse version from GitHub API response:\n${latest_release}"
        exit 1
    fi

    echo -e "${GREEN}✅ Found latest version: ${VERSION}${NC}"
}

# 检测系统类型和架构
# 根据 uname 命令的输出确定操作系统和 CPU 架构
# 支持的组合：mac_arm64, mac_intel, linux_arm64, linux_x64, windows
detect_os() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS 系统 - 检测 CPU 架构
        ARCH=$(uname -m)
        if [[ "$ARCH" == "arm64" ]]; then
            OS="mac_arm64"  # Apple Silicon (M1/M2/M3)
            echo -e "${CYAN}ℹ️ Detected macOS ARM64 architecture${NC}"
        else
            OS="mac_intel"  # Intel 处理器
            echo -e "${CYAN}ℹ️ Detected macOS Intel architecture${NC}"
        fi
    elif [[ "$(uname)" == "Linux" ]]; then
        # Linux 系统 - 检测 CPU 架构
        ARCH=$(uname -m)
        if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
            OS="linux_arm64"  # ARM64 架构
            echo -e "${CYAN}ℹ️ Detected Linux ARM64 architecture${NC}"
        else
            OS="linux_x64"   # x86_64 架构
            echo -e "${CYAN}ℹ️ Detected Linux x64 architecture${NC}"
        fi
    else
        # 其他系统假设为 Windows
        OS="windows"
        echo -e "${CYAN}ℹ️ Detected Windows system${NC}"
    fi
}

# 安装和下载 Cursor Free VIP
# 主要功能：检查本地文件、下载二进制文件、设置权限并运行
install_cursor_free_vip() {
    # 获取下载目录和构建文件路径
    local downloads_dir=$(get_downloads_dir)
    local binary_name="CursorFreeVIP_${VERSION}_${OS}"
    local binary_path="${downloads_dir}/${binary_name}"
    local download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
    
    # 检查文件是否已存在
    if [ -f "${binary_path}" ]; then
        echo -e "${GREEN}✅ Found existing installation file${NC}"
        echo -e "${CYAN}ℹ️ Location: ${binary_path}${NC}"
        
        # 检查是否以 root 权限运行
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}⚠️ Requesting administrator privileges...${NC}"
            # 尝试使用 sudo 运行
            if command -v sudo >/dev/null 2>&1; then
                echo -e "${CYAN}ℹ️ Starting program with sudo...${NC}"
                sudo chmod +x "${binary_path}"
                sudo "${binary_path}"
            else
                echo -e "${YELLOW}⚠️ sudo not found, trying to run normally...${NC}"
                chmod +x "${binary_path}"
                "${binary_path}"
            fi
        else
            # 已经是 root 权限
            echo -e "${CYAN}ℹ️ Already running as root, starting program...${NC}"
            chmod +x "${binary_path}"
            "${binary_path}"
        fi
        return
    fi
    
    echo -e "${CYAN}ℹ️ No existing installation file found, starting download...${NC}"
    echo -e "${CYAN}ℹ️ Downloading to ${downloads_dir}...${NC}"
    echo -e "${CYAN}ℹ️ Download link: ${download_url}${NC}"
    
    # 检查下载链接是否存在
    if curl --output /dev/null --silent --head --fail "$download_url"; then
        echo -e "${GREEN}✅ File exists, starting download...${NC}"
    else
        echo -e "${RED}❌ Download link does not exist: ${download_url}${NC}"
        echo -e "${YELLOW}⚠️ Trying without architecture...${NC}"
        
        # 尝试不带架构后缀的文件名（兼容性处理）
        if [[ "$OS" == "mac_arm64" || "$OS" == "mac_intel" ]]; then
            # macOS 系统尝试通用版本
            OS="mac"
            binary_name="CursorFreeVIP_${VERSION}_${OS}"
            download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
            echo -e "${CYAN}ℹ️ New download link: ${download_url}${NC}"
            
            if ! curl --output /dev/null --silent --head --fail "$download_url"; then
                echo -e "${RED}❌ New download link does not exist${NC}"
                exit 1
            fi
        elif [[ "$OS" == "linux_x64" || "$OS" == "linux_arm64" ]]; then
            # Linux 系统尝试通用版本
            OS="linux"
            binary_name="CursorFreeVIP_${VERSION}_${OS}"
            download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
            echo -e "${CYAN}ℹ️ New download link: ${download_url}${NC}"
            
            if ! curl --output /dev/null --silent --head --fail "$download_url"; then
                echo -e "${RED}❌ New download link does not exist${NC}"
                exit 1
            fi
        else
            exit 1
        fi
    fi
    
    # 下载文件
    if ! curl -L -o "${binary_path}" "$download_url"; then
        echo -e "${RED}❌ Download failed${NC}"
        exit 1
    fi
    
    # 检查下载文件大小
    local file_size=$(stat -f%z "${binary_path}" 2>/dev/null || stat -c%s "${binary_path}" 2>/dev/null)
    echo -e "${CYAN}ℹ️ Downloaded file size: ${file_size} bytes${NC}"
    
    # 如果文件太小，可能是错误信息而不是可执行文件
    if [ "$file_size" -lt 1000 ]; then
        echo -e "${YELLOW}⚠️ Warning: Downloaded file is too small, possibly not a valid executable file${NC}"
        echo -e "${YELLOW}⚠️ File content:${NC}"
        cat "${binary_path}"
        echo ""
        echo -e "${RED}❌ Download failed, please check version and operating system${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}ℹ️ Setting executable permissions...${NC}"
    if chmod +x "${binary_path}"; then
        echo -e "${GREEN}✅ Installation completed!${NC}"
        echo -e "${CYAN}ℹ️ Program downloaded to: ${binary_path}${NC}"
        echo -e "${CYAN}ℹ️ Starting program...${NC}"
        
        # 直接运行程序
        "${binary_path}"
    else
        echo -e "${RED}❌ Installation failed${NC}"
        exit 1
    fi
}

# 主程序入口
# 按顺序执行：显示 Logo -> 获取版本 -> 检测系统 -> 安装程序
main() {
    print_logo              # 显示程序标题
    get_latest_version      # 从 GitHub 获取最新版本号
    detect_os              # 检测操作系统和架构
    install_cursor_free_vip # 下载并安装程序
}

# 运行主程序
main
