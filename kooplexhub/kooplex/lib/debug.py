import datetime as dt
import inspect

def print_debug(debug,msg):
    if debug:
        section = inspect.getouterframes(inspect.currentframe())[1].filename[:-3]
        subsection = inspect.getouterframes(inspect.currentframe())[1].frame.f_code.co_name
        now=dt.datetime.now()
        timestamp="[ %d.%d.%d %d:%d:%d ]"%(now.year,now.month,now.day,now.hour,now.minute,now.second)
        print("DEBUG - %s: %s - %s\t - %s"%(timestamp,section,subsection,msg))
