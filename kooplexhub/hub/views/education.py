import logging

from django.db import transaction
from django.conf.urls import url
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from hub.models import CourseCode, Course, UserCourseCodeBinding, UserCourseBinding
from hub.models import Assignment, UserAssignmentBinding
from hub.models import Image

from kooplex.lib import now, translate_date

from hub.forms import FormAssignment
from hub.forms import T_BIND_ASSIGNMENT, T_COLLECT_ASSIGNMENT, T_FEEDBACK_ASSIGNMENT, T_SUBMIT_ASSIGNMENT

logger = logging.getLogger(__name__)


@login_required
def teaching(request):
    """Renders the projectlist page for courses taught."""
    logger.debug('Rendering teaching.html')
    context_dict = {
        'menu_teaching': 'active',
        'next_page': 'education:teaching', 
    }
    return render(request, 'edu/teaching.html', context = context_dict)


@login_required
def courses(request):
    """Renders the projectlist page for students."""
    logger.debug('Rendering courses.html')
    context_dict = {
        'menu_teaching': 'active',
        'next_page': 'education:courses', 
    }
    return render(request, 'edu/courses.html', context = context_dict)


@login_required
def conf_meta(request, course_id, next_page):
    user = request.user
    logger.debug("method: %s, course id: %s, user: %s" % (request.method, course_id, user))
    try:
        course = Course.get_usercourse(course_id = course_id, user = request.user)
    except Course.DoesNotExist as e:
        logger.error('abuse by %s course id: %s -- %s' % (user, course_id, e))
        messages.error(request, 'Course does not exist')
        return redirect(next_page)

    if request.method == 'POST' and request.POST.get('button') == 'apply':
        course.description = request.POST.get('description')
        imagename = request.POST['course_image']
        course.image = Image.objects.get(name = imagename) if imagename != 'None' else None
        course.save()
        return redirect(next_page)
    else:
        context_dict = {
            'images': Image.objects.all(),
            'course': course,
            'submenu': 'meta',
            'next_page': next_page,
        }
        return render(request, 'edu/configure.html', context = context_dict)


@login_required
def newassignment(request, course_id):
    """Renders assignment management form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        binding = UserCourseBinding.objects.get(user = user, course = course, is_teacher = True)
    except Course.DoesNotExist:
        logger.error("Missing course id %s and user %s" % (course_id, user))
        return redirect('education:teaching')
    except UserCourseBinding.DoesNotExist:
        logger.error("Missing course id %s and user %s" % (course_id, user))
        messages.error(request, 'You are not allowed to create an assignment for %s' % (course))
        return redirect('education:teaching')
    if request.method == 'GET':
        context_dict = {
            'course': course,
            'f_assignment': FormAssignment(user = user, course = course),
            'menu_teaching': 'active',
            'submenu': 'new',
            'next_page': 'education:teaching',
        }
        return render(request, 'edu/assignment-teacher.html', context = context_dict)
    elif request.method == 'POST':
        coursecode_ids = request.POST.getlist("coursecodes")
        name = request.POST.get("name").strip()
        description = request.POST.get("description").strip()
        folder = request.POST.get("folder")
        timenow = now()
        valid_from = translate_date(request.POST.get('valid_from')) or timenow
        expires_at = translate_date(request.POST.get('expires_at'))
        is_massassignment = bool(request.POST.get("is_massassignment"))
        can_studentsubmit = bool(request.POST.get("can_studentsubmit"))
        remove_collected = bool(request.POST.get("remove_collected"))
        try:
            assert valid_from >= timenow, "You try to shedule assignment behind time."
            assert len(name), "You need to provide a name"
            assert len(coursecode_ids), "You need to select at least one course code"
            extra = {}
            if expires_at:
                assert (expires_at - valid_from).total_seconds() >= 60, "Expiry is too close to handout. "
            for coursecodeid in coursecode_ids:
                coursecode = CourseCode.objects.get(id = coursecodeid)
                assert coursecode.course == course, "Course code mismatch"
                #UserCourseCodeBinding.objects.get(coursecode = coursecode, user = user, is_teacher = True)
                logger.debug("coursecode id %s" % coursecodeid)
                with transaction.atomic():
                    assignments = Assignment.objects.filter(
                        coursecode = coursecode, 
                        name = name, 
                        creator = user, 
                        description = description, 
                        folder = folder, 
                        can_studentsubmit = can_studentsubmit, 
                        remove_collected = remove_collected,
                        is_massassignment = is_massassignment, 
                        expires_at = expires_at
                        )
                    if len(assignments):
                        logger.warning('Prevented from duplicating assignments for course code %s' % (coursecode))
                        messages.warning(request, 'Maybe you double clicked on assignments.')
                        continue
                    Assignment.objects.create(
                        coursecode = coursecode, 
                        name = name, 
                        creator = user, 
                        description = description, 
                        folder = folder, 
                        can_studentsubmit = can_studentsubmit, 
                        remove_collected = remove_collected,
                        is_massassignment = is_massassignment, 
                        valid_from = valid_from,
                        expires_at = expires_at
                    )
                    logger.info('New assignments for course code %s' % (coursecode))
                    messages.info(request, 'New assignments for course code %s' % (coursecode))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot fully register assignment -- %s' % e)
            return redirect('education:newassignment', course.id)
    return redirect('education:teaching')


@login_required
def bindassignment(request, course_id):
    from django.contrib.auth.models import User
    """Bind assignment and user"""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'GET':
        s_name = request.GET.get('name', '')
        s_username = request.GET.get('username', '')
        s_assignment = request.GET.get('assignment', '')
        table_bind = T_BIND_ASSIGNMENT(course.bindableassignments())
        RequestConfig(request).configure(table_bind)
        context_dict = {
            'course': course,
            't_bind': table_bind,
            'search_name': s_name,
            'search_username': s_username,
            'search_assignment': s_assignment,
            'menu_teaching': 'active',
            'submenu': 'bind',
            'next_page': 'education:teaching', 
        }
        return render(request, 'edu/assignment-teacher.html', context = context_dict)
    elif request.method == 'POST':
        thetime = now()
        oopses = 0
        done = 0
        for br in request.POST.getlist('binding_representation'):
            user_id, assignment_id = br.split('_')
            try:
                assignment = Assignment.objects.get(id = assignment_id)
                student = User.objects.get(id = user_id)
                assert student in assignment.list_students_bindable(), "Cannot bind %s to %s" % (student, assignment)
                assert user.profile.is_coursecodeteacher(assignment.coursecode), "You are not a teacher of %s" % assignment.coursecode
            except Exception as e:
                raise
                logger.error("oops -- %s" % e)
                oopses += 1
                continue
            try:
                binding = UserAssignmentBinding.objects.get(user = student, assignment = assignment)
                logger.error("Will not create a duplicate %s" % binding)
                messages.error(request, "Prevented from creating a duplicate assignment %s for student %s" % (assignment.name, student))
            except UserAssignmentBinding.DoesNotExist:
                pass
            valid_from = translate_date(request.POST.get('valid_from_%s' % br))
            expires_at = translate_date(request.POST.get('expires_at_%s' % br))
            if valid_from and valid_from > thetime:
                UserAssignmentBinding.objects.create(user = student, assignment = assignment, valid_from = valid_from, expires_at = expires_at, state = UserAssignmentBinding.ST_QUEUED)
            else:
                UserAssignmentBinding.objects.create(user = student, assignment = assignment, valid_from = valid_from, expires_at = expires_at)
    #FIXME> expiry check in model init!
            messages.info(request, "Creating an assignment %s for student %s" % (assignment.name, student))
        url_next = reverse('education:bindassignment', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        logger.debug("next: %s %s" % (url_next, pager)) 
        return redirect(url_next + "?%s" % pager) if pager else redirect('education:bindassignment', course_id)
    else:
        return redirect('education:teaching')


@login_required
def collectassignment(request, course_id):
    """Handle assignment collection"""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    per_page=20
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'POST' and request.POST['button'] == 'search':
        s_name = request.POST.get('name')
        per_page = request.POST.get('per_page')
        s_username = request.POST.get('username')
        s_assignment = request.POST.get('assignment')
        render_page = True
    elif request.method == 'GET':
        s_name = None
        s_username = None
        s_assignment = None
        render_page = True
    else:
        render_page = False
    if render_page:
        table_collect = T_COLLECT_ASSIGNMENT(course.userassignmentbindings(s_assignment = s_assignment, s_name = s_name, s_username = s_username, s_assignmentstate = UserAssignmentBinding.ST_WORKINPROGRESS))
        RequestConfig(request,  paginate={'per_page': per_page}).configure(table_collect)
        context_dict = {
            'course': course,
            't_collect': table_collect,
            'search_name': s_name if s_name else '',
            'search_username': s_username if s_username else '',
            'search_assignment': s_assignment if s_assignment else '',
            'per_page': per_page,
            'menu_teaching': 'active',
            'submenu': 'collect',
            'next_page': 'education:feedback',
        }
        return render(request, 'edu/assignment-teacher.html', context = context_dict)
    elif request.method == 'POST':
        userassignmentbinding_ids = request.POST.getlist('userassignmentbinding_ids')
        for binding_id in userassignmentbinding_ids:
            try:
                binding = UserAssignmentBinding.objects.get(id = binding_id)
                coursecode = binding.assignment.coursecode
                assert coursecode.course == course, "course code mismatch"
                #UserCourseCodeBinding.objects.get(user = user, coursecode = coursecode, is_teacher = True)
                UserCourseBinding.objects.get(user = user, course = binding.assignment.coursecode.course, is_teacher = True)
                binding.do_collect()
                messages.info(request, 'Assignment %s of %s for course code %s is collected' % (binding.assignment.name, binding.user, coursecode))
            except Exception as e:
                logger.error(e)
                messages.error(request, 'Cannot mark assignment collected -- %s' % e)
        url_next = reverse('education:collectassignment', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        return redirect(url_next + "?%s" % pager) if pager else redirect('education:collectassignment', course_id)
    else:
        return redirect('indexpage')


@login_required
def feedbackassignment(request, course_id):
    """Mark assignments to correct"""
    from hub.models.assignment import ST_LOOKUP
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    per_page=20
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'POST' and request.POST['button'] == 'search':
        per_page = request.POST.get('per_page')
        s_name = request.POST.get('name')
        s_username = request.POST.get('username')
        s_assignment = request.POST.get('assignment')
        s_assignmentstate = request.POST.get('assignmentstate') if request.POST.get('assignmentstate') else None
        render_page = True
    elif request.method == 'GET':
        s_name = None
        s_username = None
        s_assignment = None
        s_assignmentstate = None
        render_page = True
    else:
        render_page = False
    if render_page:
        table_feedback = T_FEEDBACK_ASSIGNMENT(course.userassignmentbindings(s_assignment = s_assignment, s_name = s_name, s_username = s_username, s_assignmentstate = s_assignmentstate))
        RequestConfig(request,  paginate={'per_page': per_page}).configure(table_feedback)
        context_dict = {
            'course': course,
            't_feedback': table_feedback,
            'search_name': s_name if s_name else '',
            'search_username': s_username if s_username else '',
            'search_assignment': s_assignment if s_assignment else '',
            'search_assignmentstate': s_assignmentstate if s_assignmentstate else '',
            'states': ST_LOOKUP,
            'menu_teaching': 'active',
            'submenu': 'feedback',
            'per_page': per_page,
            'next_page': 'education:feedback',
        }
        return render(request, 'edu/assignment-teacher.html', context = context_dict)
    elif request.method == 'POST':
        for k, v in request.POST.items():
            try:
                task, binding_id = k.split('_')
                assert task == 'task'
                assert v in [ 'correct', 'ready', 'reassign' ]
                task = v
            except:
                continue
            try:
                binding = UserAssignmentBinding.objects.get(id = binding_id)
                #UserCourseCodeBinding.objects.get(user = user, coursecode = binding.assignment.coursecode, is_teacher = True)
                UserCourseBinding.objects.get(user = user, course = binding.assignment.coursecode.course, is_teacher = True)
                score = request.POST.get('score_%s' % binding_id)
                feedback_text = request.POST.get('feedback_text_%s' % binding_id)
                if task == 'correct':
                    binding.state = UserAssignmentBinding.ST_CORRECTING
                    binding.corrector = user
                elif task == 'ready':
                    binding.state = UserAssignmentBinding.ST_FEEDBACK
                    binding.corrected_at = now()
                    binding.score = float(score)
                    if feedback_text:
                        binding.feedback_text = feedback_text.strip()
                elif task == 'reassign': 
                    binding.state = UserAssignmentBinding.ST_WORKINPROGRESS
                    binding.corrected_at = now()
                binding.save()
                messages.info(request, '%s\'s assignment %s for course code %s is now %s' % (binding.user.username, binding.assignment.name, binding.assignment.coursecode.courseid, binding.assignment.state))
            except Exception as e:
                logger.error(e)
                messages.error(request, 'Cannot mark assignment corrected -- %s' % e)
        url_next = reverse('education:feedback', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        return redirect(url_next + "?%s" % pager) if pager else redirect('education:feedback', course_id)
    else:
        return redirect('education:teaching')

@login_required
def summaryassignment(request, course_id):
    """Summary of the grades for each assignment"""
    from hub.models.assignment import ST_LOOKUP
    from pandas import DataFrame 
    from django_pandas.io import read_frame
    from hub.models import UserAssignmentBinding

    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    per_page=20
    course = Course.objects.get(id = course_id)
    qs = UserAssignmentBinding.objects.filter(assignment__coursecode__course__id=course_id)
    if len(list(qs)) == 0:
        newdf = DataFrame()
        messages.warning(request, 'Course %s has no assignments yet' % (course.name))
    else:
        try:
            df = read_frame(qs)
            df['Assignments'] = df.assignment.apply(lambda x: x.split("[")[0].strip())   
            df.score.fillna(0, inplace=True)
            assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
            newdf = df.pivot_table(index='user', columns='Assignments', values='score')#, aggfunc='count')
            #qs.to_dataframe(['age', 'wage'], index='full_name'])
            #qs.filter(age__gt=20, department='IT').to_dataframe(index='full_name')
            newdf['Sum'] = df.groupby(['user']).sum().score
        except Exception as e:
            logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
            try:
                 assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = False))) > 0, "%s is not even a student of course %s" % (user, course)
                 df = df[df.user == user.username]
                 newdf = df.pivot_table(index='user', columns='Assignments', values='score')#, aggfunc='count')
                 newdf['Sum'] = df.groupby(['user']).sum().score
            except Exception as e:
                 logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
                 return redirect('indexpage')
    if request.method == 'GET':
        render_page = True
    else:
        render_page = False
    if render_page:
        context_dict = {
            'course': course,
            'pd': newdf.sort_values(by=['Sum'], ascending=True).to_html(table_id='datatable', col_space=300),
            'menu_teaching': 'active',
            'submenu': 'summary',
            'per_page': per_page,
            'next_page': 'education:summary',
        }
        return render(request, 'edu/assignment-teacher.html', context = context_dict)
    else:
        return redirect('education:teaching')


@login_required
def submitassignment(request, course_id):
    """Handle assignment submission"""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = False))) == 1, "%s is not a student of course %s" % (user, course)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'GET':
        table_submit = T_SUBMIT_ASSIGNMENT(course.userassignmentbindings(user = user))
        RequestConfig(request).configure(table_submit)
        context_dict = {
            'course': course,
            't_submit': table_submit,
            'menu_teaching': 'active',
            'submenu': 'submit',
            'next_page': 'education:course',
        }
        return render(request, 'edu/assignment-student.html', context = context_dict)
    elif request.method == 'POST':
        userassignmentbinding_ids = request.POST.getlist('userassignmentbinding_ids')
        for binding_id in userassignmentbinding_ids:
            try:
                binding = UserAssignmentBinding.objects.get(id = binding_id, user = user)
                binding.state = UserAssignmentBinding.ST_SUBMITTED
                binding.submitted_at = now()
                binding.save()
                assignment = binding.assignment
                coursecode = assignment.coursecode
                messages.info(request, '%s assignment is submitted for course %s (%s)' % (assignment.name, coursecode.course.name, coursecode.courseid))
            except Exception as e:
                logger.error(e)
                messages.error(request, 'Cannot fully submit assignment -- %s' % e)
    return redirect('education:courses')



urlpatterns = [
    url(r'^teaching/?$', teaching, name = 'teaching'),
    url(r'^courses/?$', courses, name = 'courses'),
    url(r'^configurecourse/(?P<course_id>\d+)/meta/(?P<next_page>\w+:?\w*)$', conf_meta, name = 'conf_meta'), 
    url(r'^newassignemnt/(?P<course_id>\d+)$', newassignment, name = 'newassignment'),
    url(r'^bindassignment/(?P<course_id>\d+)$', bindassignment, name = 'bindassignment'),
    url(r'^collectassignment/(?P<course_id>\d+)$', collectassignment, name = 'collectassignment'),
    url(r'^feedback/(?P<course_id>\d+)$', feedbackassignment, name = 'feedback'),
    url(r'^summary/(?P<course_id>\d+)$', summaryassignment, name = 'summary'),
    url(r'^submitassignment/(?P<course_id>\d+)$', submitassignment, name = 'submitassignment'),
]
