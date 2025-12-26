/* ========== Sound system ========== */
let soundVolume = 100; // Громкость по умолчанию
let volumeLoaded = false;

// Загрузка настроек громкости
async function loadSoundVolume() {
  if (volumeLoaded) return soundVolume;
  
  try {
    const response = await fetch('/static/sound/volume.json');
    if (response.ok) {
      const data = await response.json();
      soundVolume = data.volume || 100;
      // Ограничиваем значение от 0 до 100
      soundVolume = Math.max(0, Math.min(100, soundVolume));
    } else {
      // Если файл не найден, используем значение по умолчанию
      soundVolume = 100;
    }
  } catch (e) {
    // Если файл не найден, используем значение по умолчанию
    soundVolume = 100;
  }
  
  volumeLoaded = true;
  return soundVolume;
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

// Загружаем настройки громкости при загрузке страницы
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    loadSoundVolume();
  });
} else {
  loadSoundVolume();
}

