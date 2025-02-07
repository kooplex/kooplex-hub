from django.urls import path

from . import views

app_name = 'container'

urlpatterns = [
    path('list/', views.ContainerListView.as_view(), name = 'list'),
    path('delete/<int:pk>/', views.destroy, name = 'destroy'),
    path('open/<int:pk>/', views.open, name = 'open'),
]
