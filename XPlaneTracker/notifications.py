import threading
import logging
import platform

_IS_WINDOWS = platform.system() == "Windows"


def _fire(title: str, message: str):
    if not _IS_WINDOWS:
        return
    try:
        from winotify import Notification
        toast = Notification(app_id="CSABOLANTA", title=title, msg=message, duration="short")
        toast.show()
    except Exception as e:
        logging.warning(f"Notification failed: {e}")


def notify(title: str, message: str):
    threading.Thread(target=_fire, args=(title, message), daemon=True).start()
