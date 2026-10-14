from django.urls import path, re_path

from . import views

app_name = 'volume'

urlpatterns = [
    path('list/', views.VolumeListView.as_view(), name = 'list'),
    path('partials/grid/', views.VolumeGridView.as_view(), name='grid'),
    path('attachment_new/', views.NewAttachmentView.as_view(), name = 'new_attachment'),
    path('attachment_delete/<int:pk>/', views.destroy, name='destroy'),
    path('partials/<int:pk>/card/', views.VolumeCardView.as_view(), name='card'),
    path('partials/<int:pk>/description/', views.VolumeEditorView.as_view(), {'field': 'description', 'action': 'display'}, name='description-display'),
    path('partials/<int:pk>/description/edit/', views.VolumeEditorView.as_view(), {'field': 'description', 'action': 'edit'}, name='description-edit'),
    path('partials/<int:pk>/description/update/', views.VolumeEditorView.as_view(), {'field': 'description', 'action': 'update'}, name='description-update'),
    path('partials/<int:pk>/scope/', views.VolumeEditorView.as_view(), {'field': 'scope', 'action': 'display'}, name='scope-display'),
    path('partials/<int:pk>/scope/edit/', views.VolumeEditorView.as_view(), {'field': 'scope', 'action': 'edit'}, name='scope-edit'),
    path('partials/<int:pk>/scope/update/', views.VolumeEditorView.as_view(), {'field': 'scope', 'action': 'update'}, name='scope-update'),
]
