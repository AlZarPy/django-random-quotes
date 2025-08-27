from django.db import models
from django.db.models import UniqueConstraint, Q, F
from django.db.models.functions import Lower

class Source(models.Model):
    MOVIE = 'movie'
    BOOK = 'book'
    OTHER = 'other'
    KIND_CHOICES = [
        (MOVIE, 'Фильм'),
        (BOOK, 'Книга'),
        (OTHER, 'Другое'),
    ]
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=OTHER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(Lower('title'), 'kind', name='uq_source_title_kind_ci')
        ]

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"


class Quote(models.Model):
    text = models.TextField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='quotes')
    weight = models.PositiveIntegerField(default=1)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(Lower('text'), 'source', name='uq_quote_text_source_ci')
        ]

    def clean(self):
        # Ограничение: не более 3 цитат на источник
        if self.source_id:
            qs = Quote.objects.filter(source=self.source).exclude(pk=self.pk)
            if qs.count() >= 3:
                from django.core.exceptions import ValidationError
                raise ValidationError('У этого источника уже есть 3 цитаты.')

    def __str__(self):
        return f"{self.text[:50]}..."


class Vote(models.Model):
    LIKE = 1
    DISLIKE = -1
    VALUE_CHOICES = [
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    ]
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='votes')
    session_key = models.CharField(max_length=40)
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['quote', 'session_key'], name='uq_vote_quote_session')
        ]

    def __str__(self):
        return f"{self.session_key} -> {self.quote_id}: {self.value}"


class AppSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    show_add_button = models.BooleanField(
        'Показывать кнопку «Добавить»',
        default=True,
        help_text='Управляет видимостью кнопки «Добавить» в интерфейсе.'
    )
    require_login_to_add = models.BooleanField(
        'Добавлять могут только админы',
        default=False,
        help_text='Если включено — добавлять цитаты могут только администраторы после входа в /admin/.'
    )

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def current_mode(self) -> str:
        if not self.show_add_button:
            return 'Кнопка скрыта'
        return 'Только админы' if self.require_login_to_add else 'Открыто для всех'

    class Meta:
        verbose_name = 'Настройки приложения'
        verbose_name_plural = 'Настройки приложения'

