import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, scrolledtext, filedialog
import uuid

BLOCKS_FILE = 'blocks_config.json'


class BlockEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор блоков TurtCD")
        self.root.geometry("1200x800")

        # данные: структура { "categories": [ {id,name,color,collapsed,blocks:[{...}]}, ... ] }
        self.blocks_config = {"categories": []}
        
        # текущий файл конфигурации
        self.current_config_file = BLOCKS_FILE

        # текущие выбранные id ( строки id )
        self.current_category_id = None
        self.current_block_id = None

        # структура для виджетов полей: список словарей с конкретными виджет-ссылками
        self.field_widgets = []

        self.load_config()
        self.create_widgets()
        self.load_tree()
        self.update_window_title()

    # ---------- загрузка/сохранение ----------
    def load_config(self):
        """Загрузка конфигурации блоков из файла"""
        try:
            if os.path.exists(self.current_config_file):
                with open(self.current_config_file, 'r', encoding='utf-8') as f:
                    self.blocks_config = json.load(f)
            else:
                # пример начальной конфигурации
                self.blocks_config = {
                    "categories": [
                        {
                            "id": "main",
                            "name": "Основные",
                            "color": "#3498db",
                            "collapsed": False,
                            "blocks": [
                                {
                                    "id": "start",
                                    "name": "Начало",
                                    "type": "header",
                                    "color": "#2196F3",
                                    "fields": [],
                                    "code": "print(\"Программа начата\")\n",
                                    "width": 150,
                                    "height": 60
                                }
                            ]
                        }
                    ]
                }
                self.save_config()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки конфигурации: {e}")
            self.blocks_config = {"categories": []}

    def save_config(self):
        """Сохранение конфигурации блоков в файл"""
        try:
            with open(self.current_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.blocks_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")
            return False

    # ---------- UI ----------
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Изменили с 1 на 2, так как добавили панель файлов
        
        # Панель управления файлами
        file_frame = ttk.LabelFrame(main_frame, text="Управление файлом конфигурации", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # Текущий файл
        ttk.Label(file_frame, text="Текущий файл:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.current_file_label = ttk.Label(file_frame, text=self.current_config_file, foreground="blue")
        self.current_file_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Кнопки управления файлами
        file_buttons = ttk.Frame(file_frame)
        file_buttons.grid(row=0, column=2, sticky=tk.E)
        
        ttk.Button(file_buttons, text="📁 Открыть файл", command=self.open_config_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_buttons, text="💾 Сохранить как", command=self.save_config_as).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_buttons, text="🆕 Новый файл", command=self.new_config_file).pack(side=tk.LEFT, padx=2)

        # левая панель
        left_frame = ttk.LabelFrame(main_frame, text="Существующие блоки", padding="5")
        left_frame.grid(row=1, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        # дерево категорий и блоков
        self.tree = ttk.Treeview(left_frame, show='tree')
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # кнопки управления деревом
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(btn_frame, text="➕ Добавить категорию", command=self.add_category_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➕ Добавить блок (в выбранную)", command=self.add_block_to_selected_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="❌ Удалить", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        
        # Кнопки перемещения
        move_frame = ttk.Frame(left_frame)
        move_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(move_frame, text="⬆️ Вверх", command=self.move_item_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(move_frame, text="⬇️ Вниз", command=self.move_item_down).pack(side=tk.LEFT, padx=2)

        # правая панель - редактирование (динамическая)
        right_frame = ttk.LabelFrame(main_frame, text="Редактирование", padding="5")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        # area для динамической формы
        self.form_area = ttk.Frame(right_frame)
        self.form_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # поля ввода (специальная секция)
        fields_frame = ttk.LabelFrame(main_frame, text="Поля (для формы блока)", padding="5")
        fields_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        fields_frame.columnconfigure(0, weight=1)
        self.fields_container = ttk.Frame(fields_frame)
        self.fields_container.grid(row=0, column=0, sticky=(tk.W, tk.E))
        # кнопки для полей (внизу формы блока появится кнопка "Добавить поле" тоже)
        # но сделаем и глобальную кнопку для удобства:
        ttk.Button(fields_frame, text="➕ Добавить поле", command=self.add_field).grid(row=1, column=0, sticky=tk.W, pady=6)

        # информационная панель внизу
        bottom_frame = ttk.LabelFrame(main_frame, text="Инструкция", padding="5")
        bottom_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(8, 0))
        bottom_frame.columnconfigure(0, weight=1)
        instruction_text = (
            "Для использования значений из полей ввода в коде блока:\n"
            "• Создайте поле ввода с уникальным именем (например: variable_name)\n"
            "• В коде блока используйте {variable_name} там, где должно быть подставлено значение\n"
            "• При компиляции {variable_name} будет заменено на значение из поля ввода\n\n"
            "Пример:\nПоле: variable_name = \"count\"\nКод: print(\"{variable_name}\")\nРезультат: print(\"count\")"
        )
        instruction = scrolledtext.ScrolledText(bottom_frame, height=6, wrap=tk.WORD)
        instruction.insert(tk.END, instruction_text)
        instruction.config(state=tk.DISABLED)
        instruction.grid(row=0, column=0, sticky=(tk.W, tk.E))

    # ---------- дерево ----------
    def load_tree(self):
        """Загрузить дерево категорий и блоков"""
        self.tree.delete(*self.tree.get_children())
        for category in self.blocks_config.get('categories', []):
            # id категории в values
            cat_item = self.tree.insert('', 'end', text=category.get('name', '(unnamed)'), values=('category', category.get('id')))
            for block in category.get('blocks', []):
                # block values: ('block', block_id, category_id)
                self.tree.insert(cat_item, 'end', text=block.get('name', '(blk)'), values=('block', block.get('id'), category.get('id')))
        # expand all categories for convenience
        for iid in self.tree.get_children():
            self.tree.item(iid, open=True)

    # ---------- события выбора ----------
    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return
        v0 = vals[0]
        if v0 == 'category':
            cat_id = vals[1]
            self.current_category_id = cat_id
            self.current_block_id = None
            self.render_category_form(cat_id)
        elif v0 == 'block':
            block_id = vals[1]
            cat_id = vals[2]
            self.current_category_id = cat_id
            self.current_block_id = block_id
            self.render_block_form(cat_id, block_id)

    # ---------- формы ----------
    def render_category_form(self, category_id):
        """Показать форму редактирования категории"""
        self.clear_form()
        cat = self.find_category_by_id(category_id)
        if not cat:
            return
        # fields: name, id (read-only), color, collapsed
        ttk.Label(self.form_area, text="ID категории:").grid(row=0, column=0, sticky=tk.W, pady=4)
        id_entry = ttk.Entry(self.form_area)
        id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        id_entry.insert(0, cat.get('id', ''))
        id_entry.config(state='readonly')

        ttk.Label(self.form_area, text="Название категории:").grid(row=1, column=0, sticky=tk.W, pady=4)
        name_entry = ttk.Entry(self.form_area)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        name_entry.insert(0, cat.get('name', ''))

        ttk.Label(self.form_area, text="Цвет:").grid(row=2, column=0, sticky=tk.W, pady=4)
        color_frame = ttk.Frame(self.form_area)
        color_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        color_entry = ttk.Entry(color_frame)
        color_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        color_entry.insert(0, cat.get('color', '#3498db'))
        ttk.Button(color_frame, text="Выбрать", command=lambda: self.choose_color_dialog(color_entry)).pack(side=tk.LEFT, padx=4)

        ttk.Label(self.form_area, text="Свернута (collapsed):").grid(row=3, column=0, sticky=tk.W, pady=4)
        collapsed_combo = ttk.Combobox(self.form_area, values=['false', 'true'], state='readonly', width=10)
        collapsed_combo.grid(row=3, column=1, sticky=tk.W)
        collapsed_combo.set(str(cat.get('collapsed', False)).lower())

        def save_cat():
            cat['name'] = name_entry.get().strip() or cat['name']
            cat['color'] = color_entry.get().strip() or cat.get('color', '#3498db')
            cat['collapsed'] = (collapsed_combo.get() == 'true')
            if self.save_config():
                messagebox.showinfo("Сохранено", "Категория сохранена")
                self.load_tree()

        ttk.Button(self.form_area, text="💾 Сохранить категорию", command=save_cat).grid(row=4, column=1, sticky=tk.W, pady=8)

    def render_block_form(self, category_id, block_id):
        """Показать форму для редактирования блока"""
        self.clear_form()
        block, cat = self.find_block_and_category(category_id, block_id)
        if not block or not cat:
            return

        # ID (read-only)
        ttk.Label(self.form_area, text="ID блока:").grid(row=0, column=0, sticky=tk.W, pady=2)
        id_entry = ttk.Entry(self.form_area)
        id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        id_entry.insert(0, block.get('id', ''))
        id_entry.config(state='readonly')

        # Название
        ttk.Label(self.form_area, text="Название:").grid(row=1, column=0, sticky=tk.W, pady=2)
        name_entry = ttk.Entry(self.form_area)
        name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        name_entry.insert(0, block.get('name', ''))

        # Тип
        ttk.Label(self.form_area, text="Тип:").grid(row=2, column=0, sticky=tk.W, pady=2)
        type_combo = ttk.Combobox(self.form_area, values=["classic", "condition", "header", "loop"], state="readonly")
        type_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        type_combo.set(block.get('type', 'classic'))

        # Категория (выпадающий список — позволяет сменить группу)
        ttk.Label(self.form_area, text="Категория:").grid(row=3, column=0, sticky=tk.W, pady=2)
        categories_names = [c.get('name', '') for c in self.blocks_config.get('categories', [])]
        self.category_combo = ttk.Combobox(self.form_area, values=categories_names, state='readonly')
        self.category_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2)
        # установить имя текущей категории
        self.category_combo.set(cat.get('name', ''))

        # Цвет
        ttk.Label(self.form_area, text="Цвет:").grid(row=4, column=0, sticky=tk.W, pady=2)
        color_frame = ttk.Frame(self.form_area)
        color_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=2)
        color_entry = ttk.Entry(color_frame)
        color_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        color_entry.insert(0, block.get('color', '#FF9800'))
        ttk.Button(color_frame, text="Выбрать", command=lambda: self.choose_color_dialog(color_entry)).pack(side=tk.LEFT, padx=(6, 0))

        # Код (многострочный) + кнопки вставки/очистки
        ttk.Label(self.form_area, text="Код:").grid(row=5, column=0, sticky=tk.W, pady=2)
        code_text = scrolledtext.ScrolledText(self.form_area, height=8, width=60)
        code_text.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=2)
        code_text.insert(1.0, block.get('code', ''))

        code_btns = ttk.Frame(self.form_area)
        code_btns.grid(row=6, column=1, sticky=tk.W, pady=4)
        ttk.Button(code_btns, text="📋 Вставить из буфера", command=lambda: self.paste_from_clipboard_into(code_text)).pack(side=tk.LEFT, padx=3)
        ttk.Button(code_btns, text="🧹 Очистить", command=lambda: code_text.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=3)

        # Поля: сначала очистим контейнер, затем добавим поля как виджеты
        self.clear_fields()
        for f in block.get('fields', []):
            self.add_field(field_data=f)

        # Кнопка добавить поле прямо в форме блока
        add_field_btn = ttk.Button(self.form_area, text="➕ Добавить поле", command=lambda: self.add_field())
        add_field_btn.grid(row=7, column=1, sticky=tk.W, pady=6)

        # Сохранение блока
        def save_block_action():
            # прочитать поля
            fields = self.get_fields_data()
            # построить структуру блока
            new_block = {
                'id': block.get('id'),
                'name': name_entry.get().strip() or block.get('name'),
                'type': type_combo.get() or block.get('type', 'classic'),
                'color': color_entry.get().strip() or block.get('color', '#FF9800'),
                'code': code_text.get('1.0', tk.END),
                'fields': fields,
                'width': block.get('width', 180),
                'height': block.get('height', 80)
            }

            # определить целевую категорию по имени комбобокса
            target_cat_name = self.category_combo.get()
            target_cat = self.find_category_by_name(target_cat_name)
            if not target_cat:
                messagebox.showerror("Ошибка", "Выберите корректную категорию (группу) для блока")
                return

            # удалить блок из текущей категории (если есть)
            removed = False
            for cat in self.blocks_config.get('categories', []):
                before_count = len(cat.get('blocks', []))
                cat['blocks'] = [b for b in cat.get('blocks', []) if b.get('id') != new_block['id']]
                after_count = len(cat.get('blocks', []))
                if before_count != after_count:
                    removed = True

            # добавить/вставить в целевую категорию
            target_cat.setdefault('blocks', [])
            # если блок с таким id уже есть в target (плохой случай), заменим его
            replaced = False
            for i, ex in enumerate(target_cat['blocks']):
                if ex.get('id') == new_block['id']:
                    target_cat['blocks'][i] = new_block
                    replaced = True
                    break
            if not replaced:
                target_cat['blocks'].append(new_block)

            # обновим текущыe id и дерево
            self.current_category_id = target_cat.get('id')
            self.current_block_id = new_block.get('id')
            if self.save_config():
                messagebox.showinfo("Сохранено", "Блок сохранён")
                self.load_tree()
                # Восстанавливаем выделение после перезагрузки дерева
                self.restore_selection()

        ttk.Button(self.form_area, text="💾 Сохранить блок", command=save_block_action).grid(row=8, column=1, sticky=tk.W, pady=8)

    def clear_form(self):
        for w in self.form_area.winfo_children():
            w.destroy()
        self.clear_fields()

    # ---------- поля ввода (управление) ----------
    def add_field(self, field_data=None):
        """
        Добавляет поле ввода в fields_container.
        Храним ссылку на виджеты в структуре для корректного чтения/удаления.
        """
        # Frame for one field
        frame = ttk.Frame(self.fields_container)
        frame.pack(fill=tk.X, pady=3, padx=3)

        # widgets
        ttk.Label(frame, text="Имя:").pack(side=tk.LEFT, padx=2)
        name_e = ttk.Entry(frame, width=15)
        name_e.pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="Подпись:").pack(side=tk.LEFT, padx=2)
        label_e = ttk.Entry(frame, width=15)
        label_e.pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="Тип:").pack(side=tk.LEFT, padx=2)
        type_c = ttk.Combobox(frame, values=["text", "number", "value"], width=8, state='readonly')
        type_c.pack(side=tk.LEFT, padx=2)
        type_c.set("text")

        ttk.Label(frame, text="Обязательное:").pack(side=tk.LEFT, padx=2)
        required_var = tk.BooleanVar(value=False)
        required_cb = ttk.Checkbutton(frame, variable=required_var)
        required_cb.pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="Подсказка:").pack(side=tk.LEFT, padx=2)
        placeholder_e = ttk.Entry(frame, width=18)
        placeholder_e.pack(side=tk.LEFT, padx=2)

        # Delete and optionally paste placeholders
        delete_btn = ttk.Button(frame, text="🗑", width=3, command=lambda: self._remove_field_widget(field_struct))
        delete_btn.pack(side=tk.RIGHT, padx=2)

        # Optionally fill with provided field_data
        if field_data:
            name_e.insert(0, field_data.get('name', ''))
            label_e.insert(0, field_data.get('label', ''))
            type_c.set(field_data.get('type', 'text'))
            required_var.set(bool(field_data.get('required', False)))
            placeholder_e.insert(0, field_data.get('placeholder', ''))

        # store struct
        field_struct = {
            'frame': frame,
            'name': name_e,
            'label': label_e,
            'type': type_c,
            'required_var': required_var,
            'required_cb': required_cb,
            'placeholder': placeholder_e,
            'delete_btn': delete_btn
        }
        self.field_widgets.append(field_struct)

    def _remove_field_widget(self, field_struct):
        """Удаление конкретного поля и удаления из списка виджетов"""
        try:
            # destroy frame
            field_struct['frame'].destroy()
            # remove from list
            if field_struct in self.field_widgets:
                self.field_widgets.remove(field_struct)
        except Exception:
            pass

    def clear_fields(self):
        """Удалить все виджеты полей"""
        for fs in list(self.field_widgets):
            try:
                fs['frame'].destroy()
            except Exception:
                pass
        self.field_widgets = []

    def get_fields_data(self):
        """Собирает данные из field_widgets и возвращает список dict"""
        out = []
        for fs in self.field_widgets:
            # Guard: ensure widgets still exist
            try:
                name = fs['name'].get().strip()
                if not name:
                    continue  # имя обязательно
                label = fs['label'].get().strip()
                ftype = fs['type'].get() or 'text'
                required = bool(fs['required_var'].get())
                placeholder = fs['placeholder'].get().strip()
                out.append({
                    'name': name,
                    'label': label,
                    'type': ftype,
                    'required': required,
                    'placeholder': placeholder
                })
            except Exception:
                # если виджет удалён или невалиден — пропускаем
                continue
        return out

    # ---------- вспомогательные ----------
    def find_category_by_id(self, cid):
        for cat in self.blocks_config.get('categories', []):
            if cat.get('id') == cid:
                return cat
        return None

    def find_category_by_name(self, name):
        for cat in self.blocks_config.get('categories', []):
            if cat.get('name') == name:
                return cat
        return None

    def find_block_and_category(self, category_id, block_id):
        cat = self.find_category_by_id(category_id)
        if not cat:
            return None, None
        for blk in cat.get('blocks', []):
            if blk.get('id') == block_id:
                return blk, cat
        return None, cat

    # ---------- color helpers ----------
    def choose_color_dialog(self, entry_widget):
        color = colorchooser.askcolor(initialcolor=entry_widget.get())
        if color and color[1]:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, color[1])

    # ---------- paste clipboard ----------
    def paste_from_clipboard_into(self, text_widget):
        try:
            txt = self.root.clipboard_get()
            if txt:
                text_widget.insert(tk.END, txt)
        except tk.TclError:
            messagebox.showerror("Ошибка", "Буфер обмена пуст или недоступен")

    # ---------- управление категориями/блоками ----------
    def add_category_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить категорию")
        dialog.geometry("420x220")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="ID категории:").pack(pady=6, anchor=tk.W, padx=12)
        id_entry = ttk.Entry(dialog)
        id_entry.pack(fill=tk.X, padx=12)
        id_entry.insert(0, f"category_{uuid.uuid4().hex[:8]}")

        ttk.Label(dialog, text="Название категории:").pack(pady=6, anchor=tk.W, padx=12)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(fill=tk.X, padx=12)
        name_entry.insert(0, "Новая категория")

        ttk.Label(dialog, text="Цвет:").pack(pady=6, anchor=tk.W, padx=12)
        color_frame = ttk.Frame(dialog)
        color_frame.pack(fill=tk.X, padx=12)
        color_entry = ttk.Entry(color_frame)
        color_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        color_entry.insert(0, "#3498db")
        ttk.Button(color_frame, text="Выбрать", command=lambda: self.choose_color_dialog(color_entry)).pack(side=tk.LEFT, padx=6)

        def save_cat():
            cid = id_entry.get().strip()
            name = name_entry.get().strip()
            color = color_entry.get().strip()
            if not cid or not name:
                messagebox.showerror("Ошибка", "ID и имя категории обязательны")
                return
            # проверка уникальности id
            if self.find_category_by_id(cid):
                messagebox.showerror("Ошибка", "Категория с таким ID уже существует")
                return
            self.blocks_config.setdefault('categories', []).append({
                'id': cid,
                'name': name,
                'color': color or '#3498db',
                'collapsed': False,
                'blocks': []
            })
            if self.save_config():
                messagebox.showinfo("Готово", "Категория добавлена")
                self.load_tree()
                dialog.destroy()

        ttk.Button(dialog, text="Сохранить", command=save_cat).pack(pady=12)

    def add_block_to_selected_category(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Выбор", "Выберите категорию в дереве или создайте её")
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals or vals[0] != 'category':
            messagebox.showwarning("Выбор", "Выберите категорию (корневой элемент) для добавления блока")
            return
        cat_id = vals[1]
        cat = self.find_category_by_id(cat_id)
        if not cat:
            messagebox.showerror("Ошибка", "Категория не найдена")
            return
        # create new block with unique id
        new_id = f"block_{uuid.uuid4().hex[:8]}"
        new_block = {
            'id': new_id,
            'name': 'Новый блок',
            'type': 'action',
            'color': '#FF9800',
            'fields': [],
            'code': '',
            'width': 180,
            'height': 80
        }
        cat.setdefault('blocks', []).append(new_block)
        if self.save_config():
            messagebox.showinfo("Готово", "Блок добавлен в категорию")
            self.load_tree()

    def delete_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return
        if vals[0] == 'category':
            # удалить категорию
            if messagebox.askyesno("Подтвердите", "Удалить категорию и все её блоки?"):
                cid = vals[1]
                self.blocks_config['categories'] = [c for c in self.blocks_config.get('categories', []) if c.get('id') != cid]
                if self.save_config():
                    self.load_tree()
                    self.clear_form()
        elif vals[0] == 'block':
            if messagebox.askyesno("Подтвердите", "Удалить блок?"):
                bid = vals[1]
                cid = vals[2]
                cat = self.find_category_by_id(cid)
                if cat:
                    cat['blocks'] = [b for b in cat.get('blocks', []) if b.get('id') != bid]
                    if self.save_config():
                        self.load_tree()
                        self.clear_form()

    # ---------- управление файлами конфигурации ----------
    def open_config_file(self):
        """Открыть существующий файл конфигурации"""
        file_path = filedialog.askopenfilename(
            title="Открыть файл конфигурации",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
            initialdir=os.getcwd()
        )
        if file_path:
            self.current_config_file = file_path
            self.current_file_label.config(text=self.current_config_file)
            self.update_window_title()
            self.load_config()
            self.load_tree()
            self.clear_form()
            messagebox.showinfo("Файл открыт", f"Загружен файл: {os.path.basename(file_path)}")

    def save_config_as(self):
        """Сохранить конфигурацию в новый файл"""
        file_path = filedialog.asksaveasfilename(
            title="Сохранить файл конфигурации как",
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
            initialdir=os.getcwd()
        )
        if file_path:
            old_file = self.current_config_file
            self.current_config_file = file_path
            if self.save_config():
                self.current_file_label.config(text=self.current_config_file)
                self.update_window_title()
                messagebox.showinfo("Файл сохранен", f"Конфигурация сохранена в: {os.path.basename(file_path)}")
            else:
                self.current_config_file = old_file

    def new_config_file(self):
        """Создать новый файл конфигурации"""
        if messagebox.askyesno("Новый файл", "Создать новый файл конфигурации? Текущие изменения будут потеряны."):
            file_path = filedialog.asksaveasfilename(
                title="Создать новый файл конфигурации",
                defaultextension=".json",
                filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
                initialdir=os.getcwd()
            )
            if file_path:
                # Создаем новую пустую конфигурацию
                self.blocks_config = {"categories": []}
                self.current_config_file = file_path
                self.current_file_label.config(text=self.current_config_file)
                self.update_window_title()
                self.save_config()
                self.load_tree()
                self.clear_form()
                messagebox.showinfo("Новый файл", f"Создан новый файл: {os.path.basename(file_path)}")

    def update_window_title(self):
        """Обновить заголовок окна с именем текущего файла"""
        filename = os.path.basename(self.current_config_file)
        self.root.title(f"Редактор блоков TurtCD - {filename}")

    def restore_selection(self):
        """Восстановить выделение после перезагрузки дерева"""
        if self.current_category_id and self.current_block_id:
            # Ищем и выделяем блок
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == 'category':
                    cat_id = self.tree.item(item, 'values')[1]
                    if cat_id == self.current_category_id:
                        # Ищем блок в этой категории
                        for child in self.tree.get_children(item):
                            if self.tree.item(child, 'values')[0] == 'block':
                                block_id = self.tree.item(child, 'values')[1]
                                if block_id == self.current_block_id:
                                    self.tree.selection_set(child)
                                    self.tree.see(child)
                                    return
        elif self.current_category_id:
            # Ищем и выделяем категорию
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == 'category':
                    cat_id = self.tree.item(item, 'values')[1]
                    if cat_id == self.current_category_id:
                        self.tree.selection_set(item)
                        self.tree.see(item)
                        return

    def move_item_up(self):
        """Переместить выбранный элемент вверх"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Выбор", "Выберите элемент для перемещения")
            return
        
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return
        
        if vals[0] == 'category':
            # Перемещаем категорию
            cat_id = vals[1]
            categories = self.blocks_config.get('categories', [])
            for i, cat in enumerate(categories):
                if cat.get('id') == cat_id:
                    if i > 0:
                        # Меняем местами с предыдущей
                        categories[i], categories[i-1] = categories[i-1], categories[i]
                        if self.save_config():
                            self.load_tree()
                            self.restore_selection()
                        break
        
        elif vals[0] == 'block':
            # Перемещаем блок
            block_id = vals[1]
            cat_id = vals[2]
            cat = self.find_category_by_id(cat_id)
            if cat and cat.get('blocks'):
                blocks = cat['blocks']
                for i, block in enumerate(blocks):
                    if block.get('id') == block_id:
                        if i > 0:
                            # Меняем местами с предыдущим
                            blocks[i], blocks[i-1] = blocks[i-1], blocks[i]
                            if self.save_config():
                                self.load_tree()
                                self.restore_selection()
                            break

    def move_item_down(self):
        """Переместить выбранный элемент вниз"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Выбор", "Выберите элемент для перемещения")
            return
        
        item = self.tree.item(sel[0])
        vals = item.get('values', [])
        if not vals:
            return
        
        if vals[0] == 'category':
            # Перемещаем категорию
            cat_id = vals[1]
            categories = self.blocks_config.get('categories', [])
            for i, cat in enumerate(categories):
                if cat.get('id') == cat_id:
                    if i < len(categories) - 1:
                        # Меняем местами со следующей
                        categories[i], categories[i+1] = categories[i+1], categories[i]
                        if self.save_config():
                            self.load_tree()
                            self.restore_selection()
                        break
        
        elif vals[0] == 'block':
            # Перемещаем блок
            block_id = vals[1]
            cat_id = vals[2]
            cat = self.find_category_by_id(cat_id)
            if cat and cat.get('blocks'):
                blocks = cat['blocks']
                for i, block in enumerate(blocks):
                    if block.get('id') == block_id:
                        if i < len(blocks) - 1:
                            # Меняем местами со следующим
                            blocks[i], blocks[i+1] = blocks[i+1], blocks[i]
                            if self.save_config():
                                self.load_tree()
                                self.restore_selection()
                            break

    # ---------- полезные методы ----------
    def find_category_index_by_id(self, cid):
        for i, c in enumerate(self.blocks_config.get('categories', [])):
            if c.get('id') == cid:
                return i
        return -1

    # ---------- запуск ----------
def main():
    root = tk.Tk()
    app = BlockEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
