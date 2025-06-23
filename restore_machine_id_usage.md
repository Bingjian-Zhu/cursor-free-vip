# restore_machine_id.py 使用说明

## 文件概述

`restore_machine_id.py` 是一个用于恢复 Cursor 编辑器机器 ID 的 Python 脚本。该脚本可以从之前创建的备份文件中恢复机器标识符，确保 Cursor 编辑器能够正确识别和验证设备。

## 主要功能

1. **备份文件管理**：列出和选择可用的备份文件
2. **ID 提取**：从备份文件中提取各种机器标识符
3. **文件更新**：更新 `storage.json` 文件中的机器 ID
4. **数据库更新**：更新 SQLite 数据库中的相关记录
5. **系统级更新**：根据操作系统更新系统级标识符
6. **machineId 文件更新**：更新专用的 machineId 文件

## 使用方法

### 1. 直接运行

```bash
python restore_machine_id.py
```

### 2. 作为模块导入

```python
from restore_machine_id import run, MachineIDRestorer
from main import translator

# 运行完整的恢复流程
run(translator)

# 或者创建恢复器实例进行自定义操作
restorer = MachineIDRestorer(translator)
restorer.restore_machine_ids()
```

## 操作流程

### 步骤 1：启动程序
运行脚本后，程序会显示标题并检查配置文件。

### 步骤 2：选择备份文件
程序会列出所有可用的备份文件，显示：
- 文件名
- 创建时间
- 文件大小

用户需要输入要恢复的备份文件编号，或输入 'q' 取消操作。

### 步骤 3：预览要恢复的 ID
程序会显示从备份文件中提取的所有机器 ID，包括：
- `telemetry.devDeviceId`：设备 ID
- `telemetry.macMachineId`：Mac 机器 ID（仅 macOS）
- `telemetry.machineId`：通用机器 ID
- `telemetry.sqmId`：SQM ID
- `storage.serviceMachineId`：服务机器 ID

### 步骤 4：确认恢复
用户需要输入 'y' 确认恢复操作，或输入其他字符取消。

### 步骤 5：执行恢复
程序会依次执行以下操作：
1. 备份当前的 `storage.json` 文件
2. 更新 `storage.json` 文件中的机器 ID
3. 更新 SQLite 数据库中的相关记录
4. 更新 machineId 文件
5. 根据操作系统更新系统级标识符

## 支持的操作系统

### Windows
- 更新注册表中的 `MachineGuid`
- 更新 `SQMClient` 的 `MachineId`
- 需要管理员权限

### macOS
- 更新平台 UUID 配置文件
- 需要 sudo 权限

### Linux
- 仅更新应用程序级别的标识符
- 不涉及系统级更改

## 备份文件格式

备份文件应为 JSON 格式，包含以下字段：
```json
{
  "telemetry.devDeviceId": "设备ID",
  "telemetry.macMachineId": "Mac机器ID",
  "telemetry.machineId": "通用机器ID",
  "telemetry.sqmId": "SQM ID",
  "storage.serviceMachineId": "服务机器ID"
}
```

## 配置要求

程序需要 `config.ini` 配置文件，包含以下部分：

```ini
[windows]
db_path = Windows下的数据库路径
sqlite_path = Windows下的SQLite路径

[macos]
db_path = macOS下的数据库路径
sqlite_path = macOS下的SQLite路径

[linux]
db_path = Linux下的数据库路径
sqlite_path = Linux下的SQLite路径
```

## 错误处理

程序包含完善的错误处理机制：

1. **文件不存在**：如果备份文件或配置文件不存在，程序会显示相应错误信息
2. **权限不足**：在 Windows 或 macOS 上更新系统级标识符时，如果权限不足会显示警告
3. **格式错误**：如果备份文件格式不正确，程序会显示解析错误
4. **数据库错误**：SQLite 数据库操作失败时会显示详细错误信息

## 安全注意事项

1. **备份重要性**：程序会在修改文件前自动创建备份
2. **权限要求**：某些操作需要管理员或 sudo 权限
3. **文件完整性**：确保备份文件来源可信，避免恶意数据
4. **操作确认**：程序会在执行关键操作前要求用户确认

## 故障排除

### 常见问题

1. **权限被拒绝**
   - Windows：以管理员身份运行命令提示符
   - macOS：使用 `sudo python restore_machine_id.py`

2. **配置文件未找到**
   - 确保 `config.ini` 文件存在于脚本同一目录
   - 检查配置文件格式是否正确

3. **备份文件格式错误**
   - 确保备份文件是有效的 JSON 格式
   - 检查必需的字段是否存在

4. **SQLite 数据库锁定**
   - 确保 Cursor 编辑器已完全关闭
   - 检查是否有其他进程正在使用数据库文件

### 日志和调试

程序会在控制台输出详细的操作信息，包括：
- 操作进度
- 成功/失败状态
- 错误详情
- 文件路径信息

## 相关文件

- `reset_machine_manual.py`：用于重置机器 ID 的脚本
- `main.py`：主程序入口
- `config.ini`：配置文件
- `translations/`：多语言支持文件

## 版本兼容性

- Python 3.6+
- 支持 Windows 10+、macOS 10.14+、Ubuntu 18.04+
- 兼容 Cursor 编辑器的所有版本