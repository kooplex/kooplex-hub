from django.urls import path, re_path

from education import views

app_name = 'education'

urlpatterns = [
    path('course/', views.CourseBindingListView.as_view(), name = 'courses'),
    path('configure/<int:pk>/', views.ConfigureCourseView.as_view(), name = 'configure'),
    path('assignment_new/', views.NewAssignmentView.as_view(), name = 'assignment_new'),
    path('assignment_configure/', views.ConfigureAssignmentView.as_view(), name = 'assignment_configure'),
    path('assignment_handler/', views.HandleAssignmentView.as_view(), name = 'assignment_handle'),
    path('assignment_teachers_view/', views.assignment_teacher, name = 'assignment_teacher'), # just a dispatcher
    path('assignment/', views.StudentAssignmentListView.as_view(), name = 'assignment_student'),
    path('assignment_summary/', views.AssignmentSummaryView.as_view(), name = 'assignment_summary'),
    re_path('addcontainer/(?P<usercoursebinding_id>\d+)/?$', views.addcontainer, name = 'autoaddcontainer'),
]
