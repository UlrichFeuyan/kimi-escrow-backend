from django.urls import path
from . import views

urlpatterns = [
    # Litiges
    path('', views.DisputeListCreateView.as_view(), name='dispute-list-create'),
    path('<int:pk>/', views.DisputeDetailView.as_view(), name='dispute-detail'),
    path('<int:pk>/assign/', views.AssignArbitreView.as_view(), name='assign-arbitre'),
    path('<int:pk>/resolve/', views.ResolveDisputeView.as_view(), name='resolve-dispute'),
    
    # Preuves
    path('<int:dispute_id>/evidence/', views.DisputeEvidenceCreateView.as_view(), name='dispute-evidence'),
    
    # Commentaires
    path('<int:dispute_id>/comments/', views.DisputeCommentListCreateView.as_view(), name='dispute-comments'),
    
    # Administration
    path('admin/statistics/', views.dispute_statistics, name='dispute-statistics'),
]

