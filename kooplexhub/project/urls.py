from django.urls import path

from . import views

app_name = 'project'

urlpatterns = [
    path('list/', views.UserProjectBindingListView.as_view(), name = 'list'),
    path('delete/<int:project_id>/', views.delete_or_leave, name = 'delete'),
    path('addcontainer/<int:userprojectbinding_id>/', views.addcontainer, name = 'autoaddcontainer'),
]
