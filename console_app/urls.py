from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from console_app import views
from console_app.api import api_views

urlpatterns = [
    path('', views.home, name='home'),

    path('user-profile', views.user_profile, name='user_profile'),
    path('transaction_history', views.transaction_history, name='txn_history'),
    path('send_bundle/', views.send_bundle_page, name='send_bundle_page'),
    path("api-mgt", views.api_page, name="api_mgt"),
    path("crediting/", views.crediting_page, name="crediting"),
    path("credit-history/", views.credit_history, name="credit-history"),
    path("query_transaction/", views.query_transaction, name="query_transaction"),
    path("all_transactions/", views.all_transactions, name="all_transactions"),
    path('logout/', views.logout_user, name='logout'),
    path("password_reset/", views.password_reset_request, name="password_reset"),

    path('pending_approvals/', views.pending_approvals, name='pending_approvals'),
    path('approval_status/<int:approval_id>/<str:app_status>', views.change_approval_status, name='approval_status'),
    path('bundle-amount-graph/', views.bundle_amount_graph, name='bundle_amount_graph'),

    path('login/', views.loginpage, name='login'),
    path('sign-up', views.register, name='register'),

    # ========================================================================================================
    path('api/v1/new_transaction', api_views.new_transaction, name='new_transaction'),
    path('api/v1/transaction_detail', api_views.transaction_detail, name='transaction_detail'),
    path('api/v1/all_transactions', api_views.get_all_transactions, name='all_transactions'),
    path('api/v1/generate_token', api_views.generate_token, name='generate_token'),
    path('token_management', views.api_page, name='token_management')
]

