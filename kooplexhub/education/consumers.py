import logging
import json
import threading

from channels.generic.websocket import WebsocketConsumer

from education.models import UserAssignmentBinding, Assignment, UserCourseBinding
from education.forms import TableAssignmentHandle

from container.lib.kubernetes import CE_POOL

logger = logging.getLogger(__name__)


class AssignmentConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        self.userid = self.scope["url_route"]["kwargs"].get('userid')

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        userid = parsed.get('user_id')
        assignment_id = parsed.get('assignment_id')
        group_id = parsed.get('group_id')
        # authorize
        assignment = Assignment.objects.get(id = assignment_id)
        UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
        if group_id == "all":
            students = [ b.user for b in assignment.course.studentbindings ]
        else:
            groups = { 'n' if g is None else str(g.id): students for g, students in assignment.course.groups.items() }
            students = groups[group_id]
        bindings_present = list(UserAssignmentBinding.objects.filter(assignment = assignment, user__in = students))
        students_present = [ b.user for b in bindings_present ]
        bindings = [ UserAssignmentBinding(user = u, assignment = assignment) for u in students if u not in students_present ]
        bindings.extend(bindings_present)
        t = TableAssignmentHandle(bindings)
        self.send(text_data = json.dumps(f"""<h6 class="">Handle assignment {assignment.name}</h6>{t.as_html(None)}"""))


