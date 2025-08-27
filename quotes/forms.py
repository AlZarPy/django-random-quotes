from django import forms
from django.db.models.functions import Lower
from .models import Quote, Source

def _normalize_spaces(text: str) -> str:
    # Убираем дубли пробелов и приводим к аккуратному виду
    return ' '.join(text.strip().split())

class QuoteForm(forms.ModelForm):
    # ↓↓↓ добавь/замени это поле
    source = forms.ModelChoiceField(
        queryset=Source.objects.all(),
        required=False,
        label='Источник'
    )

    new_source_title = forms.CharField(
        label='Новый источник (если не в списке)',
        required=False,
        max_length=255
    )
    new_source_kind = forms.ChoiceField(
        label='Тип нового источника',
        choices=Source.KIND_CHOICES,
        required=False
    )

    class Meta:
        model = Quote
        fields = ['text', 'source', 'weight']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Введите текст цитаты'}),
            'weight': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {'text': 'Текст цитаты', 'weight': 'Вес (чем больше — тем чаще выпадет)'}

    def clean_text(self):
        text = self.cleaned_data.get('text', '')
        return _normalize_spaces(text)

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get('source')
        new_title = cleaned.get('new_source_title')
        new_kind = cleaned.get('new_source_kind') or Source.OTHER

        # Создание нового источника, если заполнено поле
        if new_title and not source:
            title_norm = _normalize_spaces(new_title)
            source, _ = Source.objects.get_or_create(
                # регистронезависимая уникальность
                title=title_norm,
                kind=new_kind
            )
            cleaned['source'] = source
            self.cleaned_data['source'] = source  # гарантируем доступ в save()

        if not source:
            self.add_error('source', 'Выберите источник или создайте новый.')
            return cleaned

        # Ограничение в 3 цитаты на источник
        from .models import Quote as QuoteModel
        qs = QuoteModel.objects.filter(source=source)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.count() >= 3:
            self.add_error('source', 'У этого источника уже есть 3 цитаты.')

        # Проверка дубликатов (регистронезависимо, с нормализацией пробелов)
        text_norm = cleaned.get('text') or ''
        exists = QuoteModel.objects.filter(source=source).annotate(
            text_lower=Lower('text')
        ).filter(text_lower=text_norm.lower()).exists()
        if exists and not self.instance.pk:
            self.add_error('text', 'Такая цитата уже существует для этого источника.')

        # Валидируем вес
        weight = cleaned.get('weight') or 1
        if weight < 1:
            self.add_error('weight', 'Вес должен быть положительным числом.')

        return cleaned
