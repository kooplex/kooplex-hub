import time
import smtplib
from email.mime.text import MIMEText
import logging

from kooplex.lib import get_settings

logger = logging.getLogger(__name__)

def _send(to, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = get_settings('hub', 'adminemail')
    msg['To'] = to

    try:
        s = smtplib.SMTP(get_settings('hub', 'smtpserver'))
        s.send_message(msg)
        s.quit()
        logger.info('mailto: %s [%s]' % (to, subject))
        return 0
    except Exception as e:
        logger.error('mailto: %s [%s]' % (to, subject))
        return 1

def send_new_password(user):
    subject = 'Your kooplex account is created'
    message = """
Dear %s %s,

your new kooplex account (%s) is created.

The login password is set %s . Please change it the first time you visit the dasboard at %s.

Best regards,
 Kooplex team
    """ % (user.first_name, user.last_name, user.username, user.password, get_settings('hub', 'base_url'))

    status = _send(to = user.email, subject = subject, message = message)
    if status != 0:
        send_error_report(status, 'Error delivering pw (%s) to %s' % (user.password, user.email))
    return status

def send_error_report(status, extra = 'na'):
    message = """
Instance: %s
Failure: %s
Extra: %s
    """ % (get_settings('hub', 'base_url'), status, extra)
    _send(to = get_settings('hub', 'adminemail'), subject = '[SMTP error]', message = message)

def send_token(user, token):
    subject = 'Kooplex account password reset request'
    message = """
Dear %s %s,

a kooplex account password reset request for your account (%s) is issued.

Provide the token %s along with the new password to be set in the dashboard.

Best regards,
 Kooplex team
    """ % (user.first_name, user.last_name, user.username, token)

    status = _send(to = user.email, subject = subject, message = message)
    if status != 0:
        send_error_report(status, 'Error delivering pw request token (%s) to %s' % (token, user.email))
    return status

