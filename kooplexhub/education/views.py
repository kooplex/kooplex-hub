import logging
import re
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import IntegrityError

from django_tables2 import RequestConfig

from kooplexhub.lib import now

from container.models import Image, Container
from .models import UserCourseBinding, UserAssignmentBinding, Assignment, CourseContainerBinding, Group, UserCourseGroupBinding
from .forms import FormCourse
from .forms import FormGroup
from .forms import FormAssignment
from .forms import TableAssignment, TableAssignmentConf, TableAssignmentCollect, TableUser, TableAssignmentMass, TableAssignmentSummary, TableGroup

logger = logging.getLogger(__name__)

class TeacherCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'teacher_course_list.html'
    context_object_name = 'teachercoursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        #self.paginate_by = profile.paginate_project_list
        #pattern = self.request.GET.get('project', profile.search_project_list)
        #if pattern:
        #    projectbindings = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern).order_by('project__name')
        #else:
        #    projectbindings = UserProjectBinding.objects.filter(user = user, is_hidden = False).order_by('project__name')
        #if len(projectbindings) and pattern != profile.search_project_list:
        #    profile.search_project_list = pattern
        #    profile.save()
        return UserCourseBinding.objects.filter(user = user, is_teacher = True)


class StudentCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'student_course_list.html'
    context_object_name = 'studentcoursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        #self.paginate_by = profile.paginate_project_list
        #pattern = self.request.GET.get('project', profile.search_project_list)
        #if pattern:
        #    projectbindings = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern).order_by('project__name')
        #else:
        #    projectbindings = UserProjectBinding.objects.filter(user = user, is_hidden = False).order_by('project__name')
        #if len(projectbindings) and pattern != profile.search_project_list:
        #    profile.search_project_list = pattern
        #    profile.save()
        return UserCourseBinding.objects.filter(user = user, is_teacher = False)


@login_required
def configure(request, usercoursebinding_id, next_page = 'education:teacher'):
    user = request.user
    profile = user.profile
    logger.debug(f"method: {request.method}, user: {user.username}")
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = request.user, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'abuse {user} tries to access usercoursebinding id {usercoursebinding_id}')
        messages.error(request, 'Course does not exist')
        return redirect(next_page)
    if request.POST.get('button') == 'apply':
        active_tab = request.POST.get('active_tab')

        if active_tab == 'conf':
            form_course = FormCourse(request.POST)
            if form_course.is_valid():
                course.name = form.cleaned_data['name']
                course.description = form.cleaned_data['description']
                course.image = form.cleaned_data['image']
                try:
                    course.save()
                except IntegrityError as e:
                    messages.error(request, str(e))
                else:
                    messages.error(request, form_course.errors)
        elif active_tab == 'group':
            form_group = FormGroup(request.POST)
            if form_group.is_valid():
                try:
                    form_group.save()
                    messages.info(request, f'Group {form_group.cleaned_data["name"]} for course {form_group.cleaned_data["course"].name} is created')
                except IntegrityError as e:
                    messages.error(request, str(e))
                else:
                    messages.error(request, form_group.errors)

            gids = [ x.split('-')[-1] for x in filter(lambda x: x.startswith("name-before-"), request.POST.keys()) ]
            delete_ids = request.POST.getlist('selection_group_removal', [])
            d = []
            for gid in delete_ids:
                try:
                    g = Group.objects.get(id = gid, course = course)
                    g.delete()
                    logger.info(f'- deleted g {g.name} from course {course.name} by {user.username}')
                    d.append(f'{g.name}')
                    if gid in gids:
                        gids.remove(gid)
                except Exception as e:
                    logger.error(e)
            if len(d):
                g = ', '.join(d)
                messages.info(request, f'Deleted group(s) {g}.')

            gu = []
            for g in gids:
                before_name = request.POST[f'name-before-{g}']
                after_name = request.POST[f'name-{g}']
                before_description = request.POST[f'description-before-{g}']
                after_description = request.POST[f'description-{g}']
                if (before_name == after_name) and (before_description == after_description):
                    continue
                grp = Group.objects.get(id = g, course = course)
                grp.name = after_name
                grp.description = after_description
                grp.save()
                gu.append(grp.name)
            if len(gu):
                gu = ', '.join(gu)
                messages.info(request, f'Updates group(s) {gu}.')


        return redirect(next_page)
    else:
        active_tab = request.GET.get('active_tab', 'conf')

        pattern = request.GET.get('pattern', profile.search_education_student) if active_tab == 'student' else profile.search_education_student
        table_student = TableUser(course, teacher_selector = False, pattern = pattern)
        if table_student.not_empty and pattern != profile.search_education_student:
            profile.search_education_student = pattern
            profile.save()
        RequestConfig(request).configure(table_student)
        pattern = request.GET.get('pattern', profile.search_education_teacher) if active_tab == 'teacher' else profile.search_education_teacher
        table_teacher = TableUser(course, teacher_selector = True, pattern = pattern)
        if table_teacher.not_empty and pattern != profile.search_education_teacher:
            profile.search_education_teacher = pattern
            profile.save()
        RequestConfig(request).configure(table_teacher)
        table_group = TableGroup(Group.objects.filter(course = course))
        form_course = FormCourse({ 'name': course.name, 'description': course.description, 'image': course.image })
        form_group = FormGroup(course = course)

        student_group_map = { 
                'ungrouped': UserCourseBinding.objects.filter(course = course, is_teacher = False).exclude(usercoursegroupbinding__id__gt = 0),
                'groups': dict([ (g, UserCourseBinding.objects.filter(course = course, is_teacher = False, usercoursegroupbinding__group = g)) 
                        for g in Group.objects.filter(course = course)
                    ])
                }

        context_dict = {
            'courseform': form_course,
            'groupform': form_group,
            't_student': table_student,
            't_teacher': table_teacher,
            't_group': table_group,
            'usercoursebinding_id': usercoursebinding_id,
            'course': course,
            'submenu': 'meta',
            'next_page': next_page,
            'active': active_tab,
            'student_group_map': student_group_map,
        }
        return render(request, 'course_configure.html', context = context_dict)


@login_required
def assignment(request, usercoursebinding_id = None):
    from kooplexhub.lib.dirname import course_assignment_prepare_root #FIXME: replace with container mount
    """
    @summary: handle assignment page. 
    @param usercoursebinding_id: is set if pencil is used, defaults to None if coming from menu.
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    context_dict = {
        'menu_teaching': 'active',
        'submenu': 'assignment',
        'next_page': 'education:assignment',
    }
    if usercoursebinding_id:
        try:
            ucb = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user)
        except UserCourseBinding.DoesNotExist:
            logger.error(f"Missmatch usercoursebindingid {usercoursebinding_id} for user {user}")
            messages.error(request, 'You are not allowed to use this functionality')
            return redirect('indexpage')
        if ucb.is_teacher:
            table_assignment_config = TableAssignmentConf(Assignment.objects.filter(course = ucb.course))
            RequestConfig(request).configure(table_assignment_config)
            uab_handed_out = list(UserAssignmentBinding.objects.filter(assignment__course = ucb.course))
            course_students = set([ b.user for b in ucb.course.studentbindings ])
            course_assignments = ucb.course.assignments
            descartes = [ (a, s) for a in course_assignments for s in course_students ]
            handedout_tuple = [ (b.assignment, b.user) for b in uab_handed_out ]
            complementary = set(descartes).difference(handedout_tuple)
            mock = [ UserAssignmentBinding(user = s, assignment = a) for a, s in complementary ]
            mock.extend(uab_handed_out)
            table_assignment_collect = TableAssignmentCollect(mock)
            RequestConfig(request).configure(table_assignment_collect)
            table_assignment_mass = TableAssignmentMass(Assignment.objects.filter(course = ucb.course))
            RequestConfig(request).configure(table_assignment_mass)
            table_assignment_summary = TableAssignmentSummary(Assignment.objects.filter(course = ucb.course))
            RequestConfig(request).configure(table_assignment_summary)
            context_dict.update({
                'f_assignment': FormAssignment(user = user, course = ucb.course),
                'course': ucb.course,
                't_assignment_config': table_assignment_config,
                't_assignment_collect': table_assignment_collect,
                't_assignment_mass': table_assignment_mass,
                't_assignment_summary': table_assignment_summary,
                'teacher': True,
                'dir_assignment_prepare': course_assignment_prepare_root(ucb.course), #FIXME: containermount!
            })
        else:
            table_submit = TableAssignment(UserAssignmentBinding.objects.filter(user = request.user, assignment__course = ucb.course))
            RequestConfig(request).configure(table_submit)
            context_dict.update({
                't_submit': table_submit,
            })
        return render(request, 'assignment.html', context = context_dict)
    table_submit = TableAssignment(UserAssignmentBinding.objects.filter(user = request.user))
    RequestConfig(request).configure(table_submit)
    context_dict.update({
        't_submit': table_submit,
    })
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    if len(courses):
        table_assignment_config = TableAssignmentConf(Assignment.objects.filter(course__in = courses))
        RequestConfig(request).configure(table_assignment_config)
        uab_handed_out = list(UserAssignmentBinding.objects.filter(assignment__course__in = courses))
        handedout_tuple = [ (b.assignment, b.user) for b in uab_handed_out ]
        descartes = []
        for c in courses:
            course_students = set([ b.user for b in c.studentbindings ])
            course_assignments = c.assignments
            descartes.extend( [ (a, s) for a in course_assignments for s in course_students ] )
        complementary = set(descartes).difference(handedout_tuple)
        mock = [ UserAssignmentBinding(user = s, assignment = a) for a, s in complementary ]
        mock.extend(uab_handed_out)
        table_assignment_collect = TableAssignmentCollect(mock)
        RequestConfig(request).configure(table_assignment_collect)
        table_assignment_mass = TableAssignmentMass(Assignment.objects.filter(course__in = courses))
        RequestConfig(request).configure(table_assignment_mass)
        table_assignment_summary = TableAssignmentSummary(Assignment.objects.filter(course__in = courses))
        RequestConfig(request).configure(table_assignment_summary)
        context_dict.update({
            't_assignment_config': table_assignment_config,
            't_assignment_collect': table_assignment_collect,
            't_assignment_mass': table_assignment_mass,
            't_assignment_summary': table_assignment_summary,
            'teacher': True,
        })
    return render(request, 'assignment.html', context = context_dict)


@login_required
def newassignment(request):
    """
    @summary: handle creation of a new assignment
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course_id = request.POST.get('course_id')
        course = UserCourseBinding.objects.get(user = user, course__id = course_id, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'misused by {user}')
        messages.error(request, f'Not authorized to use this functionality')
        return redirect('indexpage')
    try:
        f = FormAssignment(request.POST, course = course, user = user)
        assert f.is_valid(), f.errors
        a = Assignment.objects.create(
            name = f.cleaned_data['name'],
            course = course,
            creator = user,
            description = f.cleaned_data['description'],
            folder = f.cleaned_data['folder'],#recheck existence
            valid_from = f.cleaned_data['valid_from'],
            expires_at = f.cleaned_data['expires_at'],
            can_studentsubmit = f.cleaned_data['can_studentsubmit'],
            remove_collected = f.cleaned_data['remove_collected'],
        )
        logger.info(f'+ new assignment {a.name} ({a.folder}) in course {course.name} by {user.username}')
        messages.info(request, f'Assignment {a.name} created.')
    except Exception as e:
        logger.error(e)
        raise
    return redirect('education:teacher')


@login_required
def configureassignment(request):
    """
    @summary: handle creation of a new assignment
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    delete_ids = request.POST.getlist('selection_delete', [])
    other_ids = set(request.POST.getlist('assignment_ids', [])).difference(delete_ids)
    d = []
    oops = []
    for aid in delete_ids:
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            assert (a.creator == user) or (a.course.teacher_can_delete_foreign_assignment), f"{user} is not the creator of assignment {a.name} in course {a.course.name} and delete foreign is not set"
            a.delete()
            logger.info(f'- deleted assignment {a.name} ({a.folder}) from course {a.course.name} by {user.username}')
            d.append(f'{a.name} by {a.creator}')
        except AssertionError:
            oops.append(a.name)
            raise
        except Exception as e:
            logger.error(e)
    if len(d):
        a = ', '.join(d)
        messages.info(request, f'Deleted assignment(s) {a}.')
    if len(oops):
        a = ', '.join(oops)
        messages.warning(request, f'You are not allowed to delete assignment(s) {a}.')
    m = []
    for aid in other_ids:
        name = request.POST.get(f'name-{aid}')
        description = request.POST.get(f'description-{aid}')
        if (request.POST.get(f'name-old-{aid}') == name) and (request.POST.get('description-old-{aid}') == description):
            continue
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            a.name = name
            a.description = description
            a.save()
            logger.info(f'. modified assignment {a.name} ({a.folder}) from course {a.course.name} by {user.username}')
            m.append(a.name)
        except Exception as e:
            logger.error(e)
    if len(m):
        a = ', '.join(m)
        messages.info(request, f'Configured assignment(s) {a}.')
    return redirect('education:assignment')


@login_required
def submitform_submit(request):
    """TBA"""
    user = request.user
    logger.debug(f"user {user}, method: {request.method}")
    if request.POST.get('button') == 'apply':
        for uab_id in request.POST.getlist('selection', []):
            try:
                uab = UserAssignmentBinding.objects.get(id = uab_id, user = user, state__in = [ UserAssignmentBinding.ST_WORKINPROGRESS, UserAssignmentBinding.ST_SUBMITTED ])
                uab.submit_count += 1
                uab.state = UserAssignmentBinding.ST_SUBMITTED
                uab.submitted_at = now()
                uab.save()
                #FIXME: message
            except Exception as e:
                logger.error(e)
                #FIXME: message
                raise
        return redirect('education:assignment')
    else:
        return redirect('education:student')


@login_required
def handleassignment(request):
    """ TBA """
    user = request.user
    logger.debug(f"HANDLE user {user}, method: {request.method}")
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    oops = []
    msgs = []
    # handout
    n_handout = 0
    n_handout_error = 0
    extr = [ json.loads(x) for x in request.POST.getlist('selection_handout', []) ]
    for aid, uid in extr:
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            u = UserCourseBinding.objects.get(user__id = uid, course__in = courses, is_teacher = False).user
            UserAssignmentBinding.objects.create(user = u, assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            n_handout += 1
        except Exception as e:
            logger.error(e)
            n_handout_error += 1
            oops.append(str(e))
    if n_handout:
        msgs.append(f'Handed {n_handout} assignments out.')
    # collect
    n_collected = 0
    n_collect_error = 0
    for uab_id in request.POST.getlist('selection_collect', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            uab.state = UserAssignmentBinding.ST_COLLECTED
            uab.submitted_at = now()
            uab.save()
            n_collected += 1
        except Exception as e:
            logger.error(e)
            n_collect_error += 1
            oops.append(str(e))
    if n_collected:
        msgs.append(f'Collected {n_collected} assignments.')
    # correct
    n_corrected = 0
    n_correct_error = 0
    for uab_id in request.POST.getlist('selection_correct', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state__in = [ UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_SUBMITTED ])
            uab.state = UserAssignmentBinding.ST_CORRECTED
            uab.save()
            n_corrected += 1
        except Exception as e:
            logger.error(e)
            n_correct_error += 1
            oops.append(str(e))
    if n_collected:
        msgs.append(f'Marked {n_corrected} assignments for correction.')
    # feedback
    n_feedback = 0
    n_feedback_error = 0
    for uab_id in request.POST.getlist('selection_finalize', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_CORRECTED)
            uab.state = UserAssignmentBinding.ST_READY
            uab.corrected_at = now()
            uab.correction_count += 1
            uab.corrector = user
            uab.feedback_text = request.POST.get(f'feedback_text-{uab_id}')
            uab.score = request.POST.get(f'score-{uab_id}')
            uab.save()
            n_feedback += 1
        except Exception as e:
            logger.error(e)
            n_feedback_error += 1
            oops.append(str(e))
    if n_feedback:
        msgs.append(f'Ready with {n_feedback} assignments.')
    # updated score or feedback_text
    n_updated = 0
    n_update_error = 0
    for uab_id in request.POST.getlist('ready_ids', []):
        score = request.POST.get(f'score-{uab_id}')
        feedback_text = request.POST.get(f'feedback_text-{uab_id}')
        if (request.POST.get(f'score-old-{uab_id}') == score) and (request.POST.get(f'feedback_text-old-{uab_id}') == feedback_text):
            continue
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_READY)
            uab.score = score
            uab.feedback_text = feedback_text
            uab.save()
            n_updated += 1
        except Exception as e:
            logger.error(e)
            n_update_error += 1
            oops.append(str(e))
    if n_updated:
        msgs.append(f'{n_updated} assignment scores and or feedback messages were edited and saved.')
    # reassign
    n_reassign = 0
    n_reassign_error = 0
    for uab_id in request.POST.getlist('selection_reassign', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_READY)
            uab.state = UserAssignmentBinding.ST_WORKINPROGRESS
            uab.save()
            n_reassign += 1
        except Exception as e:
            logger.error(e)
            n_reassign_error += 1
            oops.append(str(e))
    if n_reassign:
        msgs.append(f'{n_reassign} assignments were reassigned.')
    if len(msgs):
        messages.info(request,' '.join(msgs))
    if len(oops):
        messages.error(request,' '.join(oops))
    return redirect('education:assignment')

@login_required
def massassignment(request):
    def extract(lbl):
        L = []
        for l in request.POST.getlist(lbl, []):
            L.extend(json.loads(l))
        return L
    """
    @summary: handle assignments for a course in a mass
    """
    user = request.user
    logger.debug(f"user {user}, method: {request.method}")
    if request.POST.get('button') != 'apply':
        return redirect('education:assignment')
    msgs = []
    oops = []

    n_collect = 0
    for uab_id in extract('collect_selection'):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            UserCourseBinding.objects.get(user = user, course = uab.assignment.course, is_teacher = True)
            uab.state = UserAssignmentBinding.ST_COLLECTED
            uab.submitted_at = now()
            uab.save()
            n_collect += 1
        except Exception as e:
            logger.error(e)
            oops.append(e)
    if n_collect:
        msgs.append(f'Collected {n_collect} assignments alltogether.')

    n_correct = 0
    for uab_id in extract('correct_selection'):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, state__in = [ UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_SUBMITTED ])
            UserCourseBinding.objects.get(user = user, course = uab.assignment.course, is_teacher = True)
            uab.state = UserAssignmentBinding.ST_CORRECTED
            uab.save()
            n_correct += 1
        except Exception as e:
            logger.error(e)
            oops.append(e)
    if n_correct:
        msgs.append(f'Marked {n_correct} assignments alltogether for correction.')

    n_assign = 0
    for (a_id, u_id) in extract('assign_selection'):
        try:
            a = Assignment.objects.get(id = a_id)
            UserCourseBinding.objects.get(user = user, course = a.course, is_teacher = True)
            u = UserCourseBinding.objects.get(user__id = u_id, course = a.course, is_teacher = False).user
            UserAssignmentBinding.objects.create(user = u, assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            n_assign += 1
        except Exception as e:
            logger.error(e)
            oops.append(str(e))
    if n_assign:
        msgs.append(f'Sending out to {n_assign} students an assignment.')
    if len(msgs):
        messages.info(request, ' '.join(msgs))
    if len(oops):
        messages.error(request, ' '.join(oops))
    return redirect('education:assignment')


@login_required
def _adduser(request, usercoursebinding_id, is_teacher):
    """
    @summary: the teacher of a course may add or remove students/teachers to the given course
              this function handles request
    """
    f = 'teacher' if is_teacher else 'student'
    user = request.user
    logger.debug(f"user {user}, method: {request.method}")
    oops = []
    msgs = []
    if request.POST.get('button') != 'apply':
        return redirect('education:teacher')
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        raise
        logger.error(f'misused by {user}')
        messages.error(request, f'Not authorized to use this functionality')
        return redirect('indexpage')
    added = 0
    for uid in request.POST.getlist(f'selection_{f}', []):
        try:
            u = User.objects.get(id = uid)
            UserCourseBinding.objects.create(user = u, course = course, is_teacher = is_teacher)
            added += 1
            logger.info(f'+ user {u.username} bound to course {course.name} by {user.username} as {f}')
        except Exception as e:
            logger.error(e)
            oops.append(e)
    if added:
        msgs.append(f'Bound {added} {f} to course {course.name}.')
    removed = 0
    for ucbid in request.POST.getlist(f'selection_{f}_removal', []):
        try:
            ucb = UserCourseBinding.objects.get(id = ucbid, course = course, is_teacher = is_teacher)
            ucb.delete()
            removed += 1
            logger.info(f'- user {ucb.user.username} as {f} is removed from course {course.name} by {user.username}')
        except Exception as e:
            logger.error(e)
            oops.append(e)
    if removed:
        msgs.append(f'Removed {removed} {f} from course {course.name}.')
    if len(msgs):
        messages.info(request, ' '.join(msgs))
    if len(oops):
        messages.error(request, ' '.join(oops))
    return redirect('education:teacher')


@login_required
def addstudent(request, usercoursebinding_id):
    return _adduser(request, usercoursebinding_id, is_teacher = False)


@login_required
def addteacher(request, usercoursebinding_id):
    return _adduser(request, usercoursebinding_id, is_teacher = True)


@login_required
def addcontainer(request, usercoursebinding_id):
    """
    @summary: handle assignment page. 
    @param usercoursebinding_id: is set if pencil is used, defaults to None if coming from menu.
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user).course
        container, _ = Container.objects.get_or_create(
            name = re.sub('[ _\.]', '', course.name), # course.name, #FIXME:why not validated?
            user = user,
            suffix = 'edu',
            image = course.image
        )
        CourseContainerBinding.objects.create(course = course, container = container)
    except:
        raise
    return redirect('container:list')


@login_required
def groupstudent(request, usercoursebinding_id):
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user, is_teacher = True).course
        for k in filter(lambda x: x.startswith('grp-'), request.POST.keys()):
            gid = k.split('-')[1]
            group = Group.objects.get(id = gid, course = course)
            ids_before = json.loads(request.POST[f'before_grp-{gid}'])
            ids_after = json.loads(request.POST[k])
            for ucbid in set(ids_before).difference(ids_after):
                ucgb = UserCourseGroupBinding.objects.get(usercoursebinding__id = ucbid, group = group, usercoursebinding__course = course, usercoursebinding__is_teacher = False)
                ucgb.delete()
                #FIXME: message
        for k in filter(lambda x: x.startswith('grp-'), request.POST.keys()):
            gid = k.split('-')[1]
            group = Group.objects.get(id = gid, course = course)
            ids_before = json.loads(request.POST[f'before_grp-{gid}'])
            ids_after = json.loads(request.POST[k])
            for ucbid in set(ids_after).difference(ids_before):
                ucb = UserCourseBinding.objects.get(id = ucbid, course = course, is_teacher = False)
                UserCourseGroupBinding.objects.create(usercoursebinding = ucb, group = group)
                #FIXME: message
    except:
        raise
    return redirect('education:teacher')
