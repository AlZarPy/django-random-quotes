import random
from typing import Optional
from django.db.models import Sum, Case, When, IntegerField, F
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Quote, Vote, Source
from .forms import QuoteForm
from .models import AppSettings


def _ensure_session(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key

def _pick_weighted_quote(exclude_id: Optional[int] = None) -> Optional[Quote]:
    pairs = list(Quote.objects.values_list('id', 'weight'))
    if not pairs:
        return None
    if exclude_id is not None and len(pairs) > 1:
        pairs = [p for p in pairs if p[0] != exclude_id] or pairs
    ids, weights = zip(*pairs)
    chosen_id = random.choices(ids, weights=weights, k=1)[0]
    return Quote.objects.select_related('source').get(pk=chosen_id)

def _likes_count(q: Quote) -> tuple[int, int]:
    return (
        q.votes.filter(value=Vote.LIKE).count(),
        q.votes.filter(value=Vote.DISLIKE).count(),
    )

def home(request: HttpRequest) -> HttpResponse:
    last_id = request.GET.get('exclude')
    last_id_int = int(last_id) if last_id and last_id.isdigit() else None
    quote = _pick_weighted_quote(exclude_id=last_id_int)

    if quote:
        Quote.objects.filter(pk=quote.pk).update(views=F('views') + 1)
        likes, dislikes = _likes_count(quote)
        share_url = request.build_absolute_uri(reverse('quotes:detail', args=[quote.id]))
    else:
        likes = dislikes = 0
        share_url = None

    return render(request, 'quotes/home.html', {'quote': quote, 'likes': likes, 'dislikes': dislikes, 'share_url': share_url})

def random_partial(request: HttpRequest) -> HttpResponse:
    last_id = request.GET.get('exclude')
    last_id_int = int(last_id) if last_id and last_id.isdigit() else None
    quote = _pick_weighted_quote(exclude_id=last_id_int)
    if not quote:
        return HttpResponse('<div class="alert alert-info">Пока нет цитат. Добавьте первую!</div>')
    Quote.objects.filter(pk=quote.pk).update(views=F('views') + 1)
    likes, dislikes = _likes_count(quote)
    share_url = request.build_absolute_uri(reverse('quotes:detail', args=[quote.id]))
    return render(request, 'quotes/quote_partial.html', {'quote': quote, 'likes': likes, 'dislikes': dislikes, 'share_url': share_url})

def add_quote(request: HttpRequest) -> HttpResponse:
    cfg = AppSettings.get_solo()
    # если включено "добавлять могут только админы" — отправляем на логин админки
    if cfg.require_login_to_add and not (request.user.is_authenticated and request.user.is_staff):
        return redirect(f"/admin/login/?next={request.get_full_path()}")

    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save()
            return redirect('quotes:detail', pk=quote.pk)
    else:
        form = QuoteForm()

    return render(request, 'quotes/add.html', {'form': form})


def vote(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return HttpResponseBadRequest('Метод не поддерживается')
    quote_id = request.POST.get('quote_id')
    action = request.POST.get('action')
    if not quote_id or action not in ('like', 'dislike'):
        return HttpResponseBadRequest('Некорректные данные')

    session_key = _ensure_session(request)
    quote = get_object_or_404(Quote, pk=quote_id)
    value = Vote.LIKE if action == 'like' else Vote.DISLIKE
    obj, created = Vote.objects.get_or_create(quote=quote, session_key=session_key, defaults={'value': value})
    if not created and obj.value != value:
        obj.value = value
        obj.save(update_fields=['value'])
    return redirect('quotes:home')

def top_quotes(request: HttpRequest) -> HttpResponse:
    likes_annot = Sum(Case(When(votes__value=Vote.LIKE, then=1), default=0, output_field=IntegerField()))
    quotes = (Quote.objects.select_related('source')
              .annotate(likes=likes_annot)
              .order_by('-likes', '-views', '-created_at')[:10])
    return render(request, 'quotes/top.html', {'quotes': quotes})

def dashboard(request: HttpRequest) -> HttpResponse:
    kind = request.GET.get('kind')
    qs = Quote.objects.select_related('source')
    if kind in dict(Source.KIND_CHOICES):
        qs = qs.filter(source__kind=kind)

    likes_annot = Sum(Case(When(votes__value=Vote.LIKE, then=1), default=0, output_field=IntegerField()))
    dislikes_annot = Sum(Case(When(votes__value=Vote.DISLIKE, then=1), default=0, output_field=IntegerField()))

    most_viewed = qs.order_by('-views')[:10]
    most_liked = qs.annotate(likes=likes_annot).order_by('-likes')[:10]
    most_disliked = qs.annotate(dislikes=dislikes_annot).order_by('-dislikes')[:10]

    return render(request, 'quotes/dashboard.html', {
        'most_viewed': most_viewed,
        'most_liked': most_liked,
        'most_disliked': most_disliked,
        'kind': kind,
        'kinds': Source.KIND_CHOICES,
    })

# страница конкретной цитаты (permalink)
def quote_detail(request: HttpRequest, pk: int) -> HttpResponse:
    quote = get_object_or_404(Quote.objects.select_related('source'), pk=pk)
    Quote.objects.filter(pk=quote.pk).update(views=F('views') + 1)
    likes, dislikes = _likes_count(quote)
    share_url = request.build_absolute_uri(reverse('quotes:detail', args=[quote.id]))
    return render(request, 'quotes/home.html', {'quote': quote, 'likes': likes, 'dislikes': dislikes, 'share_url': share_url})

# API JSON
def api_random(request: HttpRequest) -> JsonResponse:
    quote = _pick_weighted_quote()
    if not quote:
        return JsonResponse({'ok': True, 'data': None})
    Quote.objects.filter(pk=quote.pk).update(views=F('views') + 1)
    likes, dislikes = _likes_count(quote)
    data = {
        'id': quote.id,
        'text': quote.text,
        'source': {'id': quote.source.id, 'title': quote.source.title, 'kind': quote.source.kind},
        'weight': quote.weight,
        'views': quote.views + 1,  # уже инкрементнули
        'likes': likes,
        'dislikes': dislikes,
        'permalink': request.build_absolute_uri(reverse('quotes:detail', args=[quote.id])),
    }
    return JsonResponse({'ok': True, 'data': data})

def api_top(request: HttpRequest) -> JsonResponse:
    try:
        limit = int(request.GET.get('limit', '10'))
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))
    likes_annot = Sum(Case(When(votes__value=Vote.LIKE, then=1), default=0, output_field=IntegerField()))
    qs = (Quote.objects.select_related('source')
          .annotate(likes=likes_annot)
          .order_by('-likes', '-views', '-created_at')[:limit])
    data = [{
        'id': q.id,
        'text': q.text,
        'source': {'id': q.source.id, 'title': q.source.title, 'kind': q.source.kind},
        'weight': q.weight,
        'views': q.views,
        'likes': getattr(q, 'likes', 0) or 0,
        'permalink': request.build_absolute_uri(reverse('quotes:detail', args=[q.id])),
    } for q in qs]
    return JsonResponse({'ok': True, 'count': len(data), 'data': data})

