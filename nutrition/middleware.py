"""Middleware для переключения языков и темы."""


class LanguageMiddleware:
    """Устанавливает язык из сессии или определяет по Accept-Language заголовку."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем язык в сессии
        lang = request.session.get("django_language")
        if not lang:
            # Определяем язык по заголовку Accept-Language
            accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
            if "ru" in accept_language.lower():
                lang = "ru"
            else:
                lang = "en"
            request.session["django_language"] = lang

        # Устанавливаем язык в request
        request.LANGUAGE_CODE = lang

        # Тема: сначала cookie (переживает logout), затем session, иначе light.
        theme = (request.COOKIES.get("theme") or request.session.get("theme") or "light").strip().lower()
        theme = "dark" if theme == "dark" else "light"
        request.theme = theme  # удобный атрибут для шаблонов
        # синхронизируем сессию, если там пусто (не обязательно, но удобно)
        if request.session.get("theme") not in ("light", "dark"):
            request.session["theme"] = theme

        response = self.get_response(request)
        return response

