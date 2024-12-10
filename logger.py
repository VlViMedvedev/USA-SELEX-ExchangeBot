import logging
from logging.handlers import RotatingFileHandler

# Настройка глобального логгера
def setup_logger():
    logger = logging.getLogger("global_logger")
    logger.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Файловый лог с ротацией
    file_handler = RotatingFileHandler(
        "app.log", maxBytes=5_000_000, backupCount=3
    )  # Лимит 5 МБ на файл, сохраняются 3 резервных копии
    file_handler.setFormatter(formatter)

    # Добавляем обработчики в логгер
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Создание глобального логгера
logger = setup_logger()
