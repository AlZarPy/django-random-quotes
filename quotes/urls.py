from django.urls import path
from . import views

app_name = 'quotes'

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_quote, name='add'),
    path('vote/', views.vote, name='vote'),
    path('top/', views.top_quotes, name='top'),
    path('random/', views.random_partial, name='random_partial'),

    path('dashboard/', views.dashboard, name='dashboard'), #дашборд цитат

    path('q/<int:pk>/', views.quote_detail, name='detail'), # страницы конкретной цитаты

    # API (JSON)
    path('api/random/', views.api_random, name='api_random'),
    path('api/top/', views.api_top, name='api_top'),
]
