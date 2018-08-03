import logging

from django.core.management.base import BaseCommand, CommandError
from hub.models import Assignment, UserAssignmentBinding

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check assignment timestamps, and if necessary hand out or collect given assignemnts'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help = "Dry run: list tasks to be done, and do not actually do anything with them", action = "store_true")
        parser.add_argument('--task', help = "Task to run: all scheduled tasks are to be carried out when unspecified", choices = ['handout', 'collect'], nargs = 1)
    
    def handle(self, *args, **options):
        logger.info("tick %s %s" % (args, options))
#        print (options)
        if 'handout' in options.get('tasks', ['handout']):
            self.handle_handout(Assignment.iter_valid(), options['dry'])
        if 'collect' in options.get('tasks', ['collect']):
            self.handle_collect(UserAssignmentBinding.iter_expired(), options['dry'])

    def handle_handout(self, valid_assignments, dry):
        print ("Mass handout")
        for a in valid_assignments:
            student_list = a.list_students_bindable() if dry else a.bind_students()
            if len(student_list):
                print (a)
                for student in student_list:
                    print ("\t-> %s" % student)

    def handle_collect(self, expired_userassignments, dry):
        print ("Mass collect")
        for binding in expired_userassignments:
           print ("<- %s" % binding)
           if not dry:
               binding.do_collect()
