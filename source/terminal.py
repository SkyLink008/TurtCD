import json
import cmd
import os
import shlex

class BlockConfigTerminal(cmd.Cmd):
    intro = 'Добро пожаловать в терминал для работы с конфигурационными файлами блоков. Введите help или ? для списка команд.\n'
    prompt = 'block_terminal> '
    
    def __init__(self):
        super().__init__()
        self.open_files = {}  # Словарь для хранения открытых файлов: name -> {data, path}
    
    def do_touch(self, arg):
        """Создать новую пустую конфигурацию: touch <path>"""
        try:
            if not arg:
                print("Ошибка: Укажите путь: touch <path>")
                return
            
            path = arg.strip()
            
            if os.path.exists(path):
                print(f"Ошибка: Файл '{path}' уже существует")
                return
            
            # Создаем пустую конфигурацию
            empty_config = {
                "categories": []
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(empty_config, f, ensure_ascii=False, indent=2)
            
            print(f"Создан новый конфигурационный файл: {path}")
            
        except Exception as e:
            print(f"Ошибка при создании файла: {e}")
    
    def do_open(self, arg):
        """Открыть конфигурационный файл: open <path> as <name>"""
        try:
            args = shlex.split(arg)
            if len(args) != 3 or args[1] != 'as':
                print("Ошибка: Используйте формат: open <path> as <name>")
                return
            
            path, name = args[0], args[2]
            
            if not os.path.exists(path):
                print(f"Ошибка: Файл '{path}' не существует")
                return
            
            if name in self.open_files:
                print(f"Ошибка: Файл с именем '{name}' уже открыт")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.open_files[name] = {'data': data, 'path': path}
            print(f"Файл '{path}' успешно открыт под именем '{name}'")
            
        except json.JSONDecodeError:
            print("Ошибка: Некорректный JSON формат файла")
        except Exception as e:
            print(f"Ошибка при открытии файла: {e}")
    
    def do_show(self, arg):
        """Показать блок или группу: show group|block <id> from <name>"""
        try:
            args = shlex.split(arg)
            if len(args) != 4 or args[2] != 'from':
                print("Ошибка: Используйте формат: show group|block <id> from <name>")
                return
            
            obj_type, obj_id, name = args[0], args[1], args[3]
            
            if name not in self.open_files:
                print(f"Ошибка: Файл с именем '{name}' не найден")
                return
            
            if obj_type not in ['group', 'block']:
                print("Ошибка: Тип должен быть 'group' или 'block'")
                return
            
            data = self.open_files[name]['data']
            
            if obj_id == 'all':
                self._show_all(obj_type, data)
            else:
                self._show_single(obj_type, obj_id, data)
                
        except Exception as e:
            print(f"Ошибка: {e}")
    
    def _show_all(self, obj_type, data):
        """Показать все категории или блоки"""
        if obj_type == 'group':
            if 'categories' in data and data['categories']:
                print("\nВсе категории:")
                print("-" * 50)
                for category in data['categories']:
                    blocks_count = len(category.get('blocks', []))
                    print(f"{category['name']} | {category['id']} | блоков: {blocks_count}")
                print()
            else:
                print("Категории не найдены")
        else:  # block
            if 'categories' in data:
                print("\nВсе блоки:")
                print("-" * 70)
                for category in data['categories']:
                    for block in category.get('blocks', []):
                        print(f"{block['name']} | {block['id']} | {category['id']} | {block.get('type', 'нет')}")
                print()
            else:
                print("Блоки не найдены")
    
    def _show_single(self, obj_type, obj_id, data):
        """Показать конкретную категорию или блок"""
        if obj_type == 'group':
            if 'categories' in data:
                for category in data['categories']:
                    if str(category['id']) == obj_id:
                        blocks_count = len(category.get('blocks', []))
                        print(f"\nКатегория найдена:")
                        print(f"Имя категории: {category['name']}")
                        print(f"ID категории: {category['id']}")
                        print(f"Цвет: {category.get('color', 'нет')}")
                        print(f"Свернута: {category.get('collapsed', False)}")
                        print(f"Количество блоков: {blocks_count}\n")
                        return
                print(f"Ошибка: Категория с ID '{obj_id}' не найдена")
            else:
                print("Категории не найдены в файле")
        else:  # block
            if 'categories' in data:
                for category in data['categories']:
                    for block in category.get('blocks', []):
                        if str(block['id']) == obj_id:
                            print(f"\nБлок найден:")
                            print(f"Имя блока: {block['name']}")
                            print(f"ID блока: {block['id']}")
                            print(f"Тип блока: {block.get('type', 'нет')}")
                            print(f"ID категории: {category['id']}")
                            print(f"Цвет: {block.get('color', 'нет')}")
                            print(f"Размер: {block.get('width', '?')}x{block.get('height', '?')}")
                            print(f"Код: {block.get('code', 'нет')}")
                            print(f"Поля: {len(block.get('fields', []))}\n")
                            return
                print(f"Ошибка: Блок с ID '{obj_id}' не найден")
            else:
                print("Блоки не найдены в файле")
    
    def do_rm(self, arg):
        """Удалить группу или блок: rm group|block <id> from <name>"""
        try:
            args = shlex.split(arg)
            if len(args) != 4 or args[2] != 'from':
                print("Ошибка: Используйте формат: rm group|block <id> from <name>")
                return
            
            obj_type, obj_id, name = args[0], args[1], args[3]
            
            if name not in self.open_files:
                print(f"Ошибка: Файл с именем '{name}' не найден")
                return
            
            if obj_type not in ['group', 'block']:
                print("Ошибка: Тип должен быть 'group' или 'block'")
                return
            
            data = self.open_files[name]['data']
            found = False
            
            if obj_type == 'group':
                if 'categories' in data:
                    for i, category in enumerate(data['categories']):
                        if str(category['id']) == obj_id:
                            data['categories'].pop(i)
                            found = True
                            break
            else:  # block
                if 'categories' in data:
                    for category in data['categories']:
                        if 'blocks' in category:
                            for i, block in enumerate(category['blocks']):
                                if str(block['id']) == obj_id:
                                    category['blocks'].pop(i)
                                    found = True
                                    break
                        if found:
                            break
            
            if found:
                print(f"{obj_type.capitalize()} с ID '{obj_id}' успешно удален")
                self._save_file(name)
            else:
                print(f"Ошибка: {obj_type.capitalize()} с ID '{obj_id}' не найден")
                
        except Exception as e:
            print(f"Ошибка: {e}")
    
    def do_copy(self, arg):
        """Скопировать группу: copy group <id> from <name_1> to <name_2>"""
        try:
            args = shlex.split(arg)
            if len(args) != 6:
                print("Ошибка: Используйте формат: copy group <id> from <name_1> to <name_2>")
                return
            
            # Проверяем структуру команды
            if args[0] != 'group' or args[2] != 'from' or args[4] != 'to':
                print("Ошибка: Используйте формат: copy group <id> from <name_1> to <name_2>")
                return
            
            obj_id, name1, name2 = args[1], args[3], args[5]
            
            if name1 not in self.open_files:
                print(f"Ошибка: Файл с именем '{name1}' не найден")
                return
            
            if name2 not in self.open_files:
                print(f"Ошибка: Файл с именем '{name2}' не найден")
                return
            
            source_data = self.open_files[name1]['data']
            target_data = self.open_files[name2]['data']
            
            # Находим категорию для копирования
            category_to_copy = None
            if 'categories' in source_data:
                for category in source_data['categories']:
                    if str(category['id']) == obj_id:
                        category_to_copy = json.loads(json.dumps(category))  # Глубокое копирование
                        break
            
            if not category_to_copy:
                print(f"Ошибка: Категория с ID '{obj_id}' не найдена в файле '{name1}'")
                return
            
            # Проверяем, есть ли уже категория с таким ID в целевом файле
            if 'categories' not in target_data:
                target_data['categories'] = []
            
            for category in target_data['categories']:
                if category['id'] == category_to_copy['id']:
                    print(f"Ошибка: Категория с ID '{obj_id}' уже существует в файле '{name2}'")
                    return
            
            # Копируем категорию вместе с блоками
            target_data['categories'].append(category_to_copy)
            
            print(f"Категория '{category_to_copy['name']}' (ID: {obj_id}) успешно скопирована из '{name1}' в '{name2}'")
            print(f"Скопировано блоков: {len(category_to_copy.get('blocks', []))}")
            self._save_file(name2)
                
        except Exception as e:
            print(f"Ошибка: {e}")
    
    def do_upper(self, arg):
        """Подвинуть группу или блок выше: upper group|block <id> in <name>"""
        self._move_position(arg, 'up')
    
    def do_lower(self, arg):
        """Подвинуть группу или блок ниже: lower group|block <id> in <name>"""
        self._move_position(arg, 'down')
    
    def _move_position(self, arg, direction):
        """Общая функция для перемещения позиции"""
        try:
            args = shlex.split(arg)
            if len(args) != 4 or args[2] != 'in':
                print(f"Ошибка: Используйте формат: {'upper' if direction == 'up' else 'lower'} group|block <id> in <name>")
                return
            
            obj_type, obj_id, name = args[0], args[1], args[3]
            
            if name not in self.open_files:
                print(f"Ошибка: Файл с именем '{name}' не найден")
                return
            
            if obj_type not in ['group', 'block']:
                print("Ошибка: Тип должен быть 'group' или 'block'")
                return
            
            data = self.open_files[name]['data']
            
            if obj_type == 'group':
                if 'categories' not in data or not data['categories']:
                    print("Ошибка: Категории не найдены в файле")
                    return
                
                collection = data['categories']
                index = -1
                
                # Находим индекс категории
                for i, category in enumerate(collection):
                    if str(category['id']) == obj_id:
                        index = i
                        break
                
                if index == -1:
                    print(f"Ошибка: Категория с ID '{obj_id}' не найдена")
                    return
                
                # Перемещаем категорию
                if direction == 'up':
                    if index == 0:
                        print(f"Ошибка: Категория уже на первой позиции")
                        return
                    collection[index], collection[index-1] = collection[index-1], collection[index]
                    print(f"Категория '{collection[index-1]['name']}' перемещена выше")
                else:  # down
                    if index == len(collection) - 1:
                        print(f"Ошибка: Категория уже на последней позиции")
                        return
                    collection[index], collection[index+1] = collection[index+1], collection[index]
                    print(f"Категория '{collection[index+1]['name']}' перемещена ниже")
            
            else:  # block
                if 'categories' not in data:
                    print("Ошибка: Категории не найдены в файле")
                    return
                
                # Находим блок и его категорию
                target_category = None
                block_index = -1
                
                for category in data['categories']:
                    if 'blocks' in category:
                        for i, block in enumerate(category['blocks']):
                            if str(block['id']) == obj_id:
                                target_category = category
                                block_index = i
                                break
                    if target_category:
                        break
                
                if not target_category:
                    print(f"Ошибка: Блок с ID '{obj_id}' не найден")
                    return
                
                blocks = target_category['blocks']
                
                # Перемещаем блок внутри категории
                if direction == 'up':
                    if block_index == 0:
                        print(f"Ошибка: Блок уже на первой позиции в категории")
                        return
                    blocks[block_index], blocks[block_index-1] = blocks[block_index-1], blocks[block_index]
                    print(f"Блок '{blocks[block_index-1]['name']}' перемещен выше")
                else:  # down
                    if block_index == len(blocks) - 1:
                        print(f"Ошибка: Блок уже на последней позиции в категории")
                        return
                    blocks[block_index], blocks[block_index+1] = blocks[block_index+1], blocks[block_index]
                    print(f"Блок '{blocks[block_index+1]['name']}' перемещен ниже")
            
            self._save_file(name)
                
        except Exception as e:
            print(f"Ошибка: {e}")
    
    def do_list(self, arg):
        """Показать все открытые файлы: list"""
        if not self.open_files:
            print("Нет открытых файлов")
            return
        
        print("\nОткрытые файлы:")
        print("-" * 40)
        for name, file_info in self.open_files.items():
            categories_count = len(file_info['data'].get('categories', []))
            blocks_count = 0
            for category in file_info['data'].get('categories', []):
                blocks_count += len(category.get('blocks', []))
            print(f"{name}: {file_info['path']} (категорий: {categories_count}, блоков: {blocks_count})")
        print()
    
    def do_save(self, arg):
        """Сохранить все изменения во всех файлах: save"""
        try:
            for name in self.open_files:
                self._save_file(name)
            print("Все изменения сохранены")
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
    
    def do_save_as(self, arg):
        """Сохранить конкретный файл: save <name> [new_path]"""
        try:
            args = shlex.split(arg)
            if not args:
                print("Ошибка: Укажите имя файла: save <name> [new_path]")
                return
            
            name = args[0]
            new_path = args[1] if len(args) > 1 else None
            
            if name not in self.open_files:
                print(f"Ошибка: Файл с именем '{name}' не найден")
                return
            
            self._save_file(name, new_path)
            if new_path:
                print(f"Файл '{name}' сохранен как '{new_path}'")
            else:
                print(f"Файл '{name}' сохранен")
                
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
    
    def _save_file(self, name, new_path=None):
        """Внутренняя функция для сохранения файла"""
        file_info = self.open_files[name]
        path = new_path or file_info['path']
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(file_info['data'], f, ensure_ascii=False, indent=2)
        
        if new_path:
            file_info['path'] = new_path
    
    def do_exit(self, arg):
        """Выйти из терминала: exit"""
        print("Выход из терминала...")
        return True
    
    def do_EOF(self, arg):
        """Выйти из терминала (Ctrl+D)"""
        return self.do_exit(arg)

def main():
    terminal = BlockConfigTerminal()
    terminal.cmdloop()

if __name__ == '__main__':
    main()