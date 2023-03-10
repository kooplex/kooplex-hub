#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

#import time
#from timeloop import Timeloop
#from datetime import timedelta
#
#t = Timeloop()
#@t.job(interval=timedelta(seconds=60)))
#def tick():
#    print ("Tick : {}".format(time.ctime()))

def initialize_debugger():
    import debugpy

    debugpy.listen(("0.0.0.0", 3000))
    debugpy.wait_for_client()
    print('Attached!')

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kooplexhub.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
#    initialize_debugger()
#    try:
#        t.start(block = False)
#    except Exception as e:
#        print (e)
    main()
