import os
import shutil
import time
import sys
import json
import logging
from pathlib import Path
from typing import Set, Dict, Any, List
import tkinter as tk
from tkinter import messagebox
import atexit
import win32file
import win32con
import pywintypes
import msvcrt

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wingetfileall.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 设置控制台输出编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def handle_exit():
    root = tk.Tk()
    root.withdraw()
    if messagebox.askyesno("确认退出", "确定要退出程序吗？"):
        logging.info("用户确认退出程序")
        sys.exit(0)
    else:
        logging.info("用户取消退出程序")
        return

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        handle_exit()
        return
    logging.error("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("错误", f"程序遇到错误: {str(exc_value)}\n请查看日志文件了解详情。")

def is_file_locked(file_path: Path) -> bool:
    """检查文件是否被锁定"""
    try:
        # 尝试以独占模式打开文件
        with open(file_path, 'rb') as f:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        return False
    except (IOError, PermissionError):
        return True

def wait_for_file_completion(file_path: Path, timeout: int = 60) -> bool:
    """等待文件下载完成
    
    Args:
        file_path: 文件路径
        timeout: 超时时间（秒）
        
    Returns:
        bool: 文件是否可用
    """
    start_time = time.time()
    last_size = -1
    unchanged_count = 0
    
    while time.time() - start_time < timeout:
        try:
            current_size = file_path.stat().st_size
            if current_size == last_size:
                unchanged_count += 1
                if unchanged_count >= 3:  # 连续3次大小不变，认为下载完成
                    return True
            else:
                unchanged_count = 0
                last_size = current_size
            time.sleep(1)
        except FileNotFoundError:
            logging.warning(f"文件不存在或已被移动: {file_path}")
            return False
        except Exception as e:
            logging.error(f"检查文件大小时发生错误: {e}")
            return False
    
    logging.warning(f"等待文件 {file_path} 完成下载超时")
    return False

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
        self.known_files: Set[str] = set()  # 记录已知的文件
        self.file_sizes: dict = {}  # 记录文件大小
        # 设置日志级别
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        logging.getLogger().setLevel(log_level)
        
        logging.info(f"源目录: {self.temp_dir}, 是否存在: {self.temp_dir.exists()}")
        logging.info(f"目标目录: {self.target_dir}")
        logging.info(f"监控文件类型: {self.file_extensions}")
        logging.info(f"日志级别: {logging.getLevelName(log_level)}")
        
        if not self.temp_dir.exists():
            logging.warning(f"源目录不存在: {self.temp_dir}")
        if not self.target_dir.exists():
            logging.info(f"目标目录不存在，将创建: {self.target_dir}")
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件，如果不存在则创建默认配置"""
        config_path = Path('config.json')
        default_config = {
            "temp_dir": "%LOCALAPPDATA%/Temp/UniGetUI/ElevatedWinGetTemp/WinGet",
            "target_dir": "%USERPROFILE%/Desktop/soft",
            "file_extensions": [".exe", ".whl", ".msi"],
            "scan_interval": 5,
            "retry_attempts": 3,
            "retry_delay": 1,
            "log_level": "INFO"
        }
        
        if not config_path.exists():
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                logging.info(f"已创建默认配置文件: {config_path}")
                return default_config
            except Exception as e:
                logging.error(f"创建配置文件失败: {e}")
                return default_config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logging.info(f"已加载配置文件: {config_path}")
            return config
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}，使用默认配置")
            return default_config
    
    def get_temp_dir(self) -> Path:
        """获取监控目录路径"""
        temp_dir_str = self.config.get('temp_dir', "%LOCALAPPDATA%/Packages")
        # 替换环境变量
        if "%LOCALAPPDATA%" in temp_dir_str:
            temp_dir_str = temp_dir_str.replace("%LOCALAPPDATA%", os.environ['LOCALAPPDATA'])
        return Path(temp_dir_str)
    
    def get_target_dir(self) -> Path:
        """获取目标目录路径"""
        target_dir_str = self.config.get('target_dir', "%USERPROFILE%/Desktop/soft")
        # 替换环境变量
        if "%USERPROFILE%" in target_dir_str:
            target_dir_str = target_dir_str.replace("%USERPROFILE%", os.environ['USERPROFILE'])
        if "%LOCALAPPDATA%" in target_dir_str:
            target_dir_str = target_dir_str.replace("%LOCALAPPDATA%", os.environ['LOCALAPPDATA'])
        
        target_path = Path(target_dir_str)
        # 确保目标目录存在
        target_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"目标目录已设置为: {target_path}")
        return target_path

    def remove_empty_dirs(self, path: Path) -> None:
        """递归删除空文件夹"""
        try:
            # 确保使用正确的路径 - 使用temp_dir而不是任意路径
            target_path = self.temp_dir
            for dir_path in target_path.rglob('*'):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    try:
                        dir_path.rmdir()
                        logging.info(f"删除空文件夹 {dir_path}")
                    except PermissionError:
                        logging.warning(f"权限不足，无法删除文件夹 {dir_path}")
                    except Exception as e:
                        logging.error(f"删除文件夹 {dir_path} 时发生错误: {e}")
        except Exception as e:
            logging.error(f"删除空文件夹操作失败: {e}", exc_info=True)

    def delete_all_files(self) -> None:
        """删除 WinGet 下的所有文件和文件夹"""
        try:
            deleted_files = 0
            skipped_files = 0
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        deleted_files += 1
                        logging.info(f"删除文件 {item}")
                    except PermissionError as pe:
                        if "[WinError 32]" in str(pe):
                            logging.warning(f"文件被占用，跳过删除: {item}")
                            skipped_files += 1
                            continue
                        logging.error(f"删除文件 {item} 时权限不足: {pe}")
                        skipped_files += 1
                    except Exception as e:
                        logging.error(f"删除文件 {item} 时发生错误: {e}")
                        skipped_files += 1
                elif item.is_dir():
                    try:
                        shutil.rmtree(item)
                        logging.info(f"删除文件夹 {item}")
                        deleted_files += 1
                    except Exception as e:
                        logging.error(f"删除文件夹 {item} 时发生错误: {e}")
                        skipped_files += 1
            logging.info(f"WinGet 目录清理完成: 成功删除 {deleted_files} 个项目，跳过 {skipped_files} 个项目")
        except Exception as e:
            logging.error(f"清理 WinGet 目录时发生错误: {e}", exc_info=True)

    # 已移除prompt_for_deletion方法

    def process_files(self) -> bool:
        """递归处理所有子目录中的指定文件类型，返回是否复制了文件"""
        files_copied = False
        try:
            if not self.temp_dir.exists():
                logging.warning(f"源目录不存在: {self.temp_dir}")
                return files_copied

            current_files = set()
            current_sizes = {}
            
            # 记录当前已存在的文件夹
            existing_dirs = {d for d in self.temp_dir.iterdir() if d.is_dir()}
            
            # 扫描所有文件
            for file_path in self.temp_dir.rglob('*'):
                if not file_path.is_file():
                    continue
                
                current_files.add(file_path.name)
                try:
                    current_size = file_path.stat().st_size
                    current_sizes[file_path.name] = current_size

                    # 检查文件是否符合要求
                    if (current_size > 0 and 
                        not file_path.name.endswith('.tmp') and 
                        file_path.name not in self.copied_files and 
                        file_path.suffix.lower() in self.file_extensions):
                        
                        target_file = self.target_dir / file_path.name
                        
                        if not target_file.exists():
                            # 检查文件是否被锁定或正在下载
                            if is_file_locked(file_path):
                                logging.info(f"文件 {file_path.name} 正在被使用，等待解锁...")
                                if not wait_for_file_completion(file_path):
                                    continue
                            
                            for attempt in range(self.retry_attempts):
                                try:
                                    # 使用低级文件操作来复制
                                    with open(file_path, 'rb') as source:
                                        with open(target_file, 'wb') as target:
                                            shutil.copyfileobj(source, target, length=1024*1024)  # 1MB chunks
                                    
                                    # 验证复制是否成功
                                    if target_file.exists() and target_file.stat().st_size == current_size:
                                        self.copied_files.add(file_path.name)
                                        logging.info(f"文件 {file_path.name} 成功复制到 {target_file}")
                                        files_copied = True
                                        break
                                    else:
                                        raise Exception("文件复制验证失败")
                                    
                                except PermissionError as pe:
                                    logging.warning(f"权限错误，无法复制 {file_path}，尝试 {attempt+1}/{self.retry_attempts}")
                                    if "[WinError 32]" in str(pe):  # 文件正在使用
                                        time.sleep(self.retry_delay * 2)  # 等待更长时间
                                    if attempt < self.retry_attempts - 1:
                                        time.sleep(self.retry_delay)
                                except FileNotFoundError:
                                    logging.warning(f"源文件不存在或已被移动: {file_path}")
                                    break
                                except Exception as e:
                                    logging.error(f"复制文件时发生错误: {file_path}, 错误: {e}, 尝试 {attempt+1}/{self.retry_attempts}")
                                    if attempt < self.retry_attempts - 1:
                                        time.sleep(self.retry_delay)
                        else:
                            logging.debug(f"文件已存在，跳过: {target_file}")
                except Exception as e:
                    logging.error(f"处理文件 {file_path.name} 时发生错误: {e}")
            
            # 更新已知文件列表和大小记录
            self.known_files = current_files
            self.file_sizes = current_sizes
                    
        except Exception as e:
            logging.error(f"处理文件时发生错误: {e}", exc_info=True)
        return files_copied

    def run(self) -> None:
        """主循环"""
        logging.info(f"开始监控 {self.temp_dir}，目标路径: {self.target_dir}")
        logging.info(f"扫描间隔: {self.scan_interval}秒，重试次数: {self.retry_attempts}，重试延迟: {self.retry_delay}秒")
        
        try:
            # 程序开始时先处理现有文件
            if self.process_files():
                logging.info("初始文件处理完成")
            
            # 移除提示是否删除的功能
            logging.info("进入主循环监控模式")
            while True:
                try:
                    # 处理文件
                    if self.process_files():
                        logging.info("发现并处理了新文件")
                    
                    # 清理空目录
                    self.remove_empty_dirs(self.temp_dir)
                    
                    # 移除定期提示删除功能
                    
                except Exception as e:
                    logging.error(f"主循环迭代发生错误: {e}", exc_info=True)
                finally:
                    time.sleep(self.scan_interval)
        except Exception as e:
            logging.error(f"主循环发生致命错误: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    # 设置全局异常处理
    sys.excepthook = handle_exception
    # 注册退出处理
    atexit.register(handle_exit)
    
    try:
        monitor = FileMonitor()
        logging.info("程序启动成功，开始监控文件...")
        monitor.run()
    except Exception as e:
        logging.error(f"程序运行时发生错误: {e}", exc_info=True)
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", f"程序运行时发生错误: {str(e)}\n请查看日志文件了解详情。")
        sys.exit(1)