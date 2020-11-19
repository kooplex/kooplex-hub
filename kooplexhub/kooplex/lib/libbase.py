"""
@author: Jozsef Steger
@summary: 
"""
import re
import time
import logging
import subprocess
import shlex
import datetime
import pytz
import unidecode

from django.conf import settings
from django.http import HttpResponseRedirect

from kooplex import settings as kooplex_settings

logger = logging.getLogger(__name__)

local_timezone = pytz.timezone(kooplex_settings.TIME_ZONE if hasattr(kooplex_settings, 'TIME_ZONE') else 'UTC')

def now():
    """
    @summary: returns the current time in a tz-aware datetime format
    """
    return local_timezone.localize(datetime.datetime.now())

def translate_date(d):
    try:
        return local_timezone.localize(datetime.datetime.strptime(d, "%m/%d/%Y %I:%M %p")) if d else None
    except Exception as e:
        logger.warn("Cannot convert date time %s -- %s" % (d, e))
        return None

def human_localtime(d):
    return d.astimezone(local_timezone).strftime('%Y_%m_%d-%H:%M:%S')

def custom_redirect(url_name, *args, **kwargs):
    from django.core.urlresolvers import reverse 
    #import urllib #FIXME
    try:
        url = reverse(url_name, args = args) if args else reverse(url_name)
    except: #FIXME: NoReverseMatch
        url = url_name
    #params = urllib.urlencode(kwargs)
    params = '&'.join(f'{k}={v}' for k, v in kwargs.items())
    return HttpResponseRedirect(url + "?%s" % params) if params else HttpResponseRedirect(url)

def keeptrying(method, times, **kw):
    """
    @summary: run an arbitrary method with keyword arguments. In case an exception is raised during the call, 
    keep trying some more times with exponentially increasing waiting time between consecutive calls.
    @param method: the method to call
    @type method: callable
    @param times: the number of trials
    @type times: int
    @param kw: keyword arguments to pass to the method
    @returns the return value of method
    @raises the last exception if calling th method fails times many times
    """
    dt = .1
    while times > 0:
        logging.debug("executing %s" % method)
        times -= 1
        try:
            return method(**kw)
        except Exception as e:
            logging.warning("exception (%s) while executing %s [backoff and try %d more]" % (method, e, times))
            if times == 0:
                logging.error("gave up execution of %s" % method)
                raise
            time.sleep(dt)
            dt *= 2


def bash(command):
    """
    @summary: run a command as root in the hub container
    @param command: the shell command to run
    @type command: str
    """
    wrap = "bash -c \"%s\""
    logger.info(command)
    subprocess.call(shlex.split(command))


def standardize_str(s):
    '''
    @summary: get rid of tricky characters in a string:
              1. lower the string
              2. keep english letters amd numbers
    @param s: the string to clean
    @type s: str
    @returns: rhe cleaned string
    @raises AssertionError, if not characters are left after cleaning
    '''
    s_clean = "".join(re.split(r'[^0-9a-z]*([a-z0-9]+)[^0-9a-z]*', s.lower()))
    assert len(s_clean), "No characters kept after standardization"
    return s_clean

def deaccent_str(s):
    return unidecode.unidecode(s)
