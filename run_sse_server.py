import sys
import os
import json

# Добавляем директорию src в путь для поиска модулей
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Проверяем и создаем директорию для логов, если её нет
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Создаем конфигурационный файл для Windsurf с использованием SSE
def create_windsurf_config():
    config_path = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
    
    # Полный URL для SSE подключения
    sse_url = "http://localhost:8000/sse"
    
    config = {
        "vegalite": {
            "url": sse_url,
            "outputFormat": "png"
        }
    }
    
    # Создаем директорию, если не существует
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Записываем конфигурацию
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_path, sse_url

# Импортируем сервер
from mcp_server_vegalite import server

if __name__ == "__main__":
    print("Запуск MCP Vega-Lite сервера в режиме SSE...")
    
    # Создаем конфигурационный файл для Windsurf
    config_path, sse_url = create_windsurf_config()
    print(f"SSE сервер будет доступен по адресу: {sse_url}")
    print(f"Конфигурация Windsurf создана в: {config_path}")
    print("Для использования сервера в Windsurf, перезапустите Windsurf.")
    
    # Устанавливаем аргументы командной строки для запуска в режиме SSE
    sys.argv = [
        sys.argv[0],           # Имя скрипта
        "--transport", "sse",  # SSE транспорт
        "--port", "8000",      # Порт 8000
        "--output-type", "png"  # PNG вывод по умолчанию
    ]
    
    try:
        # Запускаем сервер
        print("Запускаем SSE сервер на порту 8000...")
        server.main()
    except KeyboardInterrupt:
        print("\nРабота сервера прервана пользователем")
    except Exception as e:
        print(f"\nОшибка при запуске сервера: {e}")
