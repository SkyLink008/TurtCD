#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Template editor for TurtCD project patterns.
Provides GUI for creating, importing and editing .turtcd templates.
"""

import json
import os
import shutil
import sys
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


def resolve_base_dir():
    """
    Returns root directory of the TurtCD bundle both for source run and frozen exe.
    """
    if getattr(sys, 'frozen', False):
        # When packaged by PyInstaller we want the directory where executable resides
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = resolve_base_dir()
PATTERNS_DIR = BASE_DIR / 'patterns'
MANIFEST_PATH = PATTERNS_DIR / 'templates_manifest.json'
DEFAULT_TEMPLATE = {
    "id": "blank",
    "name": "Пустой проект",
    "description": "Обычный пустой проект",
    "filename": "blank.turtcd"
}


def slugify(text: str) -> str:
    chars = []
    for ch in text.lower():
        if ch.isalnum():
            chars.append(ch)
        elif ch in (' ', '-', '_'):
            chars.append('-')
    slug = ''.join(chars).strip('-')
    return slug or f"template-{uuid.uuid4().hex[:8]}"


def ensure_storage():
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.write_text(json.dumps([DEFAULT_TEMPLATE], ensure_ascii=False, indent=2), encoding='utf-8')
    blank_path = PATTERNS_DIR / DEFAULT_TEMPLATE['filename']
    if not blank_path.exists():
        blank_payload = {
            "blocks": [],
            "connections": [],
            "projectPath": "",
            "createdAt": ""
        }
        blank_path.write_text(json.dumps(blank_payload, ensure_ascii=False, indent=2), encoding='utf-8')


class TemplateEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор шаблонов TurtCD")
        self.root.geometry("1000x640")
        self.root.minsize(900, 560)

        ensure_storage()
        self.templates = []
        self.current_template_id = None

        self.build_ui()
        self.load_manifest()

    def build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, padding=10)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.rowconfigure(1, weight=1)

        ttk.Label(sidebar, text="Шаблоны").grid(row=0, column=0, columnspan=2, pady=(0, 6))

        self.template_list = tk.Listbox(sidebar, width=28, activestyle='dotbox')
        self.template_list.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.template_list.bind("<<ListboxSelect>>", lambda _: self.on_template_select())

        ttk.Button(sidebar, text="Обновить", command=self.load_manifest).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(sidebar, text="Новый", command=self.create_template).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Button(sidebar, text="Импортировать .turtcd", command=self.import_template).grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Button(sidebar, text="Удалить", command=self.delete_template).grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)

        main_area = ttk.Frame(self.root, padding=10)
        main_area.grid(row=0, column=1, sticky="nsew")
        main_area.columnconfigure(1, weight=1)
        main_area.rowconfigure(5, weight=1)

        ttk.Label(main_area, text="ID").grid(row=0, column=0, sticky="w")
        self.id_var = tk.StringVar()
        ttk.Entry(main_area, textvariable=self.id_var, state='readonly').grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(main_area, text="Название").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(main_area, textvariable=self.name_var).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(main_area, text="Описание").grid(row=2, column=0, sticky="nw")
        self.description_text = tk.Text(main_area, height=4, wrap=tk.WORD)
        self.description_text.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(main_area, text="Файл").grid(row=3, column=0, sticky="w")
        self.filename_var = tk.StringVar()
        ttk.Entry(main_area, textvariable=self.filename_var, state='readonly').grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(main_area, text="Содержимое шаблона (.turtcd)").grid(row=4, column=0, columnspan=2, sticky="w")
        self.content_text = tk.Text(main_area, wrap=tk.NONE, font=("Consolas", 10))
        self.content_text.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(4, 0))

        scroll_y = ttk.Scrollbar(main_area, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=5, column=2, sticky="ns")

        self.import_content_button = ttk.Button(main_area, text="Выгрузить .turtcd", command=self.load_content_from_file)
        self.import_content_button.grid(row=6, column=0, columnspan=2, sticky="w", pady=8)

        button_frame = ttk.Frame(main_area)
        button_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=4)
        button_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(button_frame, text="Сохранить", command=self.save_template).grid(row=0, column=0, padx=4)
        ttk.Button(button_frame, text="Открыть папку", command=self.open_in_explorer).grid(row=0, column=1, padx=4)
        ttk.Button(button_frame, text="Сбросить изменения", command=self.reset_current_template).grid(row=0, column=2, padx=4)

        self.status_var = tk.StringVar(value=f"Каталог шаблонов: {PATTERNS_DIR}")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").grid(row=1, column=0, columnspan=2, sticky="ew")

    def set_status(self, text: str):
        self.status_var.set(text)

    def load_manifest(self):
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
            if not isinstance(data, list):
                raise ValueError("Manifest corrupted")
            self.templates = data
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось загрузить manifest: {exc}")
            self.templates = []
        finally:
            if not any(t.get('id') == DEFAULT_TEMPLATE['id'] for t in self.templates):
                self.templates.insert(0, DEFAULT_TEMPLATE.copy())
            self.refresh_listbox()
            self.set_status("Manifest обновлен")

    def refresh_listbox(self):
        self.template_list.delete(0, tk.END)
        for template in self.templates:
            name = template.get('name') or template.get('id')
            self.template_list.insert(tk.END, name)
        if self.templates:
            self.template_list.select_set(0)
            self.on_template_select()

    def find_template(self, template_id):
        for template in self.templates:
            if template.get('id') == template_id:
                return template
        return None

    def on_template_select(self):
        try:
            index = self.template_list.curselection()
            if not index:
                return
            template = self.templates[index[0]]
            self.current_template_id = template.get('id')
            self.id_var.set(template.get('id', ''))
            self.name_var.set(template.get('name', ''))
            self.description_text.delete('1.0', tk.END)
            self.description_text.insert(tk.END, template.get('description', ''))
            self.filename_var.set(template.get('filename', ''))
            self.load_template_content(template)
            self.set_status(f"Выбран шаблон: {template.get('name')}")
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть шаблон: {exc}")

    def load_template_content(self, template):
        self.content_text.delete('1.0', tk.END)
        filename = template.get('filename')
        if not filename:
            return
        template_path = PATTERNS_DIR / filename
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.content_text.insert(tk.END, content)
        else:
            self.content_text.insert(tk.END, json.dumps({
                "blocks": [],
                "connections": [],
                "projectPath": "",
                "createdAt": ""
            }, ensure_ascii=False, indent=2))

    def save_manifest(self):
        try:
            MANIFEST_PATH.write_text(json.dumps(self.templates, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить manifest: {exc}")

    def create_template(self):
        name = simpledialog.askstring("Новый шаблон", "Введите название шаблона:")
        if not name:
            return
        template_id = slugify(name)
        if self.find_template(template_id):
            messagebox.showerror("Ошибка", "Шаблон с таким ID уже существует.")
            return
        filename = f"{template_id}.turtcd"
        new_template = {
            "id": template_id,
            "name": name,
            "description": "",
            "filename": filename
        }
        PATTERNS_DIR.joinpath(filename).write_text(json.dumps({
            "blocks": [],
            "connections": [],
            "projectPath": "",
            "createdAt": ""
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        self.templates.append(new_template)
        self.save_manifest()
        self.refresh_listbox()
        self.set_status("Создан новый шаблон")

    def import_template(self):
        file_path = filedialog.askopenfilename(title="Выберите .turtcd файл", filetypes=[("TurtCD Project", "*.turtcd")])
        if not file_path:
            return
        name = os.path.splitext(os.path.basename(file_path))[0]
        template_id = slugify(name)
        counter = 1
        while self.find_template(template_id):
            template_id = f"{slugify(name)}-{counter}"
            counter += 1
        filename = f"{template_id}.turtcd"
        dest = PATTERNS_DIR / filename
        shutil.copyfile(file_path, dest)
        new_template = {
            "id": template_id,
            "name": name,
            "description": f"Импортировано из {os.path.basename(file_path)}",
            "filename": filename
        }
        self.templates.append(new_template)
        self.save_manifest()
        self.refresh_listbox()
        self.set_status("Шаблон импортирован")

    def delete_template(self):
        if not self.current_template_id or self.current_template_id == DEFAULT_TEMPLATE['id']:
            messagebox.showinfo("Удаление запрещено", "Нельзя удалить шаблон по умолчанию.")
            return
        if not messagebox.askyesno("Удаление", "Удалить выбранный шаблон?"):
            return
        template = self.find_template(self.current_template_id)
        if template:
            file_path = PATTERNS_DIR / template.get('filename', '')
            if file_path.exists():
                file_path.unlink()
            self.templates = [t for t in self.templates if t.get('id') != self.current_template_id]
            self.save_manifest()
            self.refresh_listbox()
            self.set_status("Шаблон удален")

    def save_template(self):
        if not self.current_template_id:
            messagebox.showerror("Ошибка", "Шаблон не выбран.")
            return
        try:
            content = self.content_text.get('1.0', tk.END).strip()
            if not content:
                raise ValueError("Содержимое пустое")
            parsed = json.loads(content)
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Некорректный JSON: {exc}")
            return

        template = self.find_template(self.current_template_id)
        if not template:
            return

        template['name'] = self.name_var.get().strip() or template['id']
        template['description'] = self.description_text.get('1.0', tk.END).strip()
        filename = template.get('filename') or f"{template['id']}.turtcd"
        template['filename'] = filename
        template_path = PATTERNS_DIR / filename
        template_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding='utf-8')
        self.save_manifest()
        self.set_status("Шаблон сохранен")

    def open_in_explorer(self):
        if os.name == 'nt':
            os.startfile(str(PATTERNS_DIR))
        else:
            messagebox.showinfo("Папка", f"Каталог шаблонов: {PATTERNS_DIR}")

    def reset_current_template(self):
        if not self.current_template_id:
            return
        self.on_template_select()
        self.set_status("Изменения сброшены")

    def load_content_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите .turtcd файл",
            filetypes=[("TurtCD Project", "*.turtcd")]
        )
        if not file_path:
            return
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            json.loads(content)  # validate JSON
            self.content_text.delete('1.0', tk.END)
            self.content_text.insert(tk.END, content)
            self.set_status(f"Загружено содержимое из {os.path.basename(file_path)}")
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {exc}")


def main():
    root = tk.Tk()
    app = TemplateEditorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

