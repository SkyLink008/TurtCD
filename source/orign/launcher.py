#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
import json
import hashlib
import uuid
import platform
from typing import Optional, Tuple

GITHUB_LINK = "https://github.com/SkyLink008/TurtCD"
HIDDEN_FILE = ".currentuserid"

class TurtCDLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("TurtCD Launcher")
        self.root.geometry("450x380")
        self.root.resizable(False, False)
        
        self.python_process = None
        self.is_running = False
        self.is_legitimate = True
        self.current_machine_id = None
        self.verification_message = ""
        
        if getattr(sys, 'frozen', False):
            self.script_dir = Path(sys.executable).parent.absolute()
        else:
            self.script_dir = Path(__file__).parent.absolute()
        
        self.check_legitimacy()
        self.center_window()
        self.create_ui()
        self.display_verification_result()
        
        if self.is_legitimate:
            self.root.after(100, self.check_python)
            self.add_status(f"Рабочая директория: {self.script_dir}", "info")
        else:
            self.block_launcher()
    
    def check_legitimacy(self):
        """Проверяет достоверность ПО без вывода в GUI"""
        try:
            hidden_file_path = self.script_dir / HIDDEN_FILE
            self.current_machine_id = self.generate_machine_id()
            
            if not hidden_file_path.exists():
                self.first_run_setup(hidden_file_path)
                self.is_legitimate = True
                self.verification_message = ("success", "+ ПО успешно авторизовано (первый запуск)\n")
            else:
                if self.verify_existing_id(hidden_file_path):
                    self.is_legitimate = True
                    self.verification_message = ("success", "+ Проверка лицензии пройдена успешно")
                else:
                    self.is_legitimate = False
                    self.verification_message = ("error", "- ОШИБКА: ПО было видоизменено или передано нелегально\n"
                                                          "Пожалуйста, посетите GitHub для скачивания актуальной версии")
                
        except Exception as e:
            self.is_legitimate = False
            self.verification_message = ("error", f"- ОШИБКА при проверке ПО: {str(e)}")
    
    def get_saved_id(self, file_path: Path) -> str:
        """Получает сохраненный ID из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            saved_id = data.get('machine_id', '')
            return saved_id[:16] + "..." if len(saved_id) > 16 else saved_id
        except:
            return "неизвестен"
    
    def generate_machine_id(self) -> str:
        """Генерирует уникальный ID машины на основе аппаратной информации"""
        try:
            system_info = {
                'machine': platform.machine(),
                'node': platform.node(),
                'processor': platform.processor(),
                'system': platform.system(),
                'release': platform.release()
            }
            
            if self.script_dir.exists():
                disk_info = str(self.script_dir.stat().st_dev)
            else:
                disk_info = "unknown"
            
            if platform.system() == 'Windows':
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                        machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                        system_info['machine_guid'] = machine_guid
                except:
                    pass
            
            info_string = json.dumps(system_info, sort_keys=True) + disk_info
            machine_id = hashlib.sha256(info_string.encode()).hexdigest()[:32]
            return machine_id
            
        except Exception as e:
            return str(uuid.uuid4())
    
    def first_run_setup(self, file_path: Path):
        """Настройка при первом запуске"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'machine_id': self.current_machine_id,
                    'first_run_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'version': '1.0'
                }, f, indent=2)
            
            if platform.system() == 'Windows':
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(str(file_path), FILE_ATTRIBUTE_HIDDEN)
            
        except Exception as e:
            raise Exception(f"Ошибка при первом запуске: {str(e)}")
    
    def verify_existing_id(self, file_path: Path) -> bool:
        """Проверяет существующий ID машины"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            saved_id = data.get('machine_id', '')
            return saved_id == self.current_machine_id
                
        except json.JSONDecodeError:
            return False
        except Exception as e:
            return False
    
    def display_verification_result(self):
        """Выводит результат проверки в консоль GUI"""
        if hasattr(self, 'status_text'):
            msg_type, message = self.verification_message
            for line in message.split('\n'):
                self.add_status(line, msg_type)
    
    def show_illegal_software_dialog(self):
        """Показывает диалоговое окно при нелегитимном ПО"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Нарушение лицензионного соглашения")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.configure(bg='#f5f5f5')
        
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'500x350+{x}+{y}')
        
        icon_label = tk.Label(
            dialog,
            text="⚠",
            font=('Segoe UI', 48),
            bg='#f5f5f5',
            fg='#d32f2f'
        )
        icon_label.pack(pady=(20, 10))
        
        title_label = tk.Label(
            dialog,
            text="Нарушение лицензионного соглашения",
            font=('Segoe UI', 14, 'bold'),
            bg='#f5f5f5',
            fg='#d32f2f'
        )
        title_label.pack(pady=(0, 10))
        
        message_text = """Обнаружено нелегальное распространение ПО!

ПО было видоизменено или передано на другое устройство
с нарушением лицензионного соглашения.

Для продолжения работы необходимо скачать актуальную
версию ПО с официального GitHub репозитория."""

        message_label = tk.Label(
            dialog,
            text=message_text,
            font=('Segoe UI', 10),
            bg='#f5f5f5',
            fg='#333333',
            justify=tk.CENTER,
            wraplength=400
        )
        message_label.pack(pady=(0, 20), padx=20)
        
        button_frame = tk.Frame(dialog, bg='#f5f5f5')
        button_frame.pack(pady=(0, 20))
        
        github_button = tk.Button(
            button_frame,
            text="📂 Перейти на GitHub",
            font=('Segoe UI', 10, 'bold'),
            bg='#2196f3',
            fg='white',
            activebackground='#1976d2',
            activeforeground='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=lambda: [webbrowser.open(GITHUB_LINK), dialog.destroy()]
        )
        github_button.pack(side=tk.LEFT, padx=5)
        
        exit_button = tk.Button(
            button_frame,
            text="Выйти",
            font=('Segoe UI', 10, 'bold'),
            bg='#757575',
            fg='white',
            activebackground='#616161',
            activeforeground='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2',
            command=lambda: [dialog.destroy(), self.root.destroy()]
        )
        exit_button.pack(side=tk.LEFT, padx=5)
        
        dialog.protocol("WM_DELETE_WINDOW", lambda: [dialog.destroy(), self.root.destroy()])
    
    def block_launcher(self):
        """Блокирует лаунчер при нелегитимном ПО"""
        self.start_button.config(state=tk.DISABLED)
        self.connect_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        
        for widget in [self.root, self.button_frame, self.progress_frame]:
            try:
                widget.configure(bg='#ffebee')
            except:
                pass
        
        self.root.after(500, self.show_illegal_software_dialog)
    
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'450x380+{x}+{y}')
    
    def create_ui(self):
        """Создает пользовательский интерфейс"""
        main_frame = tk.Frame(self.root, bg='#ffffff')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        container = tk.Frame(main_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=340)
        
        title_label = tk.Label(
            container,
            text="TurtCD Launcher",
            font=('Segoe UI', 20, 'bold'),
            bg='#ffffff',
            fg='#000000'
        )
        title_label.pack(pady=(10, 10))
        
        status_frame = tk.Frame(container, bg='#e0e0e0', relief=tk.FLAT)
        status_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=(0, 15))
        status_frame.config(height=160)
        
        self.status_text = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            width=40,
            height=8,
            font=('Consolas', 8),
            bg='#e0e0e0',
            fg='#000000',
            insertbackground='black',
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=8,
            state=tk.DISABLED
        )
        self.status_text.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        self.status_text.tag_config('info', foreground='#000000')
        self.status_text.tag_config('warning', foreground='#ff9900')
        self.status_text.tag_config('error', foreground='#ff0000')
        self.status_text.tag_config('success', foreground='#00aa00')
        
        self.progress_frame = tk.Frame(container, bg='#ffffff')
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar",
                        background='#000000',
                        troughcolor='#cccccc',
                        borderwidth=0,
                        lightcolor='#000000',
                        darkcolor='#000000')
        self.progress = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=360,
            style="TProgressbar",
            maximum=100
        )
        self.progress.pack(fill=tk.X, pady=(0, 3))
        self.progress.pack_forget()
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=('Segoe UI', 8),
            bg='#ffffff',
            fg='#000000'
        )
        self.progress_label.pack(fill=tk.X)
        self.progress_label.pack_forget()
        
        self.button_frame = tk.Frame(container, bg='#ffffff')
        self.button_frame.pack(padx=20, pady=(0, 15), fill=tk.X)
        
        self.start_button = tk.Button(
            self.button_frame,
            text="▶ Запустить сервер",
            font=('Segoe UI', 10, 'bold'),
            bg='#e0e0e0',
            fg='#000000',
            activebackground='#d0d0d0',
            activeforeground='#000000',
            relief=tk.FLAT,
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            command=self.start_server,
            state=tk.DISABLED
        )
        self.start_button.pack(fill=tk.X, pady=(0, 6))
        
        self.connect_button = tk.Button(
            self.button_frame,
            text="🌐 Подключиться к серверу",
            font=('Segoe UI', 10, 'bold'),
            bg='#e0e0e0',
            fg='#000000',
            activebackground='#d0d0d0',
            activeforeground='#000000',
            relief=tk.FLAT,
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            command=self.open_browser,
            state=tk.DISABLED
        )
        self.connect_button.pack(fill=tk.X, pady=(0, 6))
        
        self.stop_button = tk.Button(
            self.button_frame,
            text="⏹ Завершить работу",
            font=('Segoe UI', 10, 'bold'),
            bg='#e0e0e0',
            fg='#000000',
            activebackground='#d0d0d0',
            activeforeground='#000000',
            relief=tk.FLAT,
            bd=1,
            padx=15,
            pady=8,
            cursor='hand2',
            command=self.stop_server
        )
        self.stop_button.pack(fill=tk.X)
        self.stop_button.pack_forget()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def add_status(self, message, status_type='info'):
        """Добавляет сообщение в область статуса"""
        if not hasattr(self, 'status_text'):
            return
            
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"{timestamp} - {message}\n"
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, full_message, status_type)
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def show_progress(self, show=True, mode='indeterminate'):
        """Показывает/скрывает индикатор прогресса"""
        if show:
            self.progress.config(mode=mode)
            self.button_frame.pack_forget()
            self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            if mode == 'indeterminate':
                self.progress.pack(fill=tk.X, pady=(0, 3))
                self.progress_label.pack_forget()
                self.progress.start(10)
            else:
                self.progress.pack(fill=tk.X, pady=(0, 3))
                self.progress_label.pack(fill=tk.X)
                self.progress['value'] = 0
        else:
            if mode == 'indeterminate':
                self.progress.stop()
            self.progress.pack_forget()
            self.progress_label.pack_forget()
            self.progress_frame.pack_forget()
            self.button_frame.pack(padx=20, pady=(0, 15), fill=tk.X)
    
    def update_progress(self, value, text=""):
        """Обновляет прогресс-бар"""
        self.progress['value'] = value
        if text:
            self.progress_label.config(text=text)
        self.root.update_idletasks()
    
    def get_python_command(self):
        """Определяет команду для запуска Python"""
        commands = ['python', 'python3', 'py']
        for cmd in commands:
            try:
                if sys.platform == 'win32':
                    result = subprocess.run(
                        f'{cmd} --version',
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )
                else:
                    result = subprocess.run(
                        [cmd, '--version'],
                        capture_output=True,
                        timeout=5
                    )
                if result.returncode == 0:
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None
    
    def check_python(self):
        """Проверяет наличие Python"""
        self.add_status("Проверяю наличие Python...", "info")
        python_cmd = self.get_python_command()
        
        if python_cmd:
            try:
                if sys.platform == 'win32':
                    result = subprocess.run(
                        f'{python_cmd} --version',
                        shell=True,
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                else:
                    result = subprocess.run(
                        [python_cmd, '--version'],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                version = result.stdout.strip() if result.stdout else "неизвестно"
                self.add_status(f"Python найден: {python_cmd} ({version})", "info")
            except:
                self.add_status(f"Python найден: {python_cmd}", "info")
            self.check_dependencies()
        else:
            self.add_status("Python не найден. Запускаю pyinst.exe для установки Python...", "warning")
            self.install_python()
    
    def install_python(self):
        """Запускает pyinst.exe для установки Python"""
        pyinst_path = self.script_dir / "pyinst.exe"
        self.add_status("Проверяю наличие pyinst.exe...", "info")
        
        if not pyinst_path.exists():
            self.add_status("ОШИБКА: pyinst.exe не найден в директории лаунчера", "error")
            self.add_status("Открываю страницу загрузки Python...", "info")
            webbrowser.open('https://www.python.org/downloads/')
            return
        
        self.add_status("Запускаю pyinst.exe для установки Python...", "info")
        self.add_status("Это может занять несколько минут. Пожалуйста, подождите...", "info")
        self.show_progress(True)
        
        def install():
            try:
                if sys.platform == 'win32':
                    result = subprocess.run(
                        f'"{pyinst_path}"',
                        shell=True,
                        capture_output=True,
                        timeout=600
                    )
                else:
                    result = subprocess.run(
                        [str(pyinst_path)],
                        capture_output=True,
                        timeout=600
                    )
                
                self.root.after(0, self.show_progress, False)
                
                if result.returncode == 0:
                    self.root.after(0, self.add_status, "pyinst.exe завершил работу успешно!", "success")
                    self.root.after(0, self.add_status, "ВАЖНО: После установки Python необходимо перезапустить лаунчер!", "warning")
                    self.root.after(0, self.add_status, "Пожалуйста, закройте это окно и запустите лаунчер снова.", "warning")
                else:
                    self.root.after(0, self.add_status, "ОШИБКА: pyinst.exe завершил работу с ошибкой", "error")
                    self.root.after(0, self.add_status, "Открываю страницу загрузки Python для ручной установки...", "info")
                    webbrowser.open('https://www.python.org/downloads/')
            except subprocess.TimeoutExpired:
                self.root.after(0, self.show_progress, False)
                self.root.after(0, self.add_status, "ОШИБКА: Установка Python через pyinst.exe занимает слишком долго", "error")
                self.root.after(0, self.add_status, "Пожалуйста, установите Python вручную", "error")
                self.root.after(0, self.add_status, "Открываю страницу загрузки Python...", "info")
                webbrowser.open('https://www.python.org/downloads/')
            except Exception as e:
                self.root.after(0, self.show_progress, False)
                self.root.after(0, self.add_status, f"ОШИБКА: {str(e)}", "error")
                self.root.after(0, self.add_status, "Открываю страницу загрузки Python для ручной установки...", "info")
                webbrowser.open('https://www.python.org/downloads/')
        
        threading.Thread(target=install, daemon=True).start()
    
    def check_dependencies(self):
        """Проверяет и устанавливает зависимости"""
        python_cmd = self.get_python_command()
        if not python_cmd:
            self.add_status("ОШИБКА: Python не найден", "error")
            return
        
        requirements_file = self.script_dir / "requirements.txt"
        self.add_status(f"Ищу requirements.txt в: {requirements_file}", "info")
        if not requirements_file.exists():
            self.add_status(f"Файл requirements.txt не найден по пути: {requirements_file}", "warning")
            self.add_status("Проверяю текущую директорию...", "info")
            alt_path = Path.cwd() / "requirements.txt"
            if alt_path.exists():
                requirements_file = alt_path
                self.add_status(f"Найден requirements.txt в текущей директории: {alt_path}", "info")
            else:
                self.add_status("Файл requirements.txt не найден. Пропускаю установку зависимостей.", "warning")
                self.start_button.config(state=tk.NORMAL)
                return
        
        self.add_status("Проверяю зависимости...", "info")
        
        def install_deps():
            try:
                if sys.platform == 'win32':
                    result = subprocess.run(
                        f'{python_cmd} -m pip --version',
                        shell=True,
                        capture_output=True,
                        timeout=10
                    )
                else:
                    result = subprocess.run(
                        [python_cmd, '-m', 'pip', '--version'],
                        capture_output=True,
                        timeout=10
                    )
                
                if result.returncode != 0:
                    self.root.after(0, self.add_status, "Устанавливаю pip...", "info")
                    if sys.platform == 'win32':
                        subprocess.run(
                            f'{python_cmd} -m ensurepip --upgrade',
                            shell=True,
                            capture_output=True,
                            timeout=60
                        )
                    else:
                        subprocess.run(
                            [python_cmd, '-m', 'ensurepip', '--upgrade'],
                            capture_output=True,
                            timeout=60
                        )
                
                try:
                    with open(requirements_file, 'r', encoding='utf-8') as f:
                        requirements = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                    total_deps = len(requirements)
                except:
                    total_deps = 1
                
                self.root.after(0, self.add_status, f"Устанавливаю зависимости из requirements.txt ({total_deps} пакетов)...", "info")
                self.root.after(0, self.show_progress, True, 'determinate')
                self.root.after(0, self.update_progress, 0, "Подготовка к установке...")
                
                # Запускаем установку с выводом прогресса
                if sys.platform == 'win32':
                    process = subprocess.Popen(
                        f'{python_cmd} -m pip install -r "{requirements_file}"',
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                else:
                    process = subprocess.Popen(
                        [python_cmd, '-m', 'pip', 'install', '-r', str(requirements_file)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                
                installed_count = 0
                current_package = ""
                
                # Читаем вывод построчно
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Определяем прогресс по ключевым словам в выводе pip
                    if 'Collecting' in line or 'Downloading' in line:
                        # Извлекаем имя пакета
                        if 'Collecting' in line:
                            parts = line.split('Collecting')
                            if len(parts) > 1:
                                current_package = parts[1].split()[0].strip()
                                installed_count += 1
                                progress = min(90, (installed_count / total_deps) * 90) if total_deps > 0 else 50
                                self.root.after(0, self.update_progress, progress, f"Установка: {current_package} ({installed_count}/{total_deps})")
                    elif 'Successfully installed' in line or 'Requirement already satisfied' in line:
                        installed_count = min(installed_count + 1, total_deps)
                        progress = min(95, (installed_count / total_deps) * 95) if total_deps > 0 else 90
                        self.root.after(0, self.update_progress, progress, f"Установлено: {current_package} ({installed_count}/{total_deps})")
                    elif 'Installing collected packages' in line:
                        self.root.after(0, self.update_progress, 90, "Завершение установки...")
                
                process.wait()
                
                self.root.after(0, self.update_progress, 100, "Готово!")
                time.sleep(0.5)
                self.root.after(0, self.show_progress, False)
                
                if process.returncode == 0:
                    self.root.after(0, self.add_status, "Все зависимости установлены успешно", "info")
                else:
                    self.root.after(0, self.add_status, "Предупреждение: некоторые зависимости могли не установиться", "warning")
                
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                
            except subprocess.TimeoutExpired:
                self.root.after(0, self.show_progress, False)
                self.root.after(0, self.add_status, "ОШИБКА: Превышено время ожидания установки зависимостей", "error")
            except Exception as e:
                self.root.after(0, self.show_progress, False)
                self.root.after(0, self.add_status, f"ОШИБКА: {str(e)}", "error")
        
        threading.Thread(target=install_deps, daemon=True).start()
    
    def start_server(self):
        """Запускает сервер TurtCD"""
        python_cmd = self.get_python_command()
        if not python_cmd:
            self.add_status("ОШИБКА: Python не найден", "error")
            return
        
        main_py = self.script_dir / "main.py"
        self.add_status(f"Ищу main.py в: {main_py}", "info")
        if not main_py.exists():
            self.add_status(f"Файл main.py не найден по пути: {main_py}", "warning")
            # Пробуем также текущую рабочую директорию
            alt_path = Path.cwd() / "main.py"
            if alt_path.exists():
                main_py = alt_path
                self.add_status(f"Найден main.py в текущей директории: {alt_path}", "info")
            else:
                self.add_status("ОШИБКА: Файл main.py не найден", "error")
                return
        
        self.add_status("Запускаю сервер TurtCD...", "info")
        self.start_button.config(state=tk.DISABLED)
        self.start_button.pack_forget()
        self.connect_button.config(state=tk.NORMAL)
        self.stop_button.pack(fill=tk.X, pady=(0, 6))
        
        try:
            if sys.platform == 'win32':
                self.python_process = subprocess.Popen(
                    f'{python_cmd} "{main_py}"',
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(self.script_dir)
                )
            else:
                self.python_process = subprocess.Popen(
                    [python_cmd, str(main_py)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(self.script_dir)
                )
            self.is_running = True
            
            # Сразу показываем сообщение о запуске
            self.add_status("Сервер запущен. Нажмите 'Подключиться к серверу' для открытия в браузере.", "info")
            
        except Exception as e:
            self.add_status(f"ОШИБКА при запуске сервера: {str(e)}", "error")
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.start_button.pack(fill=tk.X, pady=(0, 6))
            self.stop_button.pack_forget()
    
    def enable_connect_button(self):
        """Включает кнопку подключения к серверу"""
        self.connect_button.config(state=tk.NORMAL)
    
    def open_browser(self):
        """Открывает браузер с страницей сервера"""
        try:
            webbrowser.open('http://localhost:5000')
            self.add_status("Браузер открыт.", "info")
        except Exception as e:
            self.add_status(f"ОШИБКА при открытии браузера: {str(e)}", "error")
    
    def stop_server(self):
        """Останавливает сервер"""
        if not self.is_running:
            return
        
        self.add_status("Останавливаю сервер...", "info")
        
        try:
            if self.python_process:
                self.python_process.terminate()
                try:
                    self.python_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.python_process.kill()
                self.python_process = None
            
            # Дополнительно убиваем процессы на порту 5000
            if sys.platform == 'win32':
                try:
                    subprocess.run(
                        ['taskkill', '/F', '/FI', 'COMMANDLINE eq *main.py*', '/T'],
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
            else:
                try:
                    subprocess.run(['pkill', '-f', 'main.py'], timeout=5)
                except:
                    pass
            
            time.sleep(1)
            
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.start_button.pack(fill=tk.X, pady=(0, 6))
            self.connect_button.config(state=tk.DISABLED)
            self.stop_button.pack_forget()
            
            self.add_status("Сервер остановлен", "info")
            
        except Exception as e:
            self.add_status(f"ОШИБКА при остановке сервера: {str(e)}", "error")
    
    def on_closing(self):
        """Обработка закрытия окна"""
        if self.is_running:
            self.stop_server()
            time.sleep(1)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TurtCDLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()