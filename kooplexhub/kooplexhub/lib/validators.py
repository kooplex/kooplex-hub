from django.core import validators
from django.utils.translation import gettext_lazy as _
from django.utils.regex_helper import _lazy_re_compile

slug_re = _lazy_re_compile(r'^[a-z][-a-z0-9_]*\Z')
end_re = _lazy_re_compile(r'[a-z0-9]\Z')
alnum_re = _lazy_re_compile(r'^[a-z][a-z0-9]*\Z')


def my_slug_validator(msg = None):
    return validators.RegexValidator(slug_re, _(msg), 'invalid') if msg else validators.RegexValidator(slug_re, _('^[a-z][-a-z0-9_]*\Z'), 'invalid')


def my_end_validator(msg = None):
    return validators.RegexValidator(end_re, _(msg), 'invalid') if msg else validators.RegexValidator(end_re, _('[a-z0-9]\Z'), 'invalid')


def my_alphanumeric_validator(msg = None):
    return validators.RegexValidator(alnum_re, _(msg), 'invalid') if msg else validators.RegexValidator(end_re, _('^[a-z][a-z0-9]*\Z'), 'invalid')
