from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def tr(context, ru: str, en: str):
    """
    Простой перевод без gettext.
    Использование: {% tr ru="..." en="..." %}
    Язык берём из request.session['django_language'] (ru/en).
    """
    request = context.get("request")
    lang = None
    if request is not None:
        lang = request.session.get("django_language")
    return en if lang == "en" else ru


