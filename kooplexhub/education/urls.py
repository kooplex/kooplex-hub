from django.urls import path, re_path

from education import views

app_name = 'education'

urlpatterns = [
    path('student/course/', views.StudentCourseBindingListView.as_view(), name = 'courses'),
    path('teacher/course/', views.TeacherCourseBindingListView.as_view(), name = 'teaching'),
    path('course/delete/<int:pk_course>/<int:pk_user>/', views.delete_or_leave, name = 'delete_or_leave'),
    path('addcontainer/<int:pk>/$', views.addcontainer, name = 'autoaddcontainer'),
]
