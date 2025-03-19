import os
import shutil
import time
import sys
import logging
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tqdm import tqdm
import shutil
import ctypes
from datetime import datetime

class Config:
    def __init__(self):
        self.config_file = Path(self.get_script_dir()) / 'config.json'
        self.load_config()

    def get_script_dir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def load_config(self):
        default_config = {
            'temp_dir': os.path.join(os.environ['TEMP'], 'WinGet'),
            'target_dir': os.path.join(self.get_script_dir(), 'soft'),
            'file_extensions': ['.exe', '.whl'],
            'scan_interval': 5,
            'retry_attempts': 3,
            'retry_delay': 1
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = {**default_config, **json.load(f)}
            except Exception as e:
                logging.error(f'加载配置文件失败: {e}')
                self.settings = default_config
        else:
            self.settings = default_config
            self.save_config()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f'保存配置文件失败: {e}')

class FileHandler(FileSystemEventHandler):
    def __init__(self, file_manager):
        self.file_manager = file_manager

    def on_created(self, event):
        if not event.is_directory:
            self.file_manager.process_file(event.src_path)

class StatusDisplay:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.clear_screen()
        self.total_files = 0
        self.current_file = ""
        self.last_update = datetime.now()

    def clear_screen(self):
        self.kernel32.SetConsoleTextAttribute(self.kernel32.GetStdHandle(-11), 0x07)
        os.system('cls')

    def update_status(self, file_manager):
        self.clear_screen()
        current_time = datetime.now()
        print("=== WinGet文件同步工具 ===")
        print(f"监控目录: {file_manager.config.settings['temp_dir']}")
        print(f"目标目录: {file_manager.config.settings['target_dir']}")
        print(f"已复制文件数: {len(file_manager.copied_files)}")
        if self.current_file:
            print(f"当前处理文件: {self.current_file}")
        print(f"最后更新时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("按Ctrl+C退出程序")
        self.last_update = current_time

class FileManager:
    def __init__(self, config):
        self.config = config
        self.copied_files = set()
        self.setup_directories()
        self.setup_logging()
        self.status_display = StatusDisplay()

    def setup_logging(self):
        log_file = Path(self.config.settings['target_dir']) / 'winget_file_all.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def setup_directories(self):
        for dir_path in [self.config.settings['temp_dir'], self.config.settings['target_dir']]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logging.info(f'确保目录存在: {dir_path}')

    def is_valid_file(self, file_path):
        return any(file_path.endswith(ext) for ext in self.config.settings['file_extensions'])

    def copy_file_with_retry(self, source_path, target_path):
        for attempt in range(self.config.settings['retry_attempts']):
            try:
                if not os.path.exists(target_path):
                    file_size = os.path.getsize(source_path)
                    self.status_display.current_file = os.path.basename(source_path)
                    with open(source_path, 'rb') as fsrc, open(target_path, 'wb') as fdst:
                        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'复制文件') as pbar:
                            while True:
                                buf = fsrc.read(8192)
                                if not buf:
                                    break
                                fdst.write(buf)
                                pbar.update(len(buf))
                    self.copied_files.add(os.path.basename(source_path))
                    logging.info(f'成功复制文件: {source_path} -> {target_path}')
                    self.status_display.current_file = ""
                    return True
                else:
                    logging.info(f'文件已存在，跳过复制: {target_path}')
                    return False
            except PermissionError:
                logging.warning(f'权限错误，无法复制文件: {source_path}，尝试次数: {attempt + 1}')
            except Exception as e:
                logging.error(f'复制文件失败: {e}，尝试次数: {attempt + 1}')
            
            if attempt < self.config.settings['retry_attempts'] - 1:
                time.sleep(self.config.settings['retry_delay'])
        
        return False

    def process_file(self, file_path):
        if not self.is_valid_file(file_path):
            return

        file_name = os.path.basename(file_path)
        if file_name in self.copied_files:
            return

        source_path = Path(file_path)
        target_path = Path(self.config.settings['target_dir']) / file_name

        if source_path.exists() and source_path.stat().st_size > 0:
            self.copy_file_with_retry(str(source_path), str(target_path))

    def remove_empty_dirs(self):
        for root, dirs, files in os.walk(self.config.settings['temp_dir'], topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        logging.info(f'删除空文件夹: {dir_path}')
                except Exception as e:
                    logging.error(f'删除文件夹失败: {e}')

def main():
    config = Config()
    file_manager = FileManager(config)
    event_handler = FileHandler(file_manager)
    observer = Observer()
    observer.schedule(event_handler, config.settings['temp_dir'], recursive=True)
    observer.start()

    try:
        logging.info('开始监控文件变化...')
        while True:
            file_manager.remove_empty_dirs()
            file_manager.status_display.update_status(file_manager)
            time.sleep(config.settings['scan_interval'])
    except KeyboardInterrupt:
        observer.stop()
        logging.info('程序已停止')
    observer.join()

if __name__ == '__main__':
    main()