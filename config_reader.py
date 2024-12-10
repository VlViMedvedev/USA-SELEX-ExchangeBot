import configparser
import os
from logger import logger

class ConfigReader:
    def __init__(self):
        self.config_path = "config.ini"

    def read_config(self):
        if not os.path.exists(self.config_path):
            logger.error(f"Файл конфигурации {self.config_path} не найден.")
            raise FileNotFoundError(f"Файл конфигурации {self.config_path} не найден.")

        logger.info(f"Чтение конфигурации из файла {self.config_path}...")
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')

        # Логируем содержимое конфигурации
        logger.info(f"Секции в конфигурации: {config.sections()}")
        if 'Paths' in config:
            logger.info(f"Ключи в секции [Paths]: {dict(config.items('Paths'))}")
        else:
            logger.error("Секция [Paths] отсутствует в конфигурации.")
            raise KeyError("Секция [Paths] отсутствует в config.ini")

        return config
