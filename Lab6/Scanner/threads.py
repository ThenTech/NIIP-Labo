
from threading import Thread, Lock, get_ident

class Threading:
    @staticmethod
    def new_thread(func, args=(), daemon=False):
        """
        Create and start a new thread.
        """
        tr = Thread(target=func, args=args, daemon=False)
        tr.start()
        return tr

    @staticmethod
    def new_lock():
        """
        Return a Mutex lock object.

        Example:
            lock = Threading.new_lock()
            with lock:
                pass
        """
        return Lock()

    @staticmethod
    def get_current_id():
        """Get the current thread id"""
        return get_ident()
