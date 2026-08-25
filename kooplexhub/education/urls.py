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
#    path(
#        "partials/<int:pk>/card/", 
#        views.ProjectCardPartialView.as_view(), 
#        name="card_partial",
#    ),


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

#FIXME    path('course/delete/<int:pk_course>/<int:pk_user>/', views.delete_or_leave, name = 'delete_or_leave'),
]
