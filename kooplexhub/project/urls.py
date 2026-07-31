from django.urls import path

from . import views

app_name = 'project'

urlpatterns = [
    # render projects
    path(
        "list/", 
        views.ProjectListView.as_view(), 
        name = "list",
    ),
    path(
        "partials/grid/", 
        views.ProjectGridView.as_view(), 
        name="grid",
    ),
    path(
        "partials/<int:pk>/card/", 
        views.ProjectCardPartialView.as_view(), 
        name="card_partial",
    ),

    # create new project
    path(
        "partials/create/modal/", 
        views.ProjectCreateModalView.as_view(), 
        name="create_modal",
    ),
    path(
        "create/", 
        views.ProjectCreateView.as_view(), 
        name="create",
    ),
    path(
        "partials/create/name/validate/",
        views.ProjectCreateNameValidateView.as_view(),
        name="create-validate-name",
    ),
    path(
        "partials/create/description/validate/",
        views.ProjectCreateDescriptionValidateView.as_view(),
        name="create-validate-description",
    ),
    path(
        "partials/create/preferred_image/validate/",
        views.ProjectCreatePreferredImageValidateView.as_view(),
        name="create-validate-preferred-image",
    ),

    # configure project
    path(
        "partials/<int:project_id>/name/",
        views.ProjectNameDisplayView.as_view(),
        name="name-display",
    ),
    path(
        "partials/<int:project_id>/name/edit/",
        views.ProjectNameEditView.as_view(),
        name="name-edit",
    ),
    path(
        "partials/<int:project_id>/name/update/",
        views.ProjectNameUpdateView.as_view(),
        name="name-update",
    ),

    path(
        "partials/<int:project_id>/description/",
        views.ProjectDescriptionDisplayView.as_view(),
        name="description-display",
    ),
    path(
        "partials/<int:project_id>/description/edit/",
        views.ProjectDescriptionEditView.as_view(),
        name="description-edit",
    ),
    path(
        "partials/<int:project_id>/description/update/",
        views.ProjectDescriptionUpdateView.as_view(),
        name="description-update",
    ),

    path(
        "partials/<int:project_id>/image/", 
        views.ProjectPreferredImageDisplayView.as_view(), 
        name="image-display",
    ),
    path(
        "partials/<int:project_id>/image/change/",
        views.ProjectPreferredImageChangeView.as_view(),
        name="image-edit",
    ),
    path(
        "partials/<int:project_id>/image/update/",
        views.ProjectPreferredImageUpdateView.as_view(),
        name="image-update",
    ),

    path(
        "partials/<int:project_id>/members/modal",
        views.ProjectMembersModalView.as_view(),
        name="members-modal",
    ),
    path(
        "partials/<int:project_id>/members/",
        views.ProjectMembersSummaryView.as_view(),
        name="members-display",
    ),
    path(
        "partials/<int:project_id>/members/edit/",
        views.ProjectMembersChangeView.as_view(),
        name="members-edit",
    ),
    path(
        "partials/<int:project_id>/members/update/",
        views.ProjectMembersUpdateView.as_view(),
        name="members-update",
    ),
    path(
        "partials/<int:project_id>/members/search/",
        views.ProjectMemberSearchView.as_view(),
        name="members-search",
    ),
    path(
        "partials/<int:project_id>/members/row/<int:user_id>/",
        views.ProjectMemberRowView.as_view(),
        name="member-row",
    ),
    path(
        "create/members/search/",
        views.ProjectCreateMemberSearchView.as_view(),
        name="create-members-search",
    ),
    path(
        "create/members/row/<int:user_id>/",
        views.ProjectCreateMemberRowView.as_view(),
        name="create-member-row",
    ),

    path(
        "partials/<int:project_id>/mounts/",
        views.ProjectMountsDisplayView.as_view(),
        name="mounts-display",
    ),
    path(
        "partials/<int:project_id>/mounts/edit/",
        views.ProjectMountsChangeView.as_view(),
        name="mounts-edit",
    ),
    path(
        "partials/<int:project_id>/mounts/update/",
        views.ProjectMountsUpdateView.as_view(),
        name="mounts-update",
    ),


    # environment helper
    path(
        "partials/<int:pk>/environment-tab/",
        views.ProjectEnvironmentTabView.as_view(),
        name="environment_tab",
    ),
    
    path(
        "<int:pk>/environment/create-default/",
        views.ProjectDefaultEnvironmentCreateView.as_view(),
        name="create_default_environment",
    ),
]
