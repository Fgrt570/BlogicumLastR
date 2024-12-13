from django.utils import timezone
from django.views.generic import (
    CreateView,
    UpdateView,
    DetailView,
)
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post
from .forms import PostForm
from blog.forms import PostForm, CommentForm, ProfileForm, PasswordChangeForm
from blog.models import Post, Category, Comment

User = get_user_model()
LIMIT_POSTS = 3  # Лимит на количество постов на странице


def profile_view(request, username):
    # Получаем пользователя по имени
    user = get_object_or_404(User, username=username)
    # Получаем все посты пользователя
    posts = user.posts.all()
    current_time = timezone.now()

    # Фильтрация постов для других пользователей (публикуются только те, что опубликованы и в правильной категории)
    if request.user.username != username:
        posts = posts.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=current_time,
        )

    paginator = Paginator(posts, LIMIT_POSTS)  # Пагинация
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)  # Получаем нужную страницу
    context = {
        "profile": user,
        "page_obj": page_obj,
    }
    return render(request, "blog/profile.html", context)  # Отправляем данные в шаблон


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "blog/user.html"

    def get_object(self, queryset=None):
        return self.request.user  # Возвращаем текущего пользователя

    def get_success_url(self):
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )  # После успешного обновления редирект на страницу профиля


@login_required
def password_change_view(request, username):
    user = request.user
    form = PasswordChangeForm(user, request.POST)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return redirect('blog:password_change_done')
    else:
        form = PasswordChangeForm(user)
    context = {'form': form}
    return render(request, 'blog/password_change_form.html', context)


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)  # Получаем пост по ID
    if request.user != post.author and (not post.is_published or not post.category.is_published):
        raise Http404()  # Проверка доступа к посту

    comments = post.comments.select_related('author')  # Получаем комментарии к посту
    form = CommentForm()  # Создаем форму комментария

    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }

    return render(request, 'blog/detail.html', context)

@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # Установить текущего пользователя как автора
            post.save()  # Сохранить пост
            return redirect('blog:post_detail', post_id=post.pk)  # Перенаправление на страницу деталей поста
    else:
        form = PostForm()  # Показать пустую форму для создания поста
    context = {'form': form}
    return render(request, "blog/create.html", context)

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)  # Получить пост по ID
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.pk)  # Проверка автора
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()  # Сохранить изменения в посте
            return redirect('blog:post_detail', post_id=post.pk)  # Перенаправление на страницу деталей поста
    else:
        form = PostForm(instance=post)  # Получить форму с существующими данными поста
    context = {'form': form, 'post': post, 'is_edit': True}
    return render(request, "blog/create.html", context)


@login_required
#Метод удаления поста
def delete_post(request, post_id):
    template_name = 'blog/create.html'
    #Получаем пост для удаления
    delete_post = get_object_or_404(Post, pk=post_id)
    # Если пользователь не является автором поста, редирект на профиль
    if delete_post.author != request.user:
        return redirect('blog:profile', request.user)
    # Если POST-запрос, удаляем пост
    if request.method == 'POST':
        delete_post.delete()
        return redirect('blog:profile', request.user)

    context = {
        'post': delete_post,
         'is_delete': True, #Флаг для отображения формы удаления
    }
    return render(request, template_name, context)


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self):
        object = super(PostDetailView, self).get_object()
        if self.request.user != object.author and (
            not object.is_published or not object.category.is_published
        ):
            raise Http404()
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


def index(request):
    template = 'blog/index.html'
    current_time = timezone.now()
    post = Post.objects.select_related('category').filter(
        pub_date__lte=current_time,
        is_published=True,
        category__is_published=True,
    )
    paginator = Paginator(post, LIMIT_POSTS)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    current_time = timezone.now()
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    post_list = category.posts.select_related('category').filter(
        is_published=True,
        pub_date__lte=current_time,
    )
    paginator = Paginator(post_list, LIMIT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, template, context)


@login_required
#Метод добавления комментария
def add_comment(request, post_id):
    # Получаем пост по его ID
    post = get_object_or_404(Post, pk=post_id)
    # Проверяем, была ли отправлена форма с методом POST
    if request.method == 'POST':
        return handle_comment_form(request, post)
    # Если метод не POST, перенаправляем на страницу с деталями поста
    return redirect('blog:post_detail', post_id)

def handle_comment_form(request, post):
    # Создаем форму
    form = CommentForm(request.POST)
    # Проверяем, валидна ли форма
    if form.is_valid():
        # Если форма валидна, сохраняем комментарий
        save_comment(form, request.user, post)
    return redirect('blog:post_detail', post.id)

def save_comment(form, user, post):
    # Создаем новый комментарий, не сохраняя его в базе данных сразу
    comment = form.save(commit=False)
    # Устанавливаем автора комментария
    comment.author = user
    # Устанавливаем пост, к которому относится комментарий
    comment.post = post
    # Сохраняем комментарий
    comment.save()

@login_required
#Метод редактирования комментария
def edit_comment(request, post_id, comment_id):
    # Получаем комментарий по его ID
    comment = get_object_or_404(Comment, id=comment_id)

    # Проверяем права доступа
    if not has_edit_permission(comment, request.user):
        return HttpResponseForbidden('У вас нет прав для редактирования этого комментария.')

    # Обработка формы
    if request.method == 'POST':
        return handle_post_request(request, comment, post_id)
    else:
        form = CommentForm(instance=comment)

    # Подготовка контекста и рендеринг шаблона
    context = {
        'form': form,
        'comment': comment,
        'is_edit': True,
    }
    return render(request, 'blog/comment.html', context)
# Проверка прав пользователя для редактирования комментария
def has_edit_permission(comment, user):
    return comment.author == user

# Обработка POST-запроса
def handle_post_request(request, comment, post_id):
    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    return form


@login_required
#Метод удаления комментария
def delete_comment(request, post_id, comment_id):
    # Получаем комментарий по ID, если его нет, возвращаем 404 ошибку
    comment = get_object_or_404(Comment, id=comment_id)

    # Проверяем, есть ли у пользователя права на удаление комментария
    if not has_permission_to_delete(comment, request.user):
        return HttpResponseForbidden(
            "У вас нет прав для удаления этого комментария."
        )

    # Если запрос был методом POST, выполняем удаление
    if request.method == "POST":
        return handle_comment_deletion(comment, post_id)

    # В остальных случаях отображаем страницу с подтверждением удаления
    context = {
        'comment': comment,
        'is_delete': True,
    }
    return render_delete_confirmation(request, context)

def has_permission_to_delete(comment, user):
    # Проверяем, что автор комментария совпадает с текущим пользователем
    return comment.author == user

def handle_comment_deletion(comment, post_id):
    # Удаляем комментарий и перенаправляем на страницу поста
    comment.delete()
    return redirect('blog:post_detail', post_id)

def render_delete_confirmation(request, context):
    # Отображаем страницу подтверждения удаления
    return render(request, 'blog/comment.html', context)

