import asyncio
from ftp_handler import FTPHandler
from process_monitor import ProcessMonitor
from file_processor import FileProcessor
from result_analyzer import ResultAnalyzer
from logger import logger

async def main():
    ftp_handler = FTPHandler()
    process_monitor = ProcessMonitor()
    file_processor = FileProcessor()
    result_analyzer = ResultAnalyzer()

    while True:
        try:
            # Проверяем FTP на наличие новых файлов
            logger.info("Запуск проверки FTP...")
            new_files_found = await ftp_handler.find_and_download_files()

            if new_files_found:
                logger.info("Найдены новые файлы. Запуск процесса обработки...")

                # Проверяем готовность SELEX
                await process_monitor.ensure_selex_ready()

                # Обрабатываем файлы
                await file_processor.process_files()

                # Анализируем результаты (и уведомляем, если есть проблемные файлы)
                await result_analyzer.analyze_results()

                # Загружаем файлы с предупреждениями на FTP
                await result_analyzer.upload_special_files_to_ftp()

                # Архивируем обработанные файлы на FTP
                await ftp_handler.archive_downloaded_files()
            else:
                logger.info("Новых файлов не обнаружено. Ожидание следующего цикла.")

        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")

        # Ждем перед следующей проверкой FTP
        check_interval = ftp_handler.check_interval_minutes * 60
        await asyncio.sleep(check_interval)

if __name__ == "__main__":
    asyncio.run(main())
