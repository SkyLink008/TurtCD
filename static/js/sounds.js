/* ========== Sound system ========== */
let soundVolume = 100; // Громкость по умолчанию
let volumeLoaded = false;
const PREV_VOLUME_KEY = 'turtcd_prev_volume'; // Ключ для хранения предыдущего значения громкости

// Загрузка настроек громкости через API
async function loadSoundVolume() {
  if (volumeLoaded) return soundVolume;
  
  try {
    const response = await fetch('/api/sound/volume');
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        soundVolume = data.volume || 100;
        // Ограничиваем значение от 0 до 100
        soundVolume = Math.max(0, Math.min(100, soundVolume));
        
        // Если громкость 0 (звук выключен), но нет сохраненного предыдущего значения,
        // сохраняем текущее значение 0 как предыдущее (чтобы при включении было 100)
        if (soundVolume === 0) {
          const prevVolume = localStorage.getItem(PREV_VOLUME_KEY);
          if (prevVolume === null) {
            // Если предыдущее значение не сохранено, значит звук был выключен вручную
            // При включении используем значение по умолчанию 100
            localStorage.setItem(PREV_VOLUME_KEY, '100');
          }
        } else {
          // Если звук включен, обновляем сохраненное предыдущее значение
          // (на случай, если пользователь изменил громкость вручную)
          localStorage.setItem(PREV_VOLUME_KEY, soundVolume.toString());
        }
      } else {
        soundVolume = 100;
        localStorage.setItem(PREV_VOLUME_KEY, '100');
      }
    } else {
      // Если запрос не удался, используем значение по умолчанию
      soundVolume = 100;
      localStorage.setItem(PREV_VOLUME_KEY, '100');
    }
  } catch (e) {
    // Если произошла ошибка, используем значение по умолчанию
    soundVolume = 100;
    localStorage.setItem(PREV_VOLUME_KEY, '100');
  }
  
  volumeLoaded = true;
  updateSoundButton();
  return soundVolume;
}

// Сохранение настроек громкости через API
async function saveSoundVolume(volume) {
  try {
    const response = await fetch('/api/sound/volume', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ volume: volume })
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        soundVolume = data.volume || volume;
        soundVolume = Math.max(0, Math.min(100, soundVolume));
        
        // Если громкость не 0, обновляем сохраненное предыдущее значение
        // (чтобы при следующем выключении/включении использовалось актуальное значение)
        if (soundVolume > 0) {
          localStorage.setItem(PREV_VOLUME_KEY, soundVolume.toString());
        }
        
        updateSoundButton();
        return true;
      }
    }
    return false;
  } catch (e) {
    console.error('Ошибка сохранения громкости:', e);
    return false;
  }
}

// Переключение беззвучного режима
async function toggleSound() {
  await loadSoundVolume(); // Убеждаемся, что громкость загружена
  
  if (soundVolume > 0) {
    // Выключаем звук: сохраняем текущее значение и устанавливаем 0
    localStorage.setItem(PREV_VOLUME_KEY, soundVolume.toString());
    await saveSoundVolume(0);
  } else {
    // Включаем звук: восстанавливаем предыдущее значение или используем 100
    const prevVolume = localStorage.getItem(PREV_VOLUME_KEY);
    let volumeToRestore = 100; // Значение по умолчанию
    
    if (prevVolume !== null) {
      const prevVol = parseInt(prevVolume, 10);
      if (prevVol > 0 && prevVol <= 100) {
        volumeToRestore = prevVol;
      }
    }
    
    // Восстанавливаем громкость
    await saveSoundVolume(volumeToRestore);
    // Значение остается в localStorage для следующего выключения/включения
  }
}

// Обновление внешнего вида кнопки звука
function updateSoundButton() {
  const btn = document.getElementById('soundToggleBtn');
  const icon = document.getElementById('soundIcon');
  
  if (btn && icon) {
    if (soundVolume === 0) {
      icon.textContent = '🔇';
      btn.classList.add('muted');
      btn.title = 'Включить звук';
    } else {
      icon.textContent = '🔊';
      btn.classList.remove('muted');
      btn.title = 'Выключить звук';
    }
  }
}

function playSound(soundName) {
  if (!soundName) return;
  
  // Если громкость 0, не воспроизводим звук
  if (soundVolume === 0) return;
  
  try {
    // Пробуем разные форматы
    const formats = ['mp3', 'wav', 'ogg'];
    const volume = Math.max(0, Math.min(1, soundVolume / 100));
    
    for (const format of formats) {
      const soundPath = `/static/sound/${soundName}.${format}`;
      const audio = new Audio(soundPath);
      
      // Устанавливаем громкость
      audio.volume = volume;
      
      // Обработчик успешной загрузки
      const playAudio = () => {
        audio.volume = volume;
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch(() => {
            // Игнорируем ошибки воспроизведения (например, если звук отключен в браузере)
          });
        }
      };
      
      // Пробуем воспроизвести когда файл готов
      audio.addEventListener('canplay', playAudio, { once: true });
      audio.addEventListener('canplaythrough', playAudio, { once: true });
      
      // Обработчик ошибки загрузки
      audio.addEventListener('error', () => {
        // Файл не найден, пробуем следующий формат
      }, { once: true });
      
      // Загружаем файл
      audio.load();
      
      // Если файл уже загружен, воспроизводим сразу
      if (audio.readyState >= 2) {
        playAudio();
        return;
      }
      
      // Если файл начал загружаться, используем его
      if (audio.readyState >= 1) {
        return;
      }
    }
  } catch (e) {
    // Игнорируем ошибки воспроизведения звука
  }
}

function playButtonSound(buttonType = 'click') {
  // Убеждаемся, что громкость загружена
  if (!volumeLoaded) {
    loadSoundVolume();
  }
  
  let soundName = 'button_click';
  
  if (buttonType === 'primary') {
    soundName = 'button_click_primary';
  } else if (buttonType === 'ghost') {
    soundName = 'button_click_ghost';
  } else if (buttonType === 'toggle') {
    soundName = 'button_toggle';
  }
  
  playSound(soundName);
}

// Глобальный обработчик звуков для кнопок
document.addEventListener('click', (e) => {
  const target = e.target;
  
  // Пропускаем переключатели модификаций (у них уже есть свой обработчик)
  if (target.closest('#modsPanel label')) {
    return;
  }
  
  // Проверяем, является ли элемент кнопкой или находится внутри кнопки
  const button = target.closest('button, .btn, .btn-ghost, .btn-icon');
  
  if (button) {
    // Определяем тип кнопки
    if (button.classList.contains('btn') || button.classList.contains('btn-icon')) {
      // Основные кнопки
      playButtonSound('primary');
    } else if (button.classList.contains('btn-ghost')) {
      // Вторичные кнопки
      playButtonSound('ghost');
    } else {
      // Обычные кнопки
      playButtonSound('click');
    }
  }
  
  // Обработка чекбоксов и переключателей (кроме модификаций)
  if (target.type === 'checkbox' && !target.closest('#modsPanel')) {
    playButtonSound('toggle');
  }
}, true); // Используем capture phase для раннего перехвата

// Делаем функции доступными глобально
window.toggleSound = toggleSound;
window.loadSoundVolume = loadSoundVolume;
window.saveSoundVolume = saveSoundVolume;
window.updateSoundButton = updateSoundButton;

// Загружаем настройки громкости при загрузке страницы
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', async () => {
    await loadSoundVolume();
  });
} else {
  loadSoundVolume();
}

