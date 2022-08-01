from django.urls import path, re_path

from . import views

app_name = 'education'

urlpatterns = [
    path('teaching/', views.TeacherCourseBindingListView.as_view(), name = 'teacher'),
    path('course/', views.StudentCourseBindingListView.as_view(), name = 'student'),
    path('newassignment/', views.newassignment, name = 'newassignment'),
    path('configureassignment/', views.configureassignment, name = 'configureassignment'),
    path('assignment_teachers_view/', views.assignment_teacher, name = 'assignment_teacher'),
    path('assignment_mass/', views.handle_mass, name = 'handle_mass'),
    path('assignment_mass_many/', views.handle_mass_many, name = 'handle_mass_many'),
    re_path('assignment_students_view/(?P<usercoursebinding_id>\d+)?/?$', views.assignment_student, name = 'assignment_student'),
    path('handleassigment/', views.handleassignment, name = 'handleassigment'),
    path('submitform/', views.submitform_submit, name = 'submit'),
    re_path('configure/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'configure'),
    re_path('configure_save/(?P<usercoursebinding_id>\d+)/?$', views.configure_save, name = 'configure_save'),
#    re_path('newgroup/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'newgroup'),
#    re_path('configuregroup/(?P<usercoursebinding_id>\d+)/?$', views.configure, name = 'configuregroup'),
#    re_path('addstudent/(?P<usercoursebinding_id>\d+)/?$', views.addstudent, name = 'addstudent'),
#    re_path('groupstudent/(?P<usercoursebinding_id>\d+)/?$', views.groupstudent, name = 'groupstudent'),
#    re_path('addteacher/(?P<usercoursebinding_id>\d+)/?$', views.addteacher, name = 'addteacher'),
    re_path('addcontainer/(?P<usercoursebinding_id>\d+)/?$', views.addcontainer, name = 'autoaddcontainer'),
]
