#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TurtCD Launcher - Графический лаунчер для запуска TurtCD
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
import json

class TurtCDLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 TurtCD Launcher")
        self.root.geometry("450x380")
        self.root.resizable(False, False)
        
        # Центрируем окно
        self.center_window()
        
        # Переменные
        self.python_process = None
        self.is_running = False
        # Определяем путь к директории скрипта (работает и в exe, и в .py)
        if getattr(sys, 'frozen', False):
            # Если запущено как exe (PyInstaller)
            self.script_dir = Path(sys.executable).parent.absolute()
        else:
            # Если запущено как .py скрипт
            self.script_dir = Path(__file__).parent.absolute()
        
        # Создаем интерфейс
        self.create_ui()
        
        # Запускаем проверку Python
        self.root.after(100, self.check_python)
        
        # Отладочная информация (можно убрать позже)
        self.add_status(f"Рабочая директория: {self.script_dir}", "info")
    
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
        # Основной контейнер
        main_frame = tk.Frame(self.root, bg='#ffffff')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Контейнер с содержимым
        container = tk.Frame(main_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=400, height=340)
        
        # Заголовок
        title_label = tk.Label(
            container,
            text="🚀 TurtCD Launcher",
            font=('Segoe UI', 20, 'bold'),
            bg='#ffffff',
            fg='#000000'
        )
        title_label.pack(pady=(10, 10))
        
        # Область статуса
        status_frame = tk.Frame(container, bg='#e0e0e0', relief=tk.FLAT)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.status_text = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            width=40,
            height=6,
            font=('Consolas', 8),
            bg='#e0e0e0',
            fg='#000000',
            insertbackground='black',
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=8,
            state=tk.DISABLED  # Отключаем редактирование
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Настраиваем теги для цветов (все черные)
        self.status_text.tag_config('info', foreground='#000000')
        self.status_text.tag_config('warning', foreground='#000000')
        self.status_text.tag_config('error', foreground='#000000')
        
        # Индикатор прогресса (черно-белый стиль)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar",
                        background='#000000',
                        troughcolor='#cccccc',
                        borderwidth=0,
                        lightcolor='#000000',
                        darkcolor='#000000')
        self.progress = ttk.Progressbar(
            container,
            mode='determinate',
            length=360,
            style="TProgressbar",
            maximum=100
        )
        self.progress_label = tk.Label(
            container,
            text="",
            font=('Segoe UI', 8),
            bg='#ffffff',
            fg='#000000'
        )
        self.progress.pack(padx=20, pady=(0, 5), fill=tk.X)
        self.progress_label.pack(padx=20, pady=(0, 15))
        self.progress.pack_forget()  # Скрываем по умолчанию
        self.progress_label.pack_forget()  # Скрываем по умолчанию
        
        # Кнопки
        button_frame = tk.Frame(container, bg='#ffffff')
        button_frame.pack(padx=20, pady=(0, 15), fill=tk.X)
        
        self.start_button = tk.Button(
            button_frame,
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
        
        self.stop_button = tk.Button(
            button_frame,
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
        self.stop_button.pack_forget()  # Скрываем по умолчанию
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def add_status(self, message, status_type='info'):
        """Добавляет сообщение в область статуса"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"{timestamp} - {message}\n"
        
        # Временно включаем редактирование для добавления текста
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, full_message, status_type)
        self.status_text.see(tk.END)
        # Отключаем редактирование обратно
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def show_progress(self, show=True, mode='indeterminate'):
        """Показывает/скрывает индикатор прогресса"""
        if show:
            self.progress.config(mode=mode)
            if mode == 'indeterminate':
                self.progress.pack(padx=20, pady=(0, 5), fill=tk.X, before=self.start_button)
                self.progress_label.pack_forget()
                self.progress.start(10)
            else:
                self.progress.pack(padx=20, pady=(0, 5), fill=tk.X, before=self.start_button)
                self.progress_label.pack(padx=20, pady=(0, 15), before=self.start_button)
                self.progress['value'] = 0
        else:
            if mode == 'indeterminate':
                self.progress.stop()
            self.progress.pack_forget()
            self.progress_label.pack_forget()
    
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
                # Используем shell=True для Windows, чтобы правильно находить команды
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
            # Проверяем версию Python для отладки
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
            self.add_status("Python не найден. Начинаю установку через winget...", "warning")
            self.install_python()
    
    def install_python(self):
        """Устанавливает Python через winget"""
        self.add_status("Проверяю наличие winget...", "info")
        
        try:
            if sys.platform == 'win32':
                result = subprocess.run(
                    'winget --version',
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['winget', '--version'],
                    capture_output=True,
                    timeout=5
                )
            if result.returncode != 0:
                raise FileNotFoundError
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.add_status("ОШИБКА: winget не найден. Установите App Installer из Microsoft Store", "error")
            self.add_status("Открываю страницу загрузки Python...", "info")
            webbrowser.open('https://www.python.org/downloads/')
            return
        
        self.add_status("Устанавливаю Python через winget...", "info")
        self.add_status("Это может занять несколько минут. Пожалуйста, подождите...", "info")
        self.show_progress(True)
        
        def install():
            try:
                # Уменьшаем таймаут до 3 минут (180 секунд)
                if sys.platform == 'win32':
                    result = subprocess.run(
                        'winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements',
                        shell=True,
                        capture_output=True,
                        timeout=180  # 3 минуты максимум
                    )
                else:
                    result = subprocess.run(
                        ['winget', 'install', '--id', 'Python.Python.3.12', 
                         '--silent', '--accept-package-agreements', '--accept-source-agreements'],
                        capture_output=True,
                        timeout=180  # 3 минуты максимум
                    )
                
                self.root.after(0, self.show_progress, False)
                
                if result.returncode == 0:
                    self.root.after(0, self.add_status, "Python установлен успешно!", "info")
                    self.root.after(0, self.add_status, "Обновляю переменные окружения...", "info")
                    time.sleep(2)
                    self.root.after(0, self.check_python)
                else:
                    self.root.after(0, self.add_status, "ОШИБКА: Не удалось установить Python через winget", "error")
                    self.root.after(0, self.add_status, "Открываю страницу загрузки Python для ручной установки...", "info")
                    webbrowser.open('https://www.python.org/downloads/')
            except subprocess.TimeoutExpired:
                self.root.after(0, self.show_progress, False)
                self.root.after(0, self.add_status, "ОШИБКА: Установка Python через winget занимает слишком долго", "error")
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
            # Пробуем также текущую рабочую директорию
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
                # Проверяем pip
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
                
                # Читаем requirements.txt для подсчета зависимостей
                try:
                    with open(requirements_file, 'r', encoding='utf-8') as f:
                        requirements = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                    total_deps = len(requirements)
                except:
                    total_deps = 1  # Если не удалось прочитать, используем 1
                
                # Устанавливаем зависимости
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
                
                self.root.after(0, self.update_progress, 100, "Установка завершена!")
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
        self.stop_button.pack(fill=tk.X, pady=(0, 10))
        
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
            
            # Ждем запуска сервера и открываем браузер
            self.add_status("Ожидаю запуска сервера...", "info")
            
            def wait_and_open():
                port_open = False
                for i in range(30):
                    time.sleep(1)
                    try:
                        import urllib.request
                        response = urllib.request.urlopen('http://localhost:5000', timeout=1)
                        if response.getcode() == 200:
                            port_open = True
                            break
                    except:
                        continue
                
                time.sleep(1)
                webbrowser.open('http://localhost:5000')
                
                if port_open:
                    self.root.after(0, self.add_status, "Сервер запущен. Браузер открыт.", "info")
                else:
                    self.root.after(0, self.add_status, "Сервер запущен. Браузер открыт (сервер может еще загружаться).", "info")
                
                self.root.after(0, self.add_status, "Для остановки сервера нажмите кнопку 'Завершить работу'", "info")
            
            threading.Thread(target=wait_and_open, daemon=True).start()
            
        except Exception as e:
            self.add_status(f"ОШИБКА при запуске сервера: {str(e)}", "error")
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.start_button.pack(fill=tk.X, pady=(0, 10))
            self.stop_button.pack_forget()
    
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
            self.start_button.pack(fill=tk.X, pady=(0, 10))
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

