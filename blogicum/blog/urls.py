from django.urls import path, re_path
from blog import views
app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'category/<slug:category_slug>/',
        views.category_posts,
        name='category_posts',
    ),
    path('profile/<username>/', views.profile_view, name='profile'),
    path(
        'profile/<slug:username>/edit_profile/',
        views.ProfileUpdateView.as_view(),
        name='edit_profile',
    ),
    path('posts/create/', views.post_create, name='create_post'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/edit/', views.edit_post, name='edit_post'),

    path('posts/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('posts/<int:post_id>/comment', views.add_comment, name='add_comment'),
    path(
        'posts/<int:post_id>/edit_comment/<int:comment_id>/',
        views.edit_comment,
        name='edit_comment',
    ),
    path(
        'posts/<int:post_id>/delete_comment/<int:comment_id>/',
        views.delete_comment,
        name='delete_comment',
    ),

]
