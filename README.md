# FitMacro Planner

Веб‑сервис для ведения дневника питания с автоматическим подсчётом **КБЖУ**, постановкой целей и просмотром прогресса (графики/прогноз). Есть импорт продуктов из внешнего API.

## Технологии
- **Python** 3.x
- **Django** 5.x
- **Requests** (интеграция с API)
- **Pandas** (агрегации/аналитика)
- **Plotly** (графики)
- **Tailwind CSS** (утилитарный CSS фреймворк)
- **shadcn/ui style** (дизайн-токены и компоненты на CSS variables + Tailwind, без React)
- **Flatpickr** (календарь)
- **Choices.js** (кастомные дропдауны)

## Установка и запуск (локально)

```bash
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте `http://127.0.0.1:8000/` и войдите в админ‑панель: `http://127.0.0.1:8000/admin/`.
