import os
import shutil
import time
import sys
import json
from pathlib import Path
from typing import Set, Dict, Any, List
import tkinter as tk
from tkinter import messagebox

# 设置控制台输出编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

class FileMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.temp_dir = self.get_temp_dir()
        self.target_dir = self.get_target_dir()
        self.file_extensions = self.config.get('file_extensions', ['.exe', '.whl'])
        self.scan_interval = self.config.get('scan_interval', 5)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        self.copied_files: Set[str] = set()
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.last_prompt_time = 0  # 记录上一次提示的时间
        self.prompt_interval = 20 * 60  # 20 分钟转换为秒
        self.known_files: Set[str] = set()  # 记录已知的文件
        self.file_sizes: dict = {}  # 记录文件大小
        print(f"源目录: {self.temp_dir}, 是否存在: {self.temp_dir.exists()}")
        print(f"目标目录: {self.target_dir}")
        print(f"监控文件类型: {self.file_extensions}")
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件，如果不存在则创建默认配置"""
        config_path = Path('config.json')
        default_config = {
            "temp_dir": "%TEMP%/WinGet",
            "target_dir": "./soft",
            "file_extensions": [".exe", ".whl"],
            "scan_interval": 5,
            "retry_attempts": 3,
            "retry_delay": 1
        }
        
        if not config_path.exists():
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print(f"已创建默认配置文件: {config_path}")
            return default_config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"已加载配置文件: {config_path}")
            return config
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return default_config
    
    def get_temp_dir(self) -> Path:
        """获取监控目录路径"""
        temp_dir_str = self.config.get('temp_dir', "%TEMP%/WinGet")
        # 替换环境变量
        if "%TEMP%" in temp_dir_str:
            temp_dir_str = temp_dir_str.replace("%TEMP%", os.environ['TEMP'])
        return Path(temp_dir_str)
    
    def get_target_dir(self) -> Path:
        """获取目标目录路径"""
        target_dir_str = self.config.get('target_dir', "./soft")
        # 如果是相对路径，则相对于当前目录
        if target_dir_str.startswith("./") or target_dir_str.startswith(".\\"): 
            return Path(os.getcwd()) / target_dir_str[2:]
        return Path(target_dir_str)

    def remove_empty_dirs(self, path: Path) -> None:
        """递归删除空文件夹"""
        try:
            for dir_path in path.rglob('*'):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"删除空文件夹 {dir_path}")
        except Exception as e:
            print(f"删除文件夹时发生错误: {e}")

    def delete_all_files(self) -> None:
        """删除 WinGet 下的所有文件和文件夹"""
        try:
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        print(f"删除文件 {item}")
                    except PermissionError as pe:
                        if "[WinError 32]" in str(pe):
                            print(f"文件被占用，跳过删除: {item}")
                            continue
                        raise pe
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"删除文件夹 {item}")
            print("WinGet 目录已清空")
        except Exception as e:
            print(f"删除文件时发生错误: {e}")

    def prompt_for_deletion(self) -> None:
        """提示是否删除 WinGet 下的全部文件"""
        # 统一使用GUI对话框
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        choice = messagebox.askyesno("确认", "是否删除 WinGet 下的全部文件？")
        if choice:
            self.delete_all_files()
        else:
            print("保留 WinGet 文件")

    def process_files(self) -> bool:
        """递归处理所有子目录中的指定文件类型，返回是否复制了文件"""
        files_copied = False
        try:
<<<<<<< HEAD
            if not self.temp_dir.exists():
                return files_copied

            # 获取当前所有文件
            current_files = set()
            current_sizes = {}
            
            # 记录当前已存在的文件夹
            existing_dirs = {d for d in self.temp_dir.iterdir() if d.is_dir()}
            
            # 扫描所有文件
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    current_files.add(file_path.name)
                    try:
                        current_size = file_path.stat().st_size
                        current_sizes[file_path.name] = current_size

                        # 检查是否是新文件
                        if file_path.name not in self.known_files:
                            print(f"检测到新文件: {file_path.name}")
                        # 检查文件大小是否变化（下载中）
                        elif file_path.name in self.file_sizes and current_size > self.file_sizes[file_path.name]:
                            print(f"文件正在下载中: {file_path.name} ({current_size} bytes)")

                        if (current_size > 0 and 
                            not file_path.name.endswith('.tmp') and 
                            file_path.name not in self.copied_files and 
                            file_path.suffix.lower() in ('.exe', '.whl')):
                            
                            target_file = self.target_dir / file_path.name
                            
                            if not target_file.exists():
                                try:
                                    shutil.copy(file_path, target_file)
                                    self.copied_files.add(file_path.name)
                                    print(f"文件 {file_path.name} 成功复制到 {self.target_dir}")
                                    files_copied = True
                                except PermissionError:
                                    print(f"权限错误，无法复制 {file_path}")
                                except Exception as e:
                                    print(f"复制文件时发生错误: {e}")
                            else:
                                print(f"文件 {file_path.name} 已存在，跳过")
                    except Exception as e:
                        print(f"处理文件 {file_path.name} 时发生错误: {e}")
            
            # 检查是否有新文件夹生成
            current_dirs = {d for d in self.temp_dir.iterdir() if d.is_dir()}
            new_dirs = current_dirs - existing_dirs
            for new_dir in new_dirs:
                print(f"检测到新文件夹: {new_dir}")
            
            # 更新已知文件列表和大小记录
            self.known_files = current_files
            self.file_sizes = current_sizes
                    
=======
            # 确保目标目录存在
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            # 递归搜索所有子目录
            for file_path in self.temp_dir.rglob('*'):
                if (file_path.is_file() and 
                    file_path.stat().st_size > 0 and 
                    not file_path.name.endswith('.tmp') and 
                    file_path.name not in self.copied_files and 
                    file_path.suffix.lower() in self.file_extensions):
                    
                    # 保持相对路径结构
                    rel_path = file_path.relative_to(self.temp_dir)
                    target_file = self.target_dir / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if not target_file.exists():
                        for attempt in range(self.retry_attempts):
                            try:
                                shutil.copy(file_path, target_file)
                                self.copied_files.add(file_path.name)
                                print(f"文件 {file_path.name} 成功复制到 {self.target_dir}")
                                files_copied = True
                                break
                            except PermissionError:
                                print(f"权限错误，无法复制 {file_path}，尝试 {attempt+1}/{self.retry_attempts}")
                                if attempt < self.retry_attempts - 1:
                                    time.sleep(self.retry_delay)
                            except Exception as e:
                                print(f"复制文件时发生错误: {e}，尝试 {attempt+1}/{self.retry_attempts}")
                                if attempt < self.retry_attempts - 1:
                                    time.sleep(self.retry_delay)
                    else:
                        print(f"文件 {file_path.name} 已存在，跳过")
>>>>>>> e2df8d90d183188c7defd85641487bc4f3abcb02
        except Exception as e:
            print(f"处理文件时发生错误: {e}")
        return files_copied

    def run(self) -> None:
        """主循环"""
        print(f"开始监控 {self.temp_dir}，目标路径: {self.target_dir}")
        print(f"扫描间隔: {self.scan_interval}秒，重试次数: {self.retry_attempts}，重试延迟: {self.retry_delay}秒")
        
        # 程序开始时先处理现有文件
        self.process_files()
        # 然后提示是否删除
        self.prompt_for_deletion()
        self.last_prompt_time = time.time()
        
        while True:
            try:
                # 处理文件
                self.process_files()
                
                # 清理空目录
                self.remove_empty_dirs(self.temp_dir)
                
                # 检查是否需要提示删除
                current_time = time.time()
                if current_time - self.last_prompt_time >= self.prompt_interval:
                    self.prompt_for_deletion()
                    self.last_prompt_time = current_time
                
            except Exception as e:
                print(f"主循环发生错误: {e}")
            
            time.sleep(self.scan_interval)

if __name__ == "__main__":
    monitor = FileMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n程序已终止")
    except Exception as e:
        print(f"程序运行出错: {e}")
        input("按任意键退出...")