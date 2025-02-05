from django.shortcuts import render
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

from .models.canvas import Canvas, CanvasCourse
from canvas.canvasapi import CanvasAPI


# Create your views here.
class CanvasListView(LoginRequiredMixin, generic.ListView):
    template_name = 'canvas_list.html'
    context_object_name = 'courses'
    model = Canvas

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submenu'] = 'canvas'
#        context['partial'] = 'container_partial_list.html'
#        context['wss_container_fetchlog'] = KOOPLEX.get('hub', {}).get('wss_container_fetchlog', 'wss://localhost/hub/ws/container/fetchlog/{userid}/').format(userid = self.request.user.id)
#        context['wss_container_config'] = KOOPLEX.get('hub', {}).get('wss_container_config', 'wss://localhost/hub/ws/container/config/{userid}/').format(userid = self.request.user.id)
#        context['wss_container_control'] = KOOPLEX.get('hub', {}).get('wss_container_control', 'wss://localhost/hub/ws/container/control/{userid}/').format(userid = self.request.user.id)
#        context['wss_monitor_node'] = KOOPLEX.get('hub', {}).get('wss_monitor_node', 'wss://localhost/hub/ws/monitor/node/{userid}/').format(userid = self.request.user.id)
#        context['t_project'] = TableProject(self.request.user)
#        context['t_course'] = TableCourse(self.request.user)
#        context['t_volume'] = TableVolume(self.request.user)
#        context['url_list'] = reverse('container:list')
#        context['resource_form']=FormContainer(initial={'user': self.request.user})
#        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        return context

    # All of the Canvas objects
    def get_queryset(self):
        user = self.request.user
        canvas = Canvas.objects.get(user = user)
        courses = canvas.get_courses()
        return courses


class CanvasCourseListView(LoginRequiredMixin, generic.ListView):
    template_name = 'canvascourse_list.html'
    context_object_name = 'canvascourse'

    # All of the Canvas courses for the user
    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return CanvasCourse.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #context['menu_education'] = True
        context['submenu'] = 'courses'
        #context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        return context


def create_canvas_course(tmp_course, user):
        '''
        Creates a local course based on the course or course_id
        '''
        api = CanvasAPI(user.token)
        if type(tmp_course) == int:
            tmp_course = api.get_user_courses(tmp_course)

        # Create a Course first
        folder = f"canvas_{tmp_course['id']}"
        course = Course.objects.create(name=tmp_course['name'], folder=folder, description=tmp_course['course_code'])


        is_teacher = False
        if tmp_course['enrollments'][0]['type'] == 'teacher':
            is_teacher = True
        canvas_course = CanvasCourse.objects.create(name=tmp_course['name'],
                                                    canvas_course_id=tmp_course['id'],                                                   
                                                    course=course)
        user_course = UserCourseBinding.objects.create(user=self.user, course=canvas_course.course, is_teacher=is_teacher)
        return canvas_course