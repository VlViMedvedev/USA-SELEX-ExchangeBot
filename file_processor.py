import os
import asyncio
from configparser import ConfigParser
import subprocess
from logger import logger


class FileProcessor:
    def __init__(self):
        config = self._read_config()
        self.local_input_path = config.get("Paths", "local_input_path", fallback="./data/incoming")
        self.sdexch_exe_path = config.get("Paths", "sdexch_exe_path", fallback="D:/Sel2/sdexch1c/sdexch1c.exe")

    def _read_config(self):
        """Читает настройки из config.ini."""
        config = ConfigParser()
        config.read("config.ini", encoding="utf-8")
        return config
    
    async def process_files(self):
        """Запускает обработку файлов через внешний exe-файл."""
        if not os.path.exists(self.sdexch_exe_path):
            logger.error(f"Утилита обработки не найдена: {self.sdexch_exe_path}")
            return

        if not os.path.exists(self.local_input_path):
            logger.error(f"Путь к локальной папке с файлами не найден: {self.local_input_path}")
            return

        if not self._has_dat_files():
            logger.info("Нет файлов .dat для обработки.")
            return

        logger.info(f"Начинается обработка файлов через утилиту: {self.sdexch_exe_path}")

        try:
            await self._run_sdexch_tool()
            logger.info("Все файлы успешно обработаны.")
        except Exception as e:
            logger.error(f"Ошибка при запуске обработки файлов: {e}")

    def _has_dat_files(self):
        """Проверяет, есть ли файлы .dat в папке local_input_path."""
        dat_files = [f for f in os.listdir(self.local_input_path) if f.endswith(".dat")]
        if dat_files:
            logger.info(f"Обнаружено {len(dat_files)} файл(ов) .dat для обработки в {self.local_input_path}.")
        return bool(dat_files)

    async def _run_sdexch_tool(self):
        """Запускает sdexch1c.exe с локальной папкой как аргумент."""
        command = [self.sdexch_exe_path, self.local_input_path]
    
        # Запуск внешнего процесса
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
        stdout, stderr = await process.communicate()
    
        # Пробуем декодировать вывод с кодировкой cp1251
        stdout_decoded = stdout.decode('cp1251', errors='replace')
        stderr_decoded = stderr.decode('cp1251', errors='replace')
    
        if process.returncode == 0:
            logger.info(f"Обработка завершена успешно. Лог: {stdout_decoded.strip()}")
        else:
            logger.error(f"Обработка завершилась с ошибкой. Код: {process.returncode}. Ошибка: {stderr_decoded.strip()}")
            raise RuntimeError(f"Обработка завершилась с ошибкой: {stderr_decoded.strip()}")
    