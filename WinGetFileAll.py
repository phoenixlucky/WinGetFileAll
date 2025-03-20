import os
import shutil
import time
import sys
from pathlib import Path
from typing import Set
import tkinter as tk
from tkinter import messagebox

class FileMonitor:
    def __init__(self):
        self.temp_dir = Path(os.environ['TEMP']) / 'WinGet'
        self.target_dir = Path.home() / 'Desktop' / 'soft'
        self.copied_files: Set[str] = set()
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.last_prompt_time = 0  # 记录上一次提示的时间
        self.prompt_interval = 20 * 60  # 20 分钟转换为秒
        print(f"源目录: {self.temp_dir}, 是否存在: {self.temp_dir.exists()}")
        print(f"目标目录: {self.target_dir}")

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
                    item.unlink()
                    print(f"删除文件 {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"删除文件夹 {item}")
            print("WinGet 目录已清空")
        except Exception as e:
            print(f"删除文件时发生错误: {e}")

    def prompt_for_deletion(self) -> None:
        """提示是否删除 WinGet 下的全部文件"""
        if not hasattr(sys, 'stdin') or sys.stdin is None:
            # 使用GUI对话框
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            choice = messagebox.askyesno("确认", "是否删除 WinGet 下的全部文件？")
            if choice:
                self.delete_all_files()
            else:
                print("保留 WinGet 文件")
        else:
            # 如果标准输入可用，使用命令行输入
            while True:
                try:
                    choice = input("是否删除 WinGet 下的全部文件？(Y/N): ").strip().upper()
                    if choice == 'Y':
                        self.delete_all_files()
                        break
                    elif choice == 'N':
                        print("保留 WinGet 文件")
                        break
                    else:
                        print("请输入 Y 或 N")
                except Exception as e:
                    print(f"获取输入时发生错误: {e}")
                    # 如果输入出错，默认使用GUI对话框
                    root = tk.Tk()
                    root.withdraw()
                    choice = messagebox.askyesno("确认", "是否删除 WinGet 下的全部文件？")
                    if choice:
                        self.delete_all_files()
                    else:
                        print("保留 WinGet 文件")
                    break

    def process_files(self) -> bool:
        """递归处理所有子目录中的 .exe 和 .whl 文件，返回是否复制了文件"""
        files_copied = False
        try:
            for file_path in self.temp_dir.rglob('*'):
                if (file_path.is_file() and 
                    file_path.stat().st_size > 0 and 
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
            print(f"处理文件时发生错误: {e}")
        return files_copied

    def run(self, scan_interval: float = 5.0) -> None:
        """主循环"""
        print(f"开始监控 {self.temp_dir}，目标路径: {self.target_dir}")
        
        # 程序开始时提示一次
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
            
            time.sleep(scan_interval)

if __name__ == "__main__":
    monitor = FileMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n程序已终止")