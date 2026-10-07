import logging
import time

from app.core.logging import configure_logging
from app.models.notifications import NotificationChannel
from app.workers.notifications import SMTPEmailAdapter, TwilioSMSAdapter, process_notification_batch


def main() -> None:
    configure_logging()
    adapters = {
        NotificationChannel.EMAIL: SMTPEmailAdapter(),
        NotificationChannel.SMS: TwilioSMSAdapter(),
    }
    while True:
        try:
            process_notification_batch(adapters)
        except Exception:
            logging.getLogger(__name__).exception("Notification worker batch failed")
        time.sleep(5)


if __name__ == "__main__":
    main()
