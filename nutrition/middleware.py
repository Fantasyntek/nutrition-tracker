"""Middleware для переключения языков через сессию."""


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

        response = self.get_response(request)
        return response

