from django.core.mail import send_mail

send_mail(
    'testmail',
    'This is just a test email',
    'kooplex@elte.hu',
    ['steger@complex.elte.hu'],
    fail_silently=False,
)
