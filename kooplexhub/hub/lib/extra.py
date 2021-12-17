import threading
import logging

from kooplexhub.lib import now

from ..models import Background

logger = logging.getLogger(__name__)

def background(f):
    def wrapper(*args, **kwargs):
        user = None
        try:
            #TODO: hard to read this kind of code
            # shall we check object type?
            if hasattr(args[0], 'creator'):
                user = args[0].creator
        except:
            pass
        def worker():
            error = None
            try:
                logger.info('started thread for {}(args = {}, kwargs = {})'.format(f.__name__, args, kwargs))
                if user is None:
                    b = Background.objects.create(function = f.__name__)
                else:
                    b = Background.objects.create(function = f.__name__, user = user)
                f(*args, **kwargs)
            except Exception as e:
                error = e
                logger.debug('error in thread for {}(args = {}, kwargs = {}) -- {}'.format(f.__name__, args, kwargs, e))
            finally:
                logger.info('stopped thread for {}(args = {}, kwargs = {})'.format(f.__name__, args, kwargs))
                if error is not None:
                    b.error = str(error)
                    b.error_at = now()
                    b.save()
                else:
                    b.delete()
        p = threading.Thread(target = worker)
        p.start()
    return wrapper


