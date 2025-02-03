from django.urls import path, re_path

from education import views

app_name = 'education'

urlpatterns = [
    path('student/course/', views.StudentCourseBindingListView.as_view(), name = 'courses'),
    path('teacher/course/', views.TeacherCourseBindingListView.as_view(), name = 'teaching'),
    path('course/delete/<int:pk_course>/<int:pk_user>/', views.delete_or_leave, name = 'delete_or_leave'),
#    path('configure/<int:pk>/', views.ConfigureCourseView.as_view(), name = 'configure'),
#    path('assignment_new/', views.NewAssignmentView.as_view(), name = 'assignment_new'),
#    path('assignment_new/<int:pk>/', views.NewAssignmentView.as_view(), name = 'newass'),
#    path('assignment_configure/', views.ConfigureAssignmentView.as_view(), name = 'assignment_configure'),
#    path('assignment_handler/', views.HandleAssignmentView.as_view(), name = 'assignment_handle'),
    path('assignment_teachers_view/', views.assignment_teacher, name = 'assignment_teacher'), # just a dispatcher
    path('assignment/', views.StudentAssignmentListView.as_view(), name = 'assignment_student'),
    path('assignment_summary/', views.AssignmentSummaryView.as_view(), name = 'assignment_summary'),
    re_path('addcontainer/(?P<usercoursebinding_id>\d+)/?$', views.addcontainer, name = 'autoaddcontainer'),
]
