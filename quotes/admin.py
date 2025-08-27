from django.contrib import admin
from .models import Source, Quote, Vote, AppSettings
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'created_at')
    search_fields = ('title',)
    list_filter = ('kind',)

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'source', 'weight', 'views', 'created_at')
    list_filter = ('source__kind', 'source')
    search_fields = ('text',)

    def short_text(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('quote', 'session_key', 'value', 'created_at')
    list_filter = ('value',)
    search_fields = ('session_key',)

@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ('mode_badge', 'show_add_button', 'require_login_to_add')
    list_display_links = ('mode_badge',)
    readonly_fields = ('mode_text',)
    fieldsets = (
        (None, {
            'fields': ('mode_text',),
            'description': 'Сводка текущей конфигурации.'
        }),
        ('Кнопка «Добавить»', {
            'fields': ('show_add_button',),
            'description': 'Управляет видимостью кнопки в пользовательском интерфейсе.'
        }),
        ('Доступ к добавлению', {
            'fields': ('require_login_to_add',),
            'description': 'Если включено — добавлять могут только администраторы (через вход в /admin/).'
        }),
    )

    def mode_text(self, obj):
        return f'Текущий режим: {obj.current_mode()}'
    mode_text.short_description = 'Сводка'

    def mode_badge(self, obj):
        label = obj.current_mode()
        color = 'secondary' if label == 'Кнопка скрыта' else ('warning' if label == 'Только админы' else 'success')
        return format_html('<span class="badge bg-{}">{}</span>', color, label)
    mode_badge.short_description = 'Режим'

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if AppSettings.objects.exists():
            obj = AppSettings.get_solo()
            url = reverse('admin:quotes_appsettings_change', args=[obj.pk])
            return redirect(url)
        return super().changelist_view(request, extra_context)

