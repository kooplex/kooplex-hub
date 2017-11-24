import time
import smtplib
from email.mime.text import MIMEText

#FIXME: how to import this variable?
#from kooplex.lib.settings import KOOPLEX_BASE_URL
KOOPLEX_BASE_URL = "https://kooplex.vo.elte.hu"
SMTP_SERVER = 'mail.elte.hu' #FIXME: hardcoded
FROM_ADDRESS = 'kooplex@complex.elte.hu'


def _send(to, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = FROM_ADDRESS
    msg['To'] = to

    try:
        s = smtplib.SMTP(SMTP_SERVER)
        s.send_message(msg)
        s.quit()
        return 0
    except Exception as e:
        with open('/tmp/email_err.log', 'a') as f:
            f.write('%f to: %s\t%s\n' % (time.time(), to, e))
        return e


def send_new_password(name, username, to, pw):
    # NOTE: make a local copy of the secret for debug purposes
    with open('/tmp/%s' % username, 'w') as f:
        f.write(pw)

    message = """
Dear %s,

your new kooplex account (%s) is created.

The login password is set %s . Please change it the first time you visit the dasboard at %s.

Best regards,
 Kooplex team
    """ % (name, username, pw, KOOPLEX_BASE_URL)

    status = _send(to = to, subject = 'Your kooplex account is created', message = message)
    if status != 0:
        send_error_report(status, 'Error delivering pw (%s) to %s' % (pw, to))

def send_error_report(status, extra = 'na'):
    message = """
Instance: %s
Failure: %s
Extra: %s
    """ % (KOOPLEX_BASE_URL, status, extra)

    _send(to = FROM_ADDRESS, subject = '[SMTP error]', message = message)

def send_token(user, token):
    message = """
Dear %s %s,

a kooplex account password reset request for your account (%s) is issued.

Provide the token %s along with the new password to be set at the dashboard.

Best regards,
 Kooplex team
    """ % (user.first_name, user.last_name, user.username, token)

    status = _send(to = user.email, subject = 'Kooplex account password reset request', message = message)
    if status != 0:
        send_error_report(status, 'Error delivering pw request token (%s) to %s' % (token, user.email))

