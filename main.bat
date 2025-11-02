@echo off
chcp 65001 >nul
title Python Flask Setup

echo [INFO] Проверка наличия Python на компьютере...

:: Проверяем наличие Python в системе
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Python обнаружен в системе.
    goto INSTALL_FLASK
) else (
    echo [INFO] Python не найден в PATH. Проверяем альтернативные варианты...
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [SUCCESS] Python обнаружен через py launcher.
        goto INSTALL_FLASK
    ) else (
        echo [INFO] Python не найден. Устанавливаем через winget...
        goto INSTALL_PYTHON
    )
)

:INSTALL_PYTHON
echo [INFO] Установка Python через winget...
winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 (
    echo [WARNING] Ошибка при установке Python через winget. Пробуем альтернативный метод...
    winget install Python.Python.3.11
)

:: Проверяем успешность установки
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Ошибка: Python не удалось установить автоматически.
        echo [INFO] Пожалуйста, установите Python вручную с https://python.org
        pause
        exit /b 1
    )
)

echo [SUCCESS] Python успешно установлен.

:INSTALL_FLASK
echo [INFO] Установка Flask через pip...
pip install flask telebot pyinstaller flask_socketio
if %errorlevel% neq 0 (
    echo [WARNING] Ошибка при установке Flask. Пробуем с привилегиями администратора...
    pip install --user flask cryptography psutil pyinstaller
)

:: Проверяем установку Flask
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Предупреждение: Flask может быть не установлен корректно.
) else (
    echo [SUCCESS] Flask успешно установлен.
)

:START_APP
echo [INFO] Запуск приложения...
python main.py
if %errorlevel% neq 0 (
    echo [WARNING] Ошибка при запуске через python. Пробуем py launcher...
    py main.py
    if %errorlevel% neq 0 (
        echo [ERROR] Ошибка при запуске main.py
        echo [INFO] Проверьте наличие файла main.py в текущей директории.
        pause
    )
)

exit /b 0