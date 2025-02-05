from django.urls import path, re_path

from canvas import views

app_name = 'canvas'

urlpatterns = [
    path('', views.CanvasListView.as_view(), name = 'canvas'),
    path('course', views.CanvasCourseListView.as_view(), name = 'canvascourse'),

]
