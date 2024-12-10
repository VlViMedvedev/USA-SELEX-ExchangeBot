import os
import shutil
import unidecode
from configparser import ConfigParser
from logger import logger
from ftp_handler import FTPHandler
from notifier import Notifier
import re
import asyncio

class ResultAnalyzer:
    def __init__(self):
        config = self._read_config()
        self.local_input_path = config.get("Paths", "local_input_path", fallback="./data/incoming")
        self.local_archive_path = config.get("Paths", "local_archive_path", fallback="./data/archive")
        self.local_problem_path = config.get("Paths", "local_problem_path", fallback="./data/problems")
        self.ftp_problem_path = config.get("FTP", "problem_path", fallback="/1C_TO_SELEX/problems")
        self.ftp_handler = FTPHandler()
        self.notifier = Notifier()

    def _read_config(self):
        """Читает настройки из config.ini."""
        config = ConfigParser()
        config.read("config.ini")
        return config
    

    
    async def analyze_results(self):
        """Анализирует результаты обработки файлов и отправляет уведомление при необходимости."""
        logger.info("Анализ результатов обработки файлов...")
    
        # Ждем 60 секунд перед анализом
        logger.info("Ожидание 60 секунд для завершения создания всех файлов...")
        await asyncio.sleep(60)
    
        if not os.path.exists(self.local_input_path):
            logger.error(f"Папка с входными файлами не найдена: {self.local_input_path}")
            return
    
        files = os.listdir(self.local_input_path)
        logger.info(f"Найдено {len(files)} файлов в папке {self.local_input_path}: {files}")
        dat_files = [f for f in files if f.endswith(".dat")]
    
        if not dat_files:
            logger.info("Нет файлов для анализа в папке.")
            return
    
        problematic_files = []  # Список кортежей (dat_file, [warning_files])
    
        # Убедимся, что папка для проблемных файлов существует
        os.makedirs(self.local_problem_path, exist_ok=True)
    
        for dat_file in dat_files:
            dat_file_path = os.path.join(self.local_input_path, dat_file)
            logger.info(f"Обработка файла: {dat_file}")
    
            # Основное имя файла без префикса "+"
            base_name = dat_file.lstrip("+")
            logger.info(f"Основное имя файла (без префикса '+'): {base_name}")
    
            # Поиск всех связанных файлов, содержащих основное имя файла
            related_files = [
                os.path.join(self.local_input_path, f)
                for f in files
                if f != dat_file and base_name in f
            ]
            logger.info(f"Найдено связанных файлов для {dat_file}: {related_files}")
    
            # Формируем список проблемных файлов
            if related_files or not dat_file.startswith("+"):
                # Если есть связанные файлы или файл не начинается с "+", считаем его проблемным
                logger.info(f"Файл {dat_file} обработан с ошибками. Перемещаем в папку проблем.")
                new_dat_path = self._move_file(dat_file_path, self.local_problem_path) if os.path.exists(dat_file_path) else None
                new_related_paths = [
                    self._move_file(f, self.local_problem_path) for f in related_files if os.path.exists(f)
                ]
                problematic_files.append((new_dat_path, [p for p in new_related_paths if p]))
            else:
                # Если связанных файлов нет и файл начинается с "+", считаем успешным
                logger.info(f"Файл {dat_file} обработан успешно. Перемещаем в архив.")
                if os.path.exists(dat_file_path):
                    self._move_file(dat_file_path, self.local_archive_path)
    
        # Отправляем уведомление, если есть проблемные файлы
        problematic_files = [(dat, warnings) for dat, warnings in problematic_files if dat]  # Исключаем None
        if problematic_files:
            logger.info(f"Добавлено {len(problematic_files)} проблемных файлов для уведомления.")
            await self._send_problematic_files_email(problematic_files)
        else:
            logger.info("Проблемных файлов не обнаружено, уведомление не отправляется.")
        
        
    
    
    def _move_file(self, file_path, target_folder):
        """Перемещает файл в целевую папку и возвращает новый путь."""
        os.makedirs(target_folder, exist_ok=True)
        target_path = os.path.join(target_folder, os.path.basename(file_path))
        try:
            shutil.move(file_path, target_path)
            logger.info(f"Файл {file_path} перемещен в {target_folder}.")
            return target_path
        except Exception as e:
            logger.error(f"Ошибка при перемещении файла {file_path} в {target_folder}: {e}")
            return None
    
    

    async def _send_problematic_files_email(self, problematic_files):
        """Централизованная отправка письма с проблемными файлами."""
        try:
            self.notifier.send_batch_email(problematic_files)
            logger.info("Письмо с проблемными файлами отправлено успешно.")
        except Exception as e:
            logger.error(f"Ошибка при отправке письма: {e}")

    def _move_file(self, file_path, target_folder):
        """Перемещает файл в целевую папку и возвращает новый путь."""
        os.makedirs(target_folder, exist_ok=True)
        target_path = os.path.join(target_folder, os.path.basename(file_path))
        try:
            shutil.move(file_path, target_path)
            logger.info(f"Файл {file_path} перемещен в {target_folder}.")
            return target_path
        except Exception as e:
            logger.error(f"Ошибка при перемещении файла {file_path} в {target_folder}: {e}")
            return None

    async def upload_special_files_to_ftp(self):
        """Загружает файлы с предупреждениями на FTP и перемещает их в подпапку old после успешной загрузки."""
        logger.info("Загрузка проблемных файлов на FTP...")

        if not os.path.exists(self.local_problem_path):
            logger.warning(f"Папка с проблемными файлами не найдена: {self.local_problem_path}")
            return

        problem_files = os.listdir(self.local_problem_path)
        if not problem_files:
            logger.info("Нет проблемных файлов для загрузки на FTP.")
            return

        old_folder_path = os.path.join(self.local_problem_path, "old")
        os.makedirs(old_folder_path, exist_ok=True)

        await self.ftp_handler.connect()

        try:
            self.ftp_handler.create_folder(self.ftp_problem_path)

            for file in problem_files:
                local_file_path = os.path.join(self.local_problem_path, file)
                transliterated_name = unidecode.unidecode(file)
                remote_file_path = f"{self.ftp_problem_path}/{transliterated_name}"

                if os.path.isfile(local_file_path):
                    logger.info(f"Загрузка файла {file} как {transliterated_name} на FTP: {remote_file_path}...")
                    try:
                        with open(local_file_path, "rb") as f:
                            self.ftp_handler.ftp.storbinary(f"STOR {remote_file_path}", f)
                        logger.info(f"Файл {file} успешно загружен на FTP как {transliterated_name}.")
                        old_file_path = os.path.join(old_folder_path, file)
                        shutil.move(local_file_path, old_file_path)
                        logger.info(f"Файл {file} перемещен в подпапку old после успешной загрузки.")
                    except Exception as e:
                        logger.error(f"Ошибка при загрузке файла {file} на FTP: {e}")
                else:
                    logger.warning(f"{file} не является файлом, пропускаем.")
        finally:
            await self.ftp_handler.disconnect()
