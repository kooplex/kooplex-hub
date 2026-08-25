from django.urls import path
from django.views.generic import RedirectView

from education import views

app_name = 'education'

urlpatterns = [
    # Listing courses
    path(
        "course/", 
        views.CourseListView.as_view(), 
        name='courses',
    ),
    path(
        "student/course/",
        RedirectView.as_view(
            pattern_name="education:courses",
            permanent=False,
        ),
    ),
    path(
        "teacher/course/",
        RedirectView.as_view(
            pattern_name="education:courses",
            permanent=False,
        ),
    ),
    path(
        "partials/grid/", 
        views.CourseGridView.as_view(), 
        name="course-grid",
    ),
    path(
        "partials/course/<int:course_id>/card/",
        views.CourseCardView.as_view(),
        name="course-card",
    ),

    path(
        "course/<int:course_id>/assignments/",
        views.CourseAssignmentsView.as_view(),
        name="course-assignments",
    ),

    # Course creation
    path(
        "partials/create/modal/",
        views.CourseCreateModalView.as_view(),
        name="create-modal",
    ),
    path(
        "create/",
        views.CourseCreateView.as_view(),
        name="create",
    ),
    path(
        "partials/create/name/validate/",
        views.CourseCreateNameValidateView.as_view(),
        name="create-validate-name",
    ),
    path(
        "partials/create/description/validate/",
        views.CourseCreateDescriptionValidateView.as_view(),
        name="create-validate-description",
    ),
    path(
        "partials/create/preferred_image/validate/",
        views.CourseCreatePreferredImageValidateView.as_view(),
        name="create-validate-preferred-image",
    ),
#FIXME: ez vsz nem kell, összeolvad majd
    path(
        "create/members/search/",
        views.CourseCreateMemberSearchView.as_view(),
        name="create-members-search",
    ),
    path(
        "create/members/row/<int:user_id>/",
        views.CourseCreateMemberRowView.as_view(),
        name="create-member-row",
    ),

    path(
        "course/<int:course_id>/name/",
        views.CourseNameDisplayView.as_view(),
        name="name-display",
    ),
    path(
        "course/<int:course_id>/name/edit/",
        views.CourseNameEditView.as_view(),
        name="name-edit",
    ),
    path(
        "course/<int:course_id>/name/update/",
        views.CourseNameUpdateView.as_view(),
        name="name-update",
    ),
    
    path(
        "course/<int:course_id>/description/",
        views.CourseDescriptionDisplayView.as_view(),
        name="description-display",
    ),
    path(
        "course/<int:course_id>/description/edit/",
        views.CourseDescriptionEditView.as_view(),
        name="description-edit",
    ),
    path(
        "course/<int:course_id>/description/update/",
        views.CourseDescriptionUpdateView.as_view(),
        name="description-update",
    ),

    path(
        "partials/<int:course_id>/image/",
        views.CoursePreferredImageDisplayView.as_view(),
        name="image-display",
    ),
    path(
        "partials/<int:course_id>/image/change/",
        views.CoursePreferredImageChangeView.as_view(),
        name="image-edit",
    ),
    path(
        "partials/<int:course_id>/image/update/",
        views.CoursePreferredImageUpdateView.as_view(),
        name="image-update",
    ),
    
    path(
        "partials/<int:course_id>/mounts/modal/",
        views.CourseMountsModalView.as_view(),
        name="mounts-edit",
    ),
    path(
        "partials/<int:course_id>/mounts/",
        views.CourseMountsDisplayView.as_view(),
        name="mounts-display",
    ),
    path(
        "partials/<int:course_id>/mounts/update/",
        views.CourseMountsUpdateView.as_view(),
        name="mounts-update",
    ),
    
    path(
        "partials/<int:course_id>/environment/",
        views.CourseEnvironmentTabView.as_view(),
        name="environment-tab",
    ),
    path(
        "course/<int:course_id>/environment/create-default/",
        views.CourseDefaultEnvironmentCreateView.as_view(),
        name="create-default-environment",
    ),

    path(
        "partials/<int:course_id>/members/",
        views.CourseMembersSummaryView.as_view(),
        name="members-display",
    ),
    path(
        "partials/<int:course_id>/members/modal/",
        views.CourseMembersModalView.as_view(),
        name="members-modal",
    ),
    path(
        "partials/<int:course_id>/members/update/",
        views.CourseMembersUpdateView.as_view(),
        name="members-update",
    ),
    path(
        "partials/<int:course_id>/members/search/",
        views.CourseMemberSearchView.as_view(),
        name="members-search",
    ),
    path(
        "partials/<int:course_id>/members/row/<int:user_id>/",
        views.CourseMemberRowView.as_view(),
        name="member-row",
    ),

#FIXME    path('course/delete/<int:pk_course>/<int:pk_user>/', views.delete_or_leave, name = 'delete_or_leave'),
]
