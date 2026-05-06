from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('review/', views.review, name='review'),
    path('archive/', views.archive, name='archive'),
    path('export/', views.export, name='export'),
    path('projects/', views.project_list, name='project_list'),
    path('settings/topic/', views.project_settings_topic, name='project_settings_topic'),
    path('settings/role/', views.project_settings_role, name='project_settings_role'),
    path('settings/schedule/', views.project_settings_schedule, name='project_settings_schedule'),
    path('settings/file/<int:file_id>/delete/', views.delete_file, name='delete_file'),
    path('settings/member/<int:member_id>/delete/', views.delete_member, name='delete_member'),
    path('projects/<int:project_id>/switch/', views.switch_project, name='switch_project'),
]
