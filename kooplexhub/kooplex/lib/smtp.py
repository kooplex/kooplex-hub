"""SMTP email backend class."""

from django.core.mail.backends.smtp import EmailBackend as EmailBackendOrig


import smtplib
import socket

from django.utils.encoding import force_str


class EmailBackend(EmailBackendOrig):
    """
    A wrapper that manages the SMTP network connection.
    """

    def open(self):
        """
        Ensure an open connection to the email server. Return whether or not a
        new connection was required (True or False) or None if an exception
        passed silently.
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        # We override the original hostname guess, because pod hostname results mails ending in spam folder
        connection_params = {'local_hostname': 'veo.vo.elte.hu'}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params.update({
                'keyfile': self.ssl_keyfile,
                'certfile': self.ssl_certfile,
            })
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)

            # TLS/SSL are mutually exclusive, so only attempt TLS over
            # non-secure connections.
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(keyfile=self.ssl_keyfile, certfile=self.ssl_certfile)
            if self.username and self.password:
                self.connection.login(force_str(self.username), force_str(self.password))
            return True
        except (smtplib.SMTPException, socket.error):
            if not self.fail_silently:
                raise
