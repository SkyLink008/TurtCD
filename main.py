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
LICENSE_FILE_PATH = 'license.txt'
LICENSE_ACCEPT_MARKER = '.turtcd_license.accepted'
REQUIREMENTS_FILE_PATH = 'requirements.txt'
DEFAULT_REQUIREMENTS_SOURCE = os.path.join('static', 'req')

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
    mods_metadata = {}
    if config.get('mod_allow', True):
        mods_folder = 'mods'
        if os.path.exists(mods_folder):
            for filename in os.listdir(mods_folder):
                if filename.endswith('.json'):
                    mod_path = os.path.join(mods_folder, filename)
                    try:
                        with open(mod_path, 'r', encoding='utf-8') as f:
                            mod_config = json.load(f)
                            mod_id = os.path.splitext(filename)[0]
                            mod_name = mod_config.get('name', mod_id)
                            
                            # Сохраняем метаданные модификации, включая лицензию
                            mods_metadata[mod_id] = {
                                'modId': mod_id,
                                'modName': mod_name,
                                'license': mod_config.get('license')
                            }
                            
                            # Merge categories from mod config
                            if 'categories' in mod_config:
                                for cat in mod_config['categories']:
                                    cat.setdefault('modId', mod_id)
                                    cat.setdefault('modName', mod_name)
                                config['categories'].extend(mod_config['categories'])
                    except Exception as e:
                        print(f"Ошибка загрузки мода {filename}: {e}")
    
    # Добавляем метаданные модификаций в конфигурацию
        config['modsMetadata'] = mods_metadata
    else:
        print("Загрузка модов отключена в конфигурации")
    
    return config


PROJECTS_FOLDER = 'projects'
PATTERNS_FOLDER = 'patterns'
os.makedirs(PROJECTS_FOLDER, exist_ok=True)
os.makedirs(PATTERNS_FOLDER, exist_ok=True)

TEMPLATE_MANIFEST_PATH = os.path.join(PATTERNS_FOLDER, 'templates_manifest.json')
DEFAULT_TEMPLATE = {
    "id": "blank",
    "name": "Пустой проект",
    "description": "Обычный пустой проект",
    "filename": "blank.turtcd"
}


def license_marker_path():
    return os.path.abspath(LICENSE_ACCEPT_MARKER)


def is_license_accepted():
    return os.path.exists(license_marker_path())


def mark_license_accepted():
    try:
        marker = license_marker_path()
        with open(marker, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "accepted_at": datetime.utcnow().isoformat() + 'Z',
                "app_version": "1.0"
            }))
        # Make file hidden on Windows
        if os.name == 'nt':
            try:
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(marker, FILE_ATTRIBUTE_HIDDEN)
            except Exception as e:
                print(f"Не удалось скрыть файл маркера лицензии: {e}")
        else:
            try:
                os.chmod(marker, 0o600)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"Ошибка создания маркера лицензии: {e}")
        return False


def read_license_text():
    if not os.path.exists(LICENSE_FILE_PATH):
        return None
    try:
        with open(LICENSE_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Ошибка чтения лицензии: {e}")
        return None


def read_version():
    version_file = 'version'
    if not os.path.exists(version_file):
        return '1.0.0'  # Версия по умолчанию
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            return version if version else '1.0.0'
    except Exception as e:
        print(f"Ошибка чтения версии: {e}")
        return '1.0.0'


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


@app.route('/api/license/status')
def license_status():
    return jsonify({"accepted": is_license_accepted()})


@app.route('/api/license/text')
def license_text():
    text = read_license_text()
    if text is None:
        return jsonify({"status": "error", "message": "Файл license.txt не найден"}), 404
    return jsonify({"status": "success", "text": text})


@app.route('/api/license/accept', methods=['POST'])
def license_accept():
    if mark_license_accepted():
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Не удалось сохранить состояние"}), 500


@app.route('/api/version')
def get_version():
    return jsonify({"status": "success", "version": read_version()})


@app.route('/api/system/requirements', methods=['GET'])
def get_requirements_file():
    try:
        if not os.path.exists(REQUIREMENTS_FILE_PATH):
            return jsonify({"status": "success", "content": ""})
        with open(REQUIREMENTS_FILE_PATH, 'r', encoding='utf-8') as f:
            return jsonify({"status": "success", "content": f.read()})
    except Exception as exc:
        return jsonify({"status": "error", "message": f'Не удалось прочитать requirements.txt: {exc}'}), 500


@app.route('/api/system/requirements', methods=['POST'])
def save_requirements_file():
    data = request.get_json() or {}
    content = data.get('content', '')
    try:
        with open(REQUIREMENTS_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"status": "success"})
    except Exception as exc:
        return jsonify({"status": "error", "message": f'Не удалось сохранить requirements.txt: {exc}'}), 500


@app.route('/api/system/requirements/reset', methods=['POST'])
def reset_requirements_file():
    try:
        if not os.path.exists(DEFAULT_REQUIREMENTS_SOURCE):
            return jsonify({"status": "error", "message": "Файл static/req не найден"}), 404

        with open(DEFAULT_REQUIREMENTS_SOURCE, 'r', encoding='utf-8') as src:
            default_content = src.read()

        with open(REQUIREMENTS_FILE_PATH, 'w', encoding='utf-8') as dst:
            dst.write(default_content)

        return jsonify({"status": "success", "content": default_content})
    except Exception as exc:
        return jsonify({"status": "error", "message": f'Не удалось сбросить requirements.txt: {exc}'}), 500


def _default_template_payload(path_override=''):
    return {
        "blocks": [],
        "connections": [],
        "projectPath": path_override or '',
        "createdAt": datetime.utcnow().isoformat() + 'Z'
    }


def ensure_blank_template():
    blank_path = os.path.join(PATTERNS_FOLDER, DEFAULT_TEMPLATE['filename'])
    if not os.path.exists(blank_path):
        with open(blank_path, 'w', encoding='utf-8') as f:
            json.dump(_default_template_payload(), f, ensure_ascii=False, indent=2)


def load_templates_manifest():
    ensure_blank_template()
    manifest = []
    if os.path.exists(TEMPLATE_MANIFEST_PATH):
        try:
            with open(TEMPLATE_MANIFEST_PATH, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as exc:
            print(f"Ошибка чтения manifest шаблонов: {exc}")
            manifest = []
    if not isinstance(manifest, list):
        manifest = []

    existing_ids = {t.get('id') for t in manifest if isinstance(t, dict)}
    updated = False
    if DEFAULT_TEMPLATE['id'] not in existing_ids:
        manifest.insert(0, DEFAULT_TEMPLATE.copy())
        updated = True

    if updated or not os.path.exists(TEMPLATE_MANIFEST_PATH):
        try:
            with open(TEMPLATE_MANIFEST_PATH, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"Ошибка сохранения manifest шаблонов: {exc}")
    return manifest


def get_template_entry(template_id: str):
    manifest = load_templates_manifest()
    if not template_id:
        template_id = DEFAULT_TEMPLATE['id']
    for template in manifest:
        if template.get('id') == template_id:
            return template
    return DEFAULT_TEMPLATE


def load_template_data(template_id: str, project_path=''):
    template = get_template_entry(template_id)
    template_file = os.path.join(PATTERNS_FOLDER, template.get('filename', ''))
    data = None
    if template_file and os.path.exists(template_file):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Ошибка чтения шаблона {template_id}: {exc}")
    if not isinstance(data, dict):
        data = _default_template_payload(project_path)

    data.setdefault('blocks', [])
    data.setdefault('connections', [])
    data['projectPath'] = project_path or data.get('projectPath', '')
    data['createdAt'] = datetime.utcnow().isoformat() + 'Z'
    return data


@app.route('/api/templates')
def list_templates():
    return jsonify({"status": "success", "templates": load_templates_manifest()})


@app.route('/api/project/save-file', methods=['POST'])
def save_project_file():
    data = request.get_json()
    filename = data.get('filename', '').strip()
    project_data = data.get('project_data')
    template_id = data.get('template_id')
    project_path = ''
    if isinstance(project_data, dict):
        project_path = project_data.get('projectPath', '')
    if not project_path:
        project_path = data.get('project_path', '')
    
    print(f"Received save request: filename={filename}, project_path={project_path}")
    
    if not filename:
        return jsonify({"status": "error", "message": "Имя файла обязательно"})
    if not filename.endswith('.turtcd'):
        filename += '.turtcd'
    
    if not isinstance(project_data, dict) or not project_data:
        project_data = load_template_data(template_id, project_path)
    else:
        project_data.setdefault('blocks', [])
        project_data.setdefault('connections', [])
        project_data['projectPath'] = project_path or project_data.get('projectPath', '')
        project_data['createdAt'] = datetime.utcnow().isoformat() + 'Z'
    
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


def _create_security_wrapper(safe_mode, project_path):
    """Create Python code wrapper that enforces security restrictions"""
    # Escape values for safe insertion into Python code
    safe_mode_str = safe_mode.replace("'", "\\'").replace('"', '\\"')
    project_path_str = (project_path or '').replace("'", "\\'").replace('\\', '\\\\').replace('"', '\\"')
    
    # Get engine directories (where the application runs)
    engine_root = os.path.abspath(os.getcwd())
    projects_folder = os.path.abspath(PROJECTS_FOLDER)
    compiled_folder = os.path.abspath(os.path.join(engine_root, 'compiled'))
    source_folder = os.path.abspath(os.path.join(engine_root, 'source'))
    
    # Escape engine paths
    engine_root_str = engine_root.replace("'", "\\'").replace('\\', '\\\\').replace('"', '\\"')
    projects_folder_str = projects_folder.replace("'", "\\'").replace('\\', '\\\\').replace('"', '\\"')
    compiled_folder_str = compiled_folder.replace("'", "\\'").replace('\\', '\\\\').replace('"', '\\"')
    source_folder_str = source_folder.replace("'", "\\'").replace('\\', '\\\\').replace('"', '\\"')
    
    wrapper = """
import os
import sys
import shutil
from pathlib import Path

# Security mode: {safe_mode}
# Project path: {project_path}

# Store security settings as module-level variables
_safe_mode = '{safe_mode_str}'
_project_path = r'{project_path_str}'
_engine_root = r'{engine_root_str}'
_projects_folder = r'{projects_folder_str}'
_compiled_folder = r'{compiled_folder_str}'
_source_folder = r'{source_folder_str}'

_original_open = open
_original_makedirs = os.makedirs
_original_remove = os.remove
_original_unlink = os.unlink
_original_rmdir = os.rmdir
_original_rmtree = shutil.rmtree
_original_copy = shutil.copy
_original_copy2 = shutil.copy2
_original_move = shutil.move
_original_rename = os.rename

def _is_project_path(filepath):
    '''Check if filepath is within project directory'''
    if not _project_path or not _project_path.strip():
        return False
    try:
        abs_file = os.path.abspath(filepath)
        abs_project = os.path.abspath(_project_path)
        return abs_file.startswith(abs_project)
    except:
        return False

def _is_engine_path(filepath):
    '''Check if filepath is within engine directories'''
    try:
        abs_file = os.path.abspath(filepath)
        abs_engine = os.path.abspath(_engine_root)
        abs_projects = os.path.abspath(_projects_folder)
        abs_compiled = os.path.abspath(_compiled_folder)
        abs_source = os.path.abspath(_source_folder)
        
        # Normalize paths for comparison
        abs_file_norm = os.path.normpath(abs_file)
        abs_engine_norm = os.path.normpath(abs_engine)
        abs_projects_norm = os.path.normpath(abs_projects)
        abs_compiled_norm = os.path.normpath(abs_compiled)
        abs_source_norm = os.path.normpath(abs_source)
        
        # Check if file is in specific engine folders
        if abs_file_norm.startswith(abs_projects_norm) or abs_file_norm.startswith(abs_compiled_norm) or abs_file_norm.startswith(abs_source_norm):
            return True
        
        # Check if it's directly in the root engine directory (where main.py is)
        file_dir = os.path.dirname(abs_file_norm)
        if file_dir == abs_engine_norm:
            return True
        
        # Check for common engine files in root
        engine_files = ['main.py', 'requirements.txt', 'README.md', 'config.py', 'settings.py']
        file_name = os.path.basename(abs_file_norm)
        if file_name in engine_files and file_dir == abs_engine_norm:
            return True
            
        return False
    except:
        return False

def _check_file_access(filepath, operation):
    '''Check if file operation is allowed based on security mode'''
    if _safe_mode == 'full':
        return True  # Full freedom
    
    is_project = _is_project_path(filepath)
    is_engine = _is_engine_path(filepath)
    
    if _safe_mode == 'restricted':
        # Full ban - no file operations
        raise PermissionError(f"Безопасный режим: операция {{operation}} запрещена для пути {{filepath}}")
    
    if _safe_mode == 'limited':
        # Limited - allow only non-project and non-engine files
        if is_project:
            raise PermissionError(f"Безопасный режим: операция {{operation}} запрещена для файлов проекта. Путь: {{filepath}}")
        if is_engine:
            raise PermissionError(f"Безопасный режим: операция {{operation}} запрещена для папок движка. Путь: {{filepath}}")
        return True
    
    return True

# Override file operations
def _secure_open(file, mode='r', *args, **kwargs):
    if 'w' in mode or 'a' in mode or 'x' in mode:
        _check_file_access(file, 'open')
    return _original_open(file, mode, *args, **kwargs)

def _secure_makedirs(name, *args, **kwargs):
    _check_file_access(name, 'makedirs')
    return _original_makedirs(name, *args, **kwargs)

def _secure_remove(path):
    _check_file_access(path, 'remove')
    return _original_remove(path)

def _secure_unlink(path):
    _check_file_access(path, 'unlink')
    return _original_unlink(path)

def _secure_rmdir(path):
    _check_file_access(path, 'rmdir')
    return _original_rmdir(path)

def _secure_rmtree(path, *args, **kwargs):
    _check_file_access(path, 'rmtree')
    return _original_rmtree(path, *args, **kwargs)

def _secure_copy(src, dst, *args, **kwargs):
    _check_file_access(src, 'copy')
    _check_file_access(dst, 'copy')
    return _original_copy(src, dst, *args, **kwargs)

def _secure_copy2(src, dst, *args, **kwargs):
    _check_file_access(src, 'copy2')
    _check_file_access(dst, 'copy2')
    return _original_copy2(src, dst, *args, **kwargs)

def _secure_move(src, dst):
    _check_file_access(src, 'move')
    _check_file_access(dst, 'move')
    return _original_move(src, dst)

def _secure_rename(src, dst):
    _check_file_access(src, 'rename')
    _check_file_access(dst, 'rename')
    return _original_rename(src, dst)

# Replace built-in functions
open = _secure_open
os.makedirs = _secure_makedirs
os.remove = _secure_remove
os.unlink = _secure_unlink
os.rmdir = _secure_rmdir
os.rename = _secure_rename
shutil.rmtree = _secure_rmtree
shutil.copy = _secure_copy
shutil.copy2 = _secure_copy2
shutil.move = _secure_move
""".format(safe_mode=safe_mode_str, project_path=project_path_str, safe_mode_str=safe_mode_str, project_path_str=project_path_str, engine_root_str=engine_root_str, projects_folder_str=projects_folder_str, compiled_folder_str=compiled_folder_str, source_folder_str=source_folder_str)
    return wrapper


@app.route('/api/project/start', methods=['POST'])
def start_project():
    data = request.get_json()
    code = data.get("code", "")
    safe_mode = data.get("safeMode", "restricted")  # full, limited, restricted
    session_id = str(uuid.uuid4())
    try:
        # Get current project path if available
        current_project = data.get("projectName") or request.cookies.get('currentProject') or ''
        project_path = ''
        if current_project:
            project_file = os.path.join(PROJECTS_FOLDER, current_project)
            if os.path.exists(project_file):
                try:
                    with open(project_file, 'r', encoding='utf-8') as pf:
                        project_data = json.load(pf)
                        project_path = project_data.get('projectPath', '')
                except:
                    pass
        
        # Create security wrapper based on safe mode
        security_wrapper = _create_security_wrapper(safe_mode, project_path)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write(security_wrapper)
            f.write("\n# User code starts here\n")
            f.write(code)
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
                    try:
                        ch = p.stdout.read(1)
                        if not ch:
                            break
                        q.put(ch)
                    except (OSError, ValueError, UnicodeDecodeError) as e:
                        # Handle encoding errors, broken pipes, etc.
                        q.put(f"\n[Ошибка чтения вывода: {str(e)}]\n")
                        break
                    except Exception as e:
                        # Catch any other unexpected errors
                        q.put(f"\n[Неожиданная ошибка: {str(e)}]\n")
                        break
            except Exception as e:
                # Final safety net
                try:
                    q.put(f"\n[Критическая ошибка потока: {str(e)}]\n")
                except:
                    pass
            finally:
                try:
                    q.put("__EXIT__")
                except:
                    pass

        t = threading.Thread(target=reader_thread, args=(proc, q), daemon=True)
        t.start()
        sessions[session_id] = {"process": proc, "queue": q}
        return jsonify({"status": "success", "session_id": session_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/project/read/<session_id>')
def read_project(session_id):
    try:
        sess = sessions.get(session_id)
        if not sess:
            return jsonify({"status": "error", "message": "Session not found"})
        q = sess["queue"]
        output = []
        try:
            while not q.empty():
                try:
                    output.append(q.get(timeout=0.1))
                except queue.Empty:
                    break
                except Exception as e:
                    # Handle any errors while reading from queue
                    output.append(f"\n[Ошибка чтения очереди: {str(e)}]\n")
                    break
        except Exception as e:
            # Handle errors in queue operations
            return jsonify({"status": "error", "message": f"Ошибка чтения: {str(e)}"})
        return jsonify({"status": "success", "output": "".join(output)})
    except Exception as e:
        # Final safety net - server should never crash
        return jsonify({"status": "error", "message": f"Внутренняя ошибка: {str(e)}"})


@app.route('/api/project/write/<session_id>', methods=['POST'])
def write_project(session_id):
    try:
        sess = sessions.get(session_id)
        if not sess:
            return jsonify({"status": "error", "message": "Session not found"})
        data = request.get_json()
        text = data.get("text", "") + "\n"
        try:
            proc = sess["process"]
            if proc.poll() is None:
                try:
                    proc.stdin.write(text)
                    proc.stdin.flush()
                    return jsonify({"status": "success"})
                except (BrokenPipeError, OSError, ValueError) as e:
                    # Handle broken pipes, closed streams, etc.
                    return jsonify({"status": "error", "message": f"Ошибка записи: {str(e)}"})
            else:
                return jsonify({"status": "error", "message": "Process finished"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Ошибка процесса: {str(e)}"})
    except Exception as e:
        # Final safety net
        return jsonify({"status": "error", "message": f"Внутренняя ошибка: {str(e)}"})


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