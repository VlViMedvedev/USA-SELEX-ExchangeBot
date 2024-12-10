import os
import socket
from ftplib import FTP, error_perm
from logger import logger
from config_reader import ConfigReader
import asyncio


class FTPHandler:
    def __init__(self):
        # Чтение конфигурации
        config = ConfigReader().read_config()
        self.host = config["FTP"]["host"]
        self.username = config["FTP"]["username"]
        self.password = config["FTP"]["password"]
        self.remote_path = config["FTP"]["remote_path"]
        self.archive_path = config["FTP"]["archive_path"]
        self.local_input_path = config["Paths"]["local_input_path"]
        self.ftp = None
        self.max_retries = 3  # Максимальное количество попыток подключения
        self.check_interval_minutes = int(config["General"]["check_interval_minutes"])

    async def connect(self):
        """Устанавливает соединение с FTP-сервером."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Попытка подключения к FTP-серверу ({attempt}/{self.max_retries}): {self.host}")

                # Проверяем доступность хоста
                if not self.is_host_reachable(self.host):
                    logger.warning(f"Хост {self.host}:21 недоступен. Попытка {attempt} не удалась.")
                    continue

                # Устанавливаем соединение
                self.ftp = FTP(timeout=30)  # Тайм-аут 30 секунд
                self.ftp.connect(self.host)
                self.ftp.login(user=self.username, passwd=self.password)
                self.ftp.cwd(self.remote_path)
                logger.info("Успешное подключение к FTP-серверу и переход в удалённую папку.")
                return  # Успешное подключение
            except TimeoutError:
                logger.error(f"Попытка {attempt}: Превышено время ожидания подключения к FTP-серверу.")
            except Exception as e:
                logger.error(f"Попытка {attempt}: Ошибка подключения к FTP-серверу: {e}")

            # Ожидание перед следующей попыткой
            await asyncio.sleep(5)

        # Если все попытки исчерпаны, фиксируем ошибку, но не выбрасываем её
        logger.error(f"Не удалось подключиться к FTP-серверу {self.host} после {self.max_retries} попыток.")
        self.ftp = None  # Убедимся, что объект FTP сброшен

    def is_host_reachable(self, host, port=21):
        """Проверяет, доступен ли FTP-сервер."""
        try:
            logger.info(f"Проверка доступности хоста {host}:{port}...")
            with socket.create_connection((host, port), timeout=10):
                logger.info(f"Хост {host}:{port} доступен.")
                return True
        except (socket.timeout, socket.error) as e:
            logger.warning(f"Хост {host}:{port} недоступен: {e}")
            return False

    async def find_and_download_files(self):
        """
        Ищет файлы на FTP, загружает их в локальную папку и возвращает True, если файлы найдены.
        """
        if not self.ftp:
            await self.connect()

        try:
            logger.info("Поиск файлов на FTP...")

            # Убедимся, что мы в правильной директории
            self.ftp.cwd(self.remote_path)
            logger.info(f"Текущая рабочая директория: {self.ftp.pwd()}")

            # Создание локальной папки, если она не существует
            if not os.path.exists(self.local_input_path):
                os.makedirs(self.local_input_path)
                logger.info(f"Локальная папка {self.local_input_path} создана.")

            # Получение списка файлов на FTP
            files = self.ftp.nlst()
            logger.info(f"Список файлов в текущей директории: {files}")
            dat_files = [file for file in files if file.endswith(".dat")]

            if not dat_files:
                logger.info("На FTP нет новых файлов для загрузки.")
                return False

            for file in dat_files:
                local_file_path = os.path.join(self.local_input_path, file)
                logger.info(f"Загрузка файла {file} в {local_file_path}...")
                with open(local_file_path, "wb") as local_file:
                    self.ftp.retrbinary(f"RETR {file}", local_file.write)
                logger.info(f"Файл {file} успешно загружен в {local_file_path}.")

            return True
        except error_perm as e:
            logger.error(f"Ошибка доступа к файлам на FTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при загрузке файлов с FTP: {e}")
            return False
        finally:
            await self.disconnect()

    async def disconnect(self):
        """Закрывает соединение с FTP-сервером."""
        if not self.ftp:
            logger.warning("Соединение с FTP уже закрыто или не установлено.")
            return

        try:
            self.ftp.quit()
            self.ftp = None
            logger.info("Соединение с FTP-сервером закрыто.")
        except Exception as e:
            logger.error(f"Ошибка при завершении соединения с FTP: {e}")

    def create_folder(self, folder):
        """Создаёт папку на FTP-сервере, используя абсолютные пути."""
        parts = folder.strip("/").split("/")
        current_path = "/"

        for part in parts:
            current_path = f"{current_path}/{part}".strip("/")
            try:
                logger.info(f"Проверяем существование папки: /{current_path}")
                self.ftp.cwd(f"/{current_path}")
                logger.info(f"Папка /{current_path} уже существует.")
            except error_perm:
                try:
                    logger.info(f"Создаём папку: /{current_path}")
                    self.ftp.mkd(f"/{current_path}")
                    logger.info(f"Папка /{current_path} успешно создана.")
                except error_perm as e:
                    logger.error(f"Не удалось создать папку /{current_path}: {e}")
                    break
        # Возвращаемся в remote_path для продолжения работы
        self.ftp.cwd(self.remote_path)
        logger.info(f"Возвращение в рабочую директорию: {self.remote_path}")

    async def archive_downloaded_files(self):
        """Перемещает обработанные файлы *.dat на FTP в папку архива."""
        if not self.ftp:
            await self.connect()

        try:
            logger.info("Архивация обработанных файлов...")

            # Убедимся, что архивная папка существует
            self.create_folder(self.archive_path)

            # Получаем список файлов в текущей директории
            files = self.ftp.nlst()
            dat_files = [file for file in files if file.endswith(".dat")]

            if not dat_files:
                logger.info("Нет файлов для архивации.")
                return

            for file in dat_files:
                try:
                    source_path = f"{self.remote_path}/{file}"
                    target_path = f"{self.archive_path}/{file}"

                    logger.info(f"Перемещение файла {file} в архив {self.archive_path}...")
                    self.ftp.rename(source_path, target_path)
                    logger.info(f"Файл {file} успешно перемещён в {self.archive_path}.")
                except Exception as e:
                    logger.error(f"Не удалось переместить файл {file} в архив: {e}")
        except Exception as e:
            logger.error(f"Ошибка при архивации файлов: {e}")
        finally:
            await self.disconnect()
			