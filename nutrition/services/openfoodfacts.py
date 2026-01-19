from __future__ import annotations

from dataclasses import dataclass

import hashlib
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

    @staticmethod
    def _cache_key(prefix: str, *, query: str, limit: int) -> str:
        """
        Memcached-совместимый ключ (без пробелов/двоеточий/не-ASCII).
        Также избегаем слишком длинных ключей.
        """
        q = (query or "").strip().lower()
        qh = hashlib.sha256(q.encode("utf-8")).hexdigest()[:16]
        lim = min(max(limit, 1), 30)
        return f"{prefix}_v3_{qh}_{lim}"

    def search(self, query: str, limit: int = 10) -> list[OffProduct]:
        query = (query or "").strip()
        if not query:
            return []

        # Django cache (optional)
        try:
            from django.core.cache import cache  # type: ignore
        except Exception:  # pragma: no cover
            cache = None

        cache_key = self._cache_key("off_search", query=query, limit=limit)
        if cache is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        headers = {"User-Agent": "FitMacroPlanner/1.0 (student project)"}

        # Ограничиваем поля ответа, чтобы ускорить загрузку
        fields = "code,product_name,generic_name,brands,nutriments"

        url = f"{self.base_url}/cgi/search.pl"

        def _fetch(p: dict) -> dict:
            try:
                r = requests.get(url, params=p, timeout=10, headers=headers)
                r.raise_for_status()
                data = r.json()
                # Проверяем, что ответ валидный JSON и содержит поле products
                if not isinstance(data, dict):
                    return {"products": []}
                return data
            except requests.exceptions.Timeout:
                # Таймаут - возвращаем пустой результат, не падаем
                return {"products": []}
            except requests.exceptions.RequestException:
                # Ошибка сети/HTTP - возвращаем пустой результат, не падаем
                return {"products": []}
            except (ValueError, KeyError, TypeError):
                # Ошибка парсинга JSON - возвращаем пустой результат, не падаем
                return {"products": []}
            except Exception:
                # Любая другая ошибка - возвращаем пустой результат, не падаем
                return {"products": []}

        # Базовые параметры поиска
        base_params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": min(max(limit, 1), 30),
            "fields": fields,
        }
        
        # Пробуем поиск с приоритетом российских продуктов
        params_with_country = {**base_params, "countries_tags_en": "russia"}
        data = _fetch(params_with_country)
        
        # Если результатов нет — расширяем поиск без фильтра по стране
        if not (data.get("products") or []):
            data = _fetch(base_params)

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


