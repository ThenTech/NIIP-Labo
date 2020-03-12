################
# Thread wrapper
try:
    from threading import Thread, Lock, get_ident
    mupy = False
except:
    import _thread
    mupy = True

class Threading:
    @staticmethod
    def new_thread(func, args):
        """
        Create and start a new thread.
        """
        if mupy:
            return _thread.start_new_thread(func, args)
        else:
            tr = Thread(target=func, args=args)
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
        if mupy:
            return _thread.allocate_lock()
        else:
            return Lock()

    @staticmethod
    def get_current_id():
        """Get the current thread id"""
        return _thread.get_ident() if mupy else \
               get_ident()
