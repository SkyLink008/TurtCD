import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

# Получаем путь к директории, где лежит скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(BASE_DIR, "conf")
TARGET_FILE = os.path.join(BASE_DIR, "blocks_config.json")

# Создаём окно
root = tk.Tk()
root.title("Выбор конфига")
root.geometry("300x120")
root.resizable(False, False)

# Получаем список файлов из папки conf
if not os.path.exists(CONF_DIR):
    os.makedirs(CONF_DIR)

files = [f for f in os.listdir(CONF_DIR) if os.path.isfile(os.path.join(CONF_DIR, f))]

selected_file = tk.StringVar()

# Метка
label = ttk.Label(root, text="Выберите конфиг:")
label.pack(pady=5)

# Выпадающий список
combo = ttk.Combobox(root, textvariable=selected_file, values=files, state="readonly")
combo.pack(pady=5)
if files:
    combo.current(0)

# Функция замены
def replace_config():
    file = selected_file.get()
    if not file:
        messagebox.showwarning("Ошибка", "Не выбран файл")
        return
    
    source = os.path.join(CONF_DIR, file)
    try:
        shutil.copyfile(source, TARGET_FILE)
        messagebox.showinfo("Успех", f"Файл заменён: {file} → blocks_config.json")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

# Кнопка
btn = ttk.Button(root, text="Заменить", command=replace_config)
btn.pack(pady=10)

root.mainloop()