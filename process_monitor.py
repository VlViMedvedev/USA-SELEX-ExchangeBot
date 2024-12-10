import os
import asyncio
import psutil
import tkinter as tk
from configparser import ConfigParser
from logger import logger


class ProcessMonitor:
    def __init__(self):
        config = self._read_config()
        self.selex_path = config.get("Paths", "selex_path", fallback="D:/Sel2/selex/SELEX_W.exe")
        self.local_incoming = config.get("Paths", "local_incoming", fallback="./data/incoming")
        self.window = None

    def _read_config(self):
        """Читает настройки из config.ini."""
        config = ConfigParser()
        config.read("config.ini")
        return config

    async def ensure_selex_ready(self):
        """Проверяет запущенность процесса SELEX и ожидает завершения."""
        logger.info("Проверка процесса СЕЛЭКС...")

        # Проверяем, есть ли файлы .dat в local_incoming
        dat_files = [f for f in os.listdir(self.local_incoming) if f.endswith(".dat")]
        if not dat_files:
            logger.info("Нет файлов .dat для обработки. Проверка процесса СЕЛЭКС не требуется.")
            return

        logger.info(f"Обнаружено {len(dat_files)} файл(ов) .dat для обработки в {self.local_incoming}.")

        # Проверяем, запущен ли процесс SELEX
        while self.is_process_running():
            logger.warning("Процесс SELEX запущен. Ожидание завершения...")
            self.show_window()  # Показываем окно с сообщением
            await asyncio.sleep(180)  # Ждать 3 минуты перед повторной проверкой

        logger.info("Процесс SELEX не запущен. Можно продолжать выполнение программы.")
    
    def is_process_running(self):
        """Проверяет, запущен ли процесс SELEX."""
        logger.info(f"Ищем процесс SELEX по пути: {self.selex_path}")
    
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['exe'] and os.path.normcase(proc.info['exe']) == os.path.normcase(self.selex_path):
                    logger.info(f"Процесс SELEX найден: {proc.info['exe']}")
                    return True
                elif proc.info['name'] == 'SELEX_W.exe':  # Альтернативная проверка по имени
                    logger.warning("Процесс SELEX найден по имени, но путь не совпадает.")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
        logger.info("Процесс SELEX не найден.")
        return False
    
    def show_window(self):
        """Показывает графическое окно с сообщением."""
        if self.window:
            return  # Окно уже показано

        self.window = tk.Tk()
        self.window.title("СЕЛЭКС")
        self.window.geometry("300x150")
        self.window.resizable(False, False)

        label = tk.Label(
            self.window,
            text="Есть файлы для импорта в СЕЛЭКС.\nПожалуйста, закройте ПО СЕЛЭКС.",
            font=("Arial", 12),
            wraplength=280,
            justify="center",
        )
        label.pack(pady=20)

        ok_button = tk.Button(self.window, text="ОК", command=self.hide_window)
        ok_button.pack(pady=10)

        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)  # Закрытие окна
        self.window.mainloop()

    def hide_window(self):
        """Закрывает графическое окно."""
        if self.window:
            self.window.destroy()
            self.window = None
