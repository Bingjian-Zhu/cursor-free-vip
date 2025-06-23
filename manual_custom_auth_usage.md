# Manual Custom Auth 使用说明

## 文件概述

`manual_custom_auth.py` 是一个用于手动设置 Cursor AI 认证信息的 Python 脚本。该脚本允许用户直接输入访问令牌和邮箱地址来完成 Cursor AI 的认证配置，无需通过自动化的 OAuth 流程。

## 主要功能

1. **手动令牌输入**：用户可以直接输入已获得的 Cursor 访问令牌
2. **令牌验证**：自动验证输入令牌的有效性（如果验证模块可用）
3. **邮箱配置**：支持手动输入邮箱或自动生成随机邮箱
4. **认证类型选择**：支持三种认证类型（Auth_0、Google、GitHub）
5. **数据库更新**：将认证信息保存到 Cursor 的本地数据库

## 使用方法

### 方法一：直接运行脚本

```bash
python manual_custom_auth.py
```

### 方法二：作为模块导入

```python
from manual_custom_auth import main

# 不使用翻译器
result = main(None)

# 使用翻译器（如果有）
result = main(translator_instance)
```

## 操作流程

### 步骤 1：输入访问令牌
- 程序会提示输入 Cursor 的访问令牌（access_token 或 refresh_token）
- 令牌不能为空，否则程序会终止

### 步骤 2：令牌验证
- 程序会尝试验证令牌的有效性
- 如果验证模块不存在，会跳过验证步骤
- 如果验证失败，用户可以选择是否继续

### 步骤 3：配置邮箱
- 用户可以输入自定义邮箱地址
- 如果留空，程序会自动生成格式为 `cursor_xxxxxxxx@cursor.ai` 的随机邮箱

### 步骤 4：选择认证类型
- 1：Auth_0（默认）
- 2：Google
- 3：GitHub
- 其他输入默认选择 Auth_0

### 步骤 5：确认信息
- 程序会显示输入的信息供用户确认
- 令牌会部分隐藏以保护隐私
- 用户需要输入 'y' 或 'yes' 确认继续

### 步骤 6：更新数据库
- 程序会将认证信息保存到 Cursor 的本地数据库
- 成功后返回 True，失败返回 False

## 依赖模块

### 必需依赖
- `colorama`：用于终端颜色输出
- `cursor_auth`：Cursor 认证管理模块

### 可选依赖
- `check_user_authorized`：令牌验证模块（如果不存在会跳过验证）

## 返回值

- `True`：认证信息更新成功
- `False`：操作失败或被用户取消

## 注意事项

1. **令牌安全**：请确保访问令牌的安全性，不要在不安全的环境中使用
2. **网络连接**：令牌验证需要网络连接
3. **权限要求**：程序需要有修改 Cursor 配置文件的权限
4. **备份建议**：建议在使用前备份现有的 Cursor 配置

## 错误处理

程序包含完善的错误处理机制：
- 输入验证：检查令牌是否为空
- 网络错误：处理令牌验证时的网络问题
- 文件权限：处理数据库更新时的权限问题
- 用户取消：支持用户在任何确认步骤取消操作

## 示例输出

```
==================================================
Manual Cursor Authentication
==================================================

ℹ️ Enter your Cursor token (access_token/refresh_token):
> your_token_here

ℹ️ Verifying token validity...
✅ Token verified successfully!

ℹ️ Enter email (leave blank for random email):
> 
✅ Random email generated: cursor_abc12345@cursor.ai

ℹ️ Select authentication type:
1. Auth_0 (Default)
2. Google
3. GitHub
> 1
✅ Selected authentication type: Auth_0

⚠️ Please confirm the following information:
Token: your_token...token_here
Email: cursor_abc12345@cursor.ai
Auth Type: Auth_0

Proceed? (y/N): y

🔄 Updating Cursor authentication database...
✅ Authentication information updated successfully!
```

## 故障排除

### 常见问题

1. **令牌验证失败**
   - 检查令牌是否正确
   - 确认网络连接正常
   - 可以选择跳过验证继续

2. **数据库更新失败**
   - 检查 Cursor 是否正在运行（建议关闭后再运行脚本）
   - 确认有足够的文件系统权限
   - 检查磁盘空间是否充足

3. **模块导入错误**
   - 确认所有依赖模块已正确安装
   - 检查 Python 路径配置

### 调试建议

- 使用 `-v` 参数运行 Python 以获得详细输出
- 检查 Cursor 的日志文件
- 确认 `cursor_auth.py` 模块在同一目录下