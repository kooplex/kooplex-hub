import logging
import grp, pwd
  
from django.core.management.base import BaseCommand, CommandError
from hub.models import UserGroupBinding
from hub.lib.ldap import Ldap

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List user's group binding in the hub database and check/fix in ldap if missing"

    def add_arguments(self, parser):
        parser.add_argument('--fix', help = "Do store in ldap", action = 'store_true')

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        all_os_groups = list(filter(lambda x: hasattr(x, 'gr_mem'), grp.getgrall()))
        l = Ldap()
        for ugb in UserGroupBinding.objects.all():
            try:
                username = ugb.user.username
                groups = [ g.gr_name for g in all_os_groups if username in g.gr_mem ]
                if ugb.group.name in groups:
                    print (f'OK {ugb}')
                else:
                    if options.get('fix'):
                        l.addusertogroup(user = ugb.user, group = ugb.group)
                        print (f'FIXED {ugb}')
                    else:
                        print (f'MISSING {ugb}')
            except Exception as e:
                print (f'EE: {ugb} -- {e}')

