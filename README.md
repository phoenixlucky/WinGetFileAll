# WinGetFileAll

## 项目介绍
WinGetFileAll 是一个专门为 Windows 系统设计的文件监控和同步工具。它主要用于监控 WinGet（Windows 包管理器）下载目录，自动将下载的安装包复制到指定目录，方便用户统一管理和备份安装文件。

## 主要功能
- 🔍 自动监控 WinGet 下载目录
- 📦 自动复制指定类型的文件（默认.exe和.whl）
- 📝 详细的日志记录
- ⚙️ 可配置的监控选项
- 🗑️ 自动清理空文件夹

## 运行环境要求
- Windows 操作系统
- Python 3.6 或更高版本
- 必要的Python包（见requirements.txt）

## 安装说明
1. 克隆或下载本项目
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行程序：
   ```bash
   python WinGetFileAll.py
   ```

## 配置文件说明
程序使用`config.json`进行配置，首次运行时会自动创建默认配置文件。配置项说明：

```json
{
    "temp_dir": "%LOCALAPPDATA%/Temp/UniGetUI/ElevatedWinGetTemp/WinGet",  // 监控目录，支持环境变量
    "target_dir": "%USERPROFILE%/Desktop/soft",                        // 目标保存目录
    "file_extensions": [".exe", ".whl", ".msi"],                      // 要复制的文件类型
    "scan_interval": 5,                                               // 扫描间隔（秒）
    "retry_attempts": 3,                                              // 复制失败重试次数
    "retry_delay": 1,                                                 // 重试延迟（秒）
    "file_wait_timeout": 60,                                          // 等待文件下载完成的超时时间（秒）
    "min_file_size": 1024,                                            // 最小文件大小（字节）
    "log_level": "INFO",                                              // 日志级别
    "delete_prompt_interval": 1200                                    // 删除提示间隔（秒）
}
```

## 使用说明
1. 程序启动后会自动开始监控配置的目录
2. 当检测到新文件时，会自动复制到目标目录
3. 程序会自动清理空文件夹
4. 程序运行日志保存在`wingetfileall.log`文件中

## 日志说明
日志文件`wingetfileall.log`记录以下信息：
- 程序启动和配置信息
- 文件复制操作记录
- 错误和异常信息
- 清理操作记录

## 注意事项
- 确保程序有足够的文件读写权限
- 建议定期查看日志文件了解程序运行状态
- 可以通过修改配置文件调整程序行为

## 贡献
欢迎提交Issue和Pull Request来帮助改进这个项目。

## 许可证
MIT License