import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from config_reader import ConfigReader
from logger import logger


class Notifier:
    def __init__(self):
        config = ConfigReader().read_config()
        self.recipients = [email.strip() for email in config.get("Email", "recipients", fallback="").split(",")]
        self.sender_email = "eshmo@yandex.ru"
        self.sender_password = "vfmcpjwqrcvpsinu"
        self.smtp_server = "smtp.yandex.ru"
        self.smtp_port = 587

    def send_batch_email(self, problematic_files):
        """
        Отправка одного email с перечислением всех проблемных файлов.
        :param problematic_files: список кортежей (dat_file, [warning_files])
        """
        if not self.recipients:
            logger.warning("Список получателей пуст. Письмо не отправлено.")
            return

        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"Обмен УСА с СЕЛЭКС: Отказы и предупреждения — {current_date}"

        # Формируем тело письма
        body = "Уважаемые коллеги,\n\n"
        body += "Ниже приведён список проблемных файлов, обнаруженных при обмене УСА с СЕЛЭКС:\n\n"

        for dat_file, warning_files in problematic_files:
            body += f"- Основной файл: {os.path.basename(dat_file)}\n"
            if warning_files:
                body += "  Связанные файлы:\n"
                for warning_file in warning_files:
                    body += f"    - {os.path.basename(warning_file)}\n"
            else:
                body += "  Связанных файлов нет.\n"
        body += "\nПожалуйста, проверьте приложенные файлы.\n\nС уважением,\nАвтоматизированная система обмена УСА."

        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Добавляем вложения
            for dat_file, warning_files in problematic_files:
                if dat_file and os.path.exists(dat_file):
                    with open(dat_file, "rb") as attachment:
                        part = MIMEApplication(attachment.read(), Name=os.path.basename(dat_file))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(dat_file)}"'
                        msg.attach(part)

                if warning_files:
                    for warning_file in warning_files:
                        if os.path.exists(warning_file):
                            with open(warning_file, "rb") as attachment:
                                part = MIMEApplication(attachment.read(), Name=os.path.basename(warning_file))
                                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(warning_file)}"'
                                msg.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
                logger.info("Email успешно отправлен с вложениями.")
        except Exception as e:
            logger.error(f"Ошибка при отправке email: {e}")
