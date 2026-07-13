from django.urls import path

from . import views

app_name = 'container'

urlpatterns = [
    # render containers
    path(
        "list/", 
        views.ContainerListView.as_view(), 
        name = "list",
    ),
    path(
        "partials/grid/", 
        views.ContainerGridView.as_view(), 
        name="grid",
    ),
    path(
        "partials/<int:pk>/card/", 
        views.ContainerCardPartialView.as_view(), 
        name="card_partial",
    ),

    # create new container
    path(
        "create/", 
        views.ContainerCreateView.as_view(), 
        name="create",
    ),
    path(
        "partials/create-picker-empty/", 
        views.ContainerCreatePickerEmptyView.as_view(), 
        name="create_picker_empty",
    ),
    path(
        "partials/create-modal/", 
        views.ContainerCreateModalView.as_view(), 
        name="create_modal",
    ),
    path(
        "partials/create-image-picker/", 
        views.ContainerCreateImagePickerView.as_view(), 
        name="create_image_picker",
    ),
    path(
        "partials/create-image-selected/<int:pk>/",
        views.ContainerCreateImageSelectedView.as_view(),
        name="create_image_selected",
    ),
    path(
        "partials/create-mounts-picker/", 
        views.ContainerCreateMountsPickerView.as_view(), 
        name="create_mounts_picker",
    ),
    path(
        "partials/create-mounts-selected/", 
        views.ContainerCreateMountsSelectedView.as_view(), 
        name="create_mounts_selected",
    ),

    # configure container
    path(
        "<int:pk>/name/display/",
        views.ContainerNameDisplayView.as_view(),
        name="name_display",
    ),
    path(
        "<int:pk>/name/edit/",
        views.ContainerNameEditView.as_view(),
        name="name_edit",
    ),
    path(
        "<int:pk>/name/update/",
        views.ContainerNameUpdateView.as_view(),
        name="name_update",
    ),
    
    path(
        "<int:pk>/uptime/display/",
        views.ContainerUptimeDisplayView.as_view(),
        name="uptime_display",
    ),
    path(
        "<int:pk>/uptime/edit/",
        views.ContainerUptimeEditView.as_view(),
        name="uptime_edit",
    ),
    path(
        "<int:pk>/uptime/update/",
        views.ContainerUptimeUpdateView.as_view(),
        name="uptime_update",
    ),
    path(
        "partials/<int:pk>/image-modal/", 
        views.ContainerImageModalView.as_view(), 
        name="image_modal",
    ),
    path(
        "partials/<int:pk>/image-picker/", 
        views.ContainerImagePickerView.as_view(), 
        name="image_picker",
    ),
    path(
        "partials/<int:pk>/image-save/", 
        views.ContainerImageSaveView.as_view(), 
        name="image_save",
    ),
    path(
        "partials/<int:pk>/mounts-modal/", 
        views.ContainerMountsModalView.as_view(), 
        name="mounts_modal",
    ),
    path(
        "partials/<int:pk>/mounts-save/", 
        views.ContainerMountsSaveView.as_view(), 
        name="mounts_save",
    ),
    path(
        "<int:pk>/compute/display/",
        views.ContainerComputeDisplayView.as_view(),
        name="compute_display",
    ),
    path(
        "<int:pk>/compute/edit/",
        views.ContainerComputeEditView.as_view(),
        name="compute_edit",
    ),
    path(
        "<int:pk>/compute/update/",
        views.ContainerComputeUpdateView.as_view(),
        name="compute_update",
    ),

    # container live widgets and action (htmx endpoints)s
    path(
        "partials/<int:pk>/start-button/",
        views.ContainerStartButtonPartialView.as_view(),
        name="start_button_partial",
    ),
    path(
        "partials/<int:pk>/stop-button/",
        views.ContainerStopButtonPartialView.as_view(),
        name="stop_button_partial",
    ),
    path(
        "partials/<int:pk>/restart-button/",
        views.ContainerRestartButtonPartialView.as_view(),
        name="restart_button_partial",
    ),
    path(
        "partials/<int:pk>/fetchlog-button/",
        views.ContainerFetchlogButtonPartialView.as_view(),
        name="fetchlog_button_partial",
    ),
    path(
        "<int:pk>/control/<str:action>/",
        views.ContainerControlView.as_view(),
        name="control",
    ),
    path(
        "partials/<int:pk>/open-button/",
        views.ContainerOpenButtonPartialView.as_view(),
        name="open_button_partial",
    ),
    path(
        "open/<int:pk>/<int:pk_view>/",
        views.ContainerOpenServiceView.as_view(),
        name="open_serviceview",
    ),
    path(
        "partials/<int:pk>/fetchlog-modal/",
        views.ContainerFetchLogModalView.as_view(),
        name="fetchlog_modal",
    ),
    
    path(
        "partials/<int:pk>/fetchlog/",
        views.ContainerFetchLogView.as_view(),
        name="fetchlog",
    ),

 
    # delete container
    path(
        "delete/<int:pk>/",
        views.ContainerDeleteView.as_view(),
        name="destroy",
    ),

]
