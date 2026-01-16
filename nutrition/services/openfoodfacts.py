from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class OffProduct:
    code: str
    name: str
    brand: str
    kcal_100g: float | None
    protein_100g: float | None
    fat_100g: float | None
    carbs_100g: float | None


class OpenFoodFactsClient:
    """
    Минимальный клиент OpenFoodFacts.
    Документация: https://openfoodfacts.github.io/api-documentation/
    """

    base_url = "https://world.openfoodfacts.org"

    def search(self, query: str, limit: int = 10) -> list[OffProduct]:
        query = (query or "").strip()
        if not query:
            return []

        # Django cache (optional)
        try:
            from django.core.cache import cache  # type: ignore
        except Exception:  # pragma: no cover
            cache = None

        cache_key = f"off:search:v2:{query.lower()}:{min(max(limit, 1), 30)}"
        if cache is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        headers = {"User-Agent": "FitMacroPlanner/1.0 (student project)"}

        # Ограничиваем поля ответа, чтобы ускорить загрузку
        fields = "code,product_name,generic_name,brands,nutriments"

        # Пробуем поиск с приоритетом российских продуктов
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": min(max(limit, 1), 30),
            "countries_tags_en": "russia",  # Приоритет российским продуктам
            "fields": fields,
        }
        url = f"{self.base_url}/cgi/search.pl"

        try:
            r = requests.get(url, params=params, timeout=8, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception:
            data = {"products": []}

        # Если результатов мало/нет — расширяем поиск без фильтра по стране
        if not (data.get("products") or []):
            params.pop("countries_tags_en", None)
            r = requests.get(url, params=params, timeout=8, headers=headers)
            r.raise_for_status()
            data = r.json()

        products = []
        for p in data.get("products", []) or []:
            code = str(p.get("code") or "").strip()
            if not code:
                continue

            nutr = p.get("nutriments") or {}
            products.append(
                OffProduct(
                    code=code,
                    name=str(p.get("product_name") or p.get("generic_name") or "Без названия").strip(),
                    brand=str(p.get("brands") or "").strip(),
                    kcal_100g=_to_float(nutr.get("energy-kcal_100g")),
                    protein_100g=_to_float(nutr.get("proteins_100g")),
                    fat_100g=_to_float(nutr.get("fat_100g")),
                    carbs_100g=_to_float(nutr.get("carbohydrates_100g")),
                )
            )

        if cache is not None:
            cache.set(cache_key, products, timeout=60 * 60 * 6)  # 6h
        return products

    def get_product(self, code: str) -> OffProduct | None:
        code = (code or "").strip()
        if not code:
            return None

        headers = {"User-Agent": "FitMacroPlanner/1.0 (student project)"}
        r = requests.get(f"{self.base_url}/api/v2/product/{code}.json", timeout=8, headers=headers)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != 1:
            return None

        p = data.get("product") or {}
        nutr = p.get("nutriments") or {}
        return OffProduct(
            code=code,
            name=str(p.get("product_name") or p.get("generic_name") or "Без названия").strip(),
            brand=str(p.get("brands") or "").strip(),
            kcal_100g=_to_float(nutr.get("energy-kcal_100g")),
            protein_100g=_to_float(nutr.get("proteins_100g")),
            fat_100g=_to_float(nutr.get("fat_100g")),
            carbs_100g=_to_float(nutr.get("carbohydrates_100g")),
        )


def _to_float(v) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


