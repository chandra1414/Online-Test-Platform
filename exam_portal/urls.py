from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.student_dashboard, name='home'),
    path('login/', views.user_login_view, name='login'),
    path('register/', views.student_register_view, name='register'),
    path('logout/', views.user_logout_view, name='logout'),

    # Student portal
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('test/<int:test_id>/instruction/', views.test_instruction, name='test_instruction'),
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),
    path('attempt/<uuid:attempt_id>/take/', views.take_test, name='take_test'),
    path('attempt/<uuid:attempt_id>/save-ajax/', views.save_answer_ajax, name='save_answer_ajax'),
    path('student/run-code-ajax/', views.run_code_ajax, name='run_code_ajax'),
    path('attempt/<uuid:attempt_id>/submit/', views.submit_test, name='submit_test'),
    path('attempt/<uuid:attempt_id>/result/', views.test_result, name='test_result'),
    path('history/', views.test_history, name='test_history'),
    path('attempt/<uuid:attempt_id>/certificate/', views.download_certificate, name='download_certificate'),

    # Leaderboard
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),

    # Custom Admin Module
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/tests/', views.admin_tests_list, name='admin_tests_list'),
    path('admin-portal/tests/create/', views.admin_test_create, name='admin_test_create'),
    path('admin-portal/tests/<int:test_id>/', views.admin_test_detail, name='admin_test_detail'),
    path('admin-portal/tests/<int:test_id>/edit/', views.admin_test_edit, name='admin_test_edit'),
    path('admin-portal/tests/<int:test_id>/delete/', views.admin_test_delete, name='admin_test_delete'),
    path('admin-portal/tests/<int:test_id>/questions/add/', views.admin_question_create, name='admin_question_create'),
    path('admin-portal/questions/<int:question_id>/edit/', views.admin_question_edit, name='admin_question_edit'),
    path('admin-portal/questions/<int:question_id>/delete/', views.admin_question_delete, name='admin_question_delete'),
    path('admin-portal/attempts/', views.admin_attempts_list, name='admin_attempts_list'),
]
