import time
import json
import sys
import logging
  
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.lib import dirname
from project import filesystem as fs
from hub.models import FilesystemTask, Group, UserGroupBinding
from project.models import Project, UserProjectBinding

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


class Command(BaseCommand):
    help = "Group management and fix filesystem permissions for a project"

    def add_arguments(self, parser):
        parser.add_argument('--project', help = "Select project to handle", nargs = '+')

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        P = options.get('project')
        if P is None:
            print ('WW: available projects: {}'.format(', '.join(map(lambda x: f"{x.subpath} ({x.name} -- {x.creator})", filter(lambda x: len(x.collaborators) > 1, Project.objects.all())))))
            sys.exit(0)
        for psp in P:
            try:
                upb = UserProjectBinding.objects.filter(project__subpath = psp)
                assert len(upb) > 1, f'No collaborators {upb[0].project}'
                group, group_created = Group.objects.get_or_create(name = upb[0].groupname, grouptype = Group.TP_PROJECT)
                if group_created:
                    print (f'Created group {group}')
                for b in upb:
                    _, c = UserGroupBinding.objects.get_or_create(user = b.user, group = group)
                    if c:
                        print (f'{b.user} added to group {group}')
                    time.sleep(.02) # avoid flooding database
                if group_created:
                    FilesystemTask.objects.create(
                        folder = fs.path_project(upb[0].project),
                        group_ro = code([ group ]),
                        recursive = True,
                        task = FilesystemTask.TSK_GRANT
                    )
                    print (f'Fixing fs...')
            except Exception as e:
                print (f'EE: {e}')


