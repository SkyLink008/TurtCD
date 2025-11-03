import json
import os
import sys
import uuid
import subprocess
import tempfile
import threading
import queue
import shutil
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response

app = Flask(__name__)

# Configuration - фиксированные настройки
config = {
    "is_host": True,
    "port": 5000,
    "mod_allow": True
}

BLOCKS_CONFIG_PATH = 'blocks_config.json'

DEFAULT_BLOCKS_CONFIG = {
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
                },
                {
                    "id": "action",
                    "name": "Действие",
                    "type": "classic",
                    "color": "#FF9800",
                    "fields": [
                        {
                            "name": "action_text",
                            "label": "Текст действия",
                            "type": "text",
                            "required": True,
                            "placeholder": "Введите текст"
                        }
                    ],
                    "code": "print(\"{action_text}\")\n",
                    "width": 180,
                    "height": 80
                }
            ]
        }
    ]
}


def load_blocks_config():
    # Load main config
    if os.path.exists(BLOCKS_CONFIG_PATH):
        with open(BLOCKS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = DEFAULT_BLOCKS_CONFIG.copy()
        with open(BLOCKS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    # Ensure core categories have mod metadata
    for cat in config.get('categories', []):
        cat.setdefault('modId', 'core')
        cat.setdefault('modName', 'Основные')

    # Load additional configs from mods folder (if allowed)
    if config.get('mod_allow', True):
        mods_folder = 'mods'
        if os.path.exists(mods_folder):
            for filename in os.listdir(mods_folder):
                if filename.endswith('.json'):
                    mod_path = os.path.join(mods_folder, filename)
                    try:
                        with open(mod_path, 'r', encoding='utf-8') as f:
                            mod_config = json.load(f)
                            # Merge categories from mod config
                            if 'categories' in mod_config:
                                mod_id = os.path.splitext(filename)[0]
                                mod_name = mod_config.get('name', mod_id)
                                for cat in mod_config['categories']:
                                    cat.setdefault('modId', mod_id)
                                    cat.setdefault('modName', mod_name)
                                config['categories'].extend(mod_config['categories'])
                    except Exception as e:
                        print(f"Ошибка загрузки мода {filename}: {e}")
    else:
        print("Загрузка модов отключена в конфигурации")
    
    return config


PROJECTS_FOLDER = 'projects'
os.makedirs(PROJECTS_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return render_template('project_selection.html')


@app.route('/editor')
def editor():
    return render_template('index.html')


@app.route('/compiled.html')
def compiled():
    return render_template('compiled.html')


@app.route('/api/blocks')
def get_blocks():
    return jsonify(load_blocks_config())


@app.route('/api/project/save-file', methods=['POST'])
def save_project_file():
    data = request.get_json()
    filename = data.get('filename', '').strip()
    project_data = data.get('project_data', {})
    project_path = project_data.get('projectPath', '')
    
    print(f"Received save request: filename={filename}, project_path={project_path}")
    
    if not filename:
        return jsonify({"status": "error", "message": "Имя файла обязательно"})
    if not filename.endswith('.turtcd'):
        filename += '.turtcd'
    
    # Всегда сохраняем в папку projects для простоты
    filepath = os.path.join(PROJECTS_FOLDER, filename)
    print(f"Saving to projects folder: {filepath}")
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved project to: {filepath}")
        return jsonify({"status": "success", "filename": filename, "path": filepath})
    except Exception as e:
        print(f"Error saving file: {e}")
        return jsonify({"status": "error", "message": f"Ошибка сохранения: {str(e)}"})


@app.route('/api/project/load-file', methods=['POST'])
def load_project_file():
    data = request.get_json()
    filename = data.get('filename')
    
    # Сначала ищем в папке projects
    filepath = os.path.join(PROJECTS_FOLDER, filename)
    if not os.path.exists(filepath):
        # Если не найден в projects, ищем в других местах
        # Пока что возвращаем ошибку, но в будущем можно расширить поиск
        return jsonify({"status": "error", "message": "Файл не найден"})
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        return jsonify({"status": "success", "project_data": project_data})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка загрузки: {str(e)}"})


@app.route('/api/project/list')
def list_projects():
    try:
        if not os.path.exists(PROJECTS_FOLDER):
            os.makedirs(PROJECTS_FOLDER, exist_ok=True)
            print(f"Created projects folder: {PROJECTS_FOLDER}")
        
        projects = [f for f in os.listdir(PROJECTS_FOLDER) if f.endswith('.turtcd')]
        
        print(f"Found projects: {projects}")
        return jsonify({"status": "success", "projects": projects})
    except Exception as e:
        print(f"Error listing projects: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/delete', methods=['POST'])
def delete_project():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"status": "error", "message": "Имя файла обязательно"})
    
    # Ищем файл в папке projects
    filepath = os.path.join(PROJECTS_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "Файл не найден"})
    
    try:
        os.remove(filepath)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/compile', methods=['POST'])
def compile_project():
    data = request.get_json()
    return jsonify({
        "status": "success",
        "code": generate_python_code(data.get('project_data', {}))
    })


@app.route('/api/project/compile-exe', methods=['POST'])
def compile_exe():
    try:
        # Get form data
        code = request.form.get('code', '')
        exe_name = request.form.get('exe_name', 'program.exe')
        hide_console = request.form.get('hide_console', 'false').lower() == 'true'
        icon_file = request.files.get('icon')
        
        if not code.strip():
            return jsonify({"status": "error", "message": "Код не может быть пустым"})
        
        # Create compiled folder in project directory
        compiled_path = os.path.join(os.getcwd(), 'compiled')
        os.makedirs(compiled_path, exist_ok=True)
        
        def generate_progress():
            try:
                # Step 1: Create temporary Python file
                yield f'data: {{"progress": 10, "status": "Создание временного файла..."}}\n\n'
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(code)
                    temp_py_file = f.name
                
                # Step 2: Install PyInstaller if needed
                yield f'data: {{"progress": 20, "status": "Проверка PyInstaller..."}}\n\n'
                
                try:
                    subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    yield f'data: {{"progress": 25, "status": "Установка PyInstaller..."}}\n\n'
                    subprocess.run(['pip', 'install', 'pyinstaller'], check=True)
                
                # Step 3: Prepare command
                yield f'data: {{"progress": 30, "status": "Подготовка команды..."}}\n\n'
                
                exe_name_clean = exe_name.replace('.exe', '')
                cmd = [
                    'pyinstaller',
                    '--onefile',
                    '--distpath', compiled_path,
                    '--name', exe_name_clean,
                    '--clean'
                ]
                
                if hide_console:
                    cmd.append('--noconsole')
                
                if icon_file:
                    icon_temp = tempfile.NamedTemporaryFile(suffix='.ico', delete=False)
                    icon_file.save(icon_temp.name)
                    cmd.extend(['--icon', icon_temp.name])
                
                cmd.append(temp_py_file)
                
                # Step 4: Run PyInstaller
                yield f'data: {{"progress": 40, "status": "Запуск компиляции..."}}\n\n'
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(temp_py_file)
                )
                
                # Step 5: Check result
                yield f'data: {{"progress": 90, "status": "Проверка результата..."}}\n\n'
                
                exe_path = os.path.join(compiled_path, exe_name_clean + '.exe')
                
                if result.returncode == 0 and os.path.exists(exe_path):
                    yield f'data: {{"progress": 100, "status": "completed", "message": "EXE файл успешно создан!"}}\n\n'
                else:
                    error_msg = result.stderr or result.stdout or "Неизвестная ошибка"
                    yield f'data: {{"status": "error", "message": "Ошибка компиляции: {error_msg[:200]}"}}\n\n'
                
                # Cleanup
                try:
                    os.unlink(temp_py_file)
                    if icon_file:
                        os.unlink(icon_temp.name)
                    # Clean PyInstaller files
                    for item in ['build', '__pycache__', exe_name_clean + '.spec']:
                        if os.path.exists(item):
                            if os.path.isdir(item):
                                shutil.rmtree(item)
                            else:
                                os.unlink(item)
                except:
                    pass
                    
            except Exception as e:
                yield f'data: {{"status": "error", "message": "Ошибка: {str(e)}"}}\n\n'
        
        return Response(generate_progress(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка сервера: {str(e)}"})


@app.route('/api/project/open-compiled-folder', methods=['POST'])
def open_compiled_folder():
    try:
        compiled_path = os.path.join(os.getcwd(), 'compiled')
        
        if not os.path.exists(compiled_path):
            return jsonify({"status": "error", "message": "Папка compiled не найдена"})
        
        # Try to open folder in file explorer
        if os.name == 'nt':  # Windows
            os.startfile(compiled_path)
        elif os.name == 'posix':  # macOS and Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', compiled_path])
        else:
            return jsonify({"status": "error", "message": "Неподдерживаемая операционная система"})
        
        return jsonify({"status": "success", "message": "Папка открыта"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка открытия папки: {str(e)}"})


@app.route('/api/block/duplicate', methods=['POST'])
def duplicate_block():
    data = request.get_json()
    block_data = data.get('block_data', {})
    new_block = block_data.copy()
    new_block['id'] = str(uuid.uuid4())
    new_block['x'] += 20
    new_block['y'] += 20
    return jsonify({"status": "success", "new_block": new_block})


# ===================== Interactive Run =====================
sessions = {}  # session_id -> {"process": Popen, "queue": queue.Queue()}


@app.route('/api/project/start', methods=['POST'])
def start_project():
    data = request.get_json()
    code = data.get("code", "")
    session_id = str(uuid.uuid4())
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n" + code)
            fname = f.name
        
        # Определяем команду Python для Windows
        python_cmd = None
        for cmd in ["python", "py", "python3"]:
            try:
                subprocess.run([cmd, "--version"], capture_output=True, check=True)
                python_cmd = cmd
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if not python_cmd:
            return jsonify({"status": "error", "message": "Python не найден в системе. Установите Python с https://python.org"})
        
        proc = subprocess.Popen(
            [python_cmd, fname],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0  # без буфера
        )
        q = queue.Queue()

        def reader_thread(p, q):
            try:
                while True:
                    ch = p.stdout.read(1)
                    if not ch:
                        break
                    q.put(ch)
            except Exception:
                pass
            q.put("__EXIT__")

        t = threading.Thread(target=reader_thread, args=(proc, q), daemon=True)
        t.start()
        sessions[session_id] = {"process": proc, "queue": q}
        return jsonify({"status": "success", "session_id": session_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/read/<session_id>')
def read_project(session_id):
    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"status": "error", "message": "Session not found"})
    q = sess["queue"]
    output = []
    while not q.empty():
        output.append(q.get())
    return jsonify({"status": "success", "output": "".join(output)})


@app.route('/api/project/write/<session_id>', methods=['POST'])
def write_project(session_id):
    sess = sessions.get(session_id)
    if not sess:
        return jsonify({"status": "error", "message": "Session not found"})
    data = request.get_json()
    text = data.get("text", "") + "\n"
    try:
        proc = sess["process"]
        if proc.poll() is None:
            proc.stdin.write(text)
            proc.stdin.flush()
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Process finished"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/stop/<session_id>', methods=['POST'])
def stop_project(session_id):
    sess = sessions.pop(session_id, None)
    if sess:
        proc = sess["process"]
        if proc.poll() is None:
            proc.kill()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Session not found"})


@app.route('/api/project/update', methods=['POST'])
def update_project():
    try:
        data = request.get_json()
        print(f"Update project request data: {data}")  # Отладочная информация
        
        # Поддерживаем оба варианта имен полей для совместимости
        filename = data.get('filename') or data.get('oldFilename')
        new_name = data.get('new_name') or data.get('newFilename')
        
        print(f"Parsed: filename={filename}, new_name={new_name}")
        
        if not filename:
            return jsonify({"status": "error", "message": "Filename is required"})
        
        filepath = os.path.join(PROJECTS_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({"status": "error", "message": "Project file not found"})
        
        # Загружаем существующие данные проекта
        with open(filepath, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        print(f"Loaded project_data: {project_data}")  # Отладочная информация
        
        # Если нужно переименовать файл
        if new_name and new_name != filename:
            new_filepath = os.path.join(PROJECTS_FOLDER, new_name)
            if os.path.exists(new_filepath):
                return jsonify({"status": "error", "message": "Project with this name already exists"})
            
            # Сохраняем обновленные данные в новый файл
            with open(new_filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            # Удаляем старый файл
            os.remove(filepath)
            
            return jsonify({"status": "success", "message": "Project updated and renamed", "filename": new_name})
        else:
            # Просто обновляем существующий файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            return jsonify({"status": "success", "message": "Project updated"})
            
    except Exception as e:
        print(f"Error updating project: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/duplicate', methods=['POST'])
def duplicate_project():
    try:
        data = request.get_json()
        source_filename = data.get('sourceFilename')
        target_filename = data.get('targetFilename')
        
        if not source_filename or not target_filename:
            return jsonify({"status": "error", "message": "Source and target filenames are required"})
        
        # Добавляем расширение .turtcd если его нет
        if not target_filename.endswith('.turtcd'):
            target_filename += '.turtcd'
        
        source_filepath = os.path.join(PROJECTS_FOLDER, source_filename)
        target_filepath = os.path.join(PROJECTS_FOLDER, target_filename)
        
        if not os.path.exists(source_filepath):
            return jsonify({"status": "error", "message": "Source project not found"})
        
        if os.path.exists(target_filepath):
            return jsonify({"status": "error", "message": "Project with this name already exists"})
        
        # Загружаем исходный проект
        with open(source_filepath, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Обновляем метаданные для копии
        project_data['createdAt'] = datetime.now().isoformat()
        if 'description' in project_data:
            project_data['description'] = project_data['description'] + ' (копия)'
        
        # Сохраняем копию
        with open(target_filepath, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"status": "success", "message": "Project duplicated successfully", "filename": target_filename})
        
    except Exception as e:
        print(f"Error duplicating project: {e}")
        return jsonify({"status": "error", "message": str(e)})


# ===================== Code Generator =====================
def generate_python_code(project):
    if not project or 'blocks' not in project:
        return "# Нет блоков в проекте"

    blocks = {b['id']: b for b in project['blocks']}
    connections = project.get('connections', [])
    outgoing = {}
    for conn in connections:
        outgoing.setdefault(conn['from'], []).append(conn)

    visited, code_lines = set(), []

    def compile_block(block_id, indent=0):
        if block_id in visited:
            return
        visited.add(block_id)
        block = blocks.get(block_id)
        if not block:
            return
        block_cfg = find_block_config(block.get('template'))
        if not block_cfg:
            return
        
        is_ignored = block.get('ignored', False)
        
        code = block_cfg.get('code', '')
        for n, v in block.get('fields', {}).items():
            code = code.replace(f"{{{n}}}", str(v or ""))
        if code.strip():
            # Разбиваем код на строки и применяем отступ к каждой строке
            lines = code.rstrip().split('\n')
            for line in lines:
                if line.strip():  # Добавляем только непустые строки
                    if is_ignored:
                        # Комментируем строки игнорированного блока
                        code_lines.append("    " * indent + "# " + line)
                    else:
                        code_lines.append("    " * indent + line)
        if block_cfg['type'] in ['condition', 'loop']:
            body = next((c for c in outgoing.get(block_id, []) if c['fromConnector'] == 'right'), None)
            if body:
                # Если блок игнорирован, все блоки на правом коннекторе также будут игнорированы
                # и автоматически закомментированы внутри compile_block
                compile_block(body['to'], indent + 1)
            nxt = next((c for c in outgoing.get(block_id, []) if c['fromConnector'] == 'bottom'), None)
            if nxt:
                compile_block(nxt['to'], indent)
        else:
            nxt = next((c for c in outgoing.get(block_id, []) if c['fromConnector'] == 'bottom'), None)
            if nxt:
                compile_block(nxt['to'], indent)

    start = next((b for b in blocks.values() if b['type'] == 'header'), None)
    if start:
        compile_block(start['id'], 0)
    return "\n".join(code_lines)


def find_block_config(template_id):
    cfg = load_blocks_config()
    for cat in cfg.get('categories', []):
        for blk in cat.get('blocks', []):
            if blk.get('id') == template_id:
                return blk
    return None


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    load_blocks_config()
    
    # Get configuration values
    port = config['port']
    is_host = config['is_host']
    host = '0.0.0.0' if is_host else '127.0.0.1'
    
    
    app.run(debug=True, port=port, host=host)
