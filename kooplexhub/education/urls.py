from django.urls import path, re_path

from . import views

app_name = 'education'

urlpatterns = [
    path('teaching/', views.TeacherCourseBindingListView.as_view(), name = 'teacher'),
    path('course/', views.StudentCourseBindingListView.as_view(), name = 'student'),
    path('newassignment/', views.newassignment, name = 'newassignment'),
    path('configureassignment/', views.configureassignment, name = 'configureassignment'),
    re_path('assignment_teachers_view/(?P<usercoursebinding_id>\d+)?/?$', views.assignment_teacher, name = 'assignment_teacher'),
    re_path('assignment_students_view/(?P<usercoursebinding_id>\d+)?/?$', views.assignment_student, name = 'assignment_student'),
    path('assignments', views.massassignment, name = 'massassignment'),
    path('handleassigment/', views.handleassignment, name = 'handleassigment'),
    path('submitform/', views.submitform_submit, name = 'submit'),
    re_path('configure/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'configure'),
    re_path('search/(?P<usercoursebinding_id>\d+)?/?$', views.search, name = 'search'),
    re_path('newgroup/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'newgroup'),
    re_path('configuregroup/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'configuregroup'),
    re_path('addstudent/(?P<usercoursebinding_id>\d+)/?$', views.addstudent, name = 'addstudent'),
    re_path('groupstudent/(?P<usercoursebinding_id>\d+)/?$', views.groupstudent, name = 'groupstudent'),
    re_path('addteacher/(?P<usercoursebinding_id>\d+)/?$', views.addteacher, name = 'addteacher'),
    re_path('addcontainer/(?P<usercoursebinding_id>\d+)/?$', views.addcontainer, name = 'autoaddcontainer'),
#    re_path('delete/(?P<project_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
#    path('list/', views.UserProjectBindingListView.as_view(), name = 'list'),
#    path('join/', views.join, name = 'join'),
#    path('layoutflip/', views.layout_flip, name = 'layout_flip'),
#    path('setpagination/', views.set_pagination, name = 'set_pagination'),
#    re_path('hide/(?P<project_id>\d+)/?$', views.hide, name = 'hide'),
#    re_path('show/(?P<project_id>\d+)/?$', views.show, name = 'show'),
#    path('showhide/', views.show_hide, name = 'showhide'),
]
