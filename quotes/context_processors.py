from .models import AppSettings

def app_settings(request):
    try:
        cfg = AppSettings.get_solo()
    except Exception:
        class _D:
            show_add_button = True
            require_login_to_add = False
        cfg = _D()

    can_add = bool(
        getattr(cfg, 'show_add_button', True) and (
            not getattr(cfg, 'require_login_to_add', False)
            or (request.user.is_authenticated and getattr(request.user, 'is_staff', False))
        )
    )
    return {'app_settings': cfg, 'can_add_quotes': can_add}
