"""Deterministic, source-labelled shopping product candidates (no paid AI)."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("value"))
    return None


def _product_nodes(obj: Any) -> Iterator[dict]:
    if isinstance(obj, list):
        for entry in obj:
            yield from _product_nodes(entry)
    elif isinstance(obj, dict):
        types = [str(x).lower().split("/")[-1] for x in _as_list(obj.get("@type"))]
        if "product" in types or "productgroup" in types:
            yield obj
        for key in ("@graph", "mainEntity", "hasPart", "itemListElement"):
            if key in obj:
                yield from _product_nodes(obj[key])


def _offer(source: dict) -> dict:
    offers = source.get("offers") or {}
    choices = [x for x in _as_list(offers) if isinstance(x, dict)]
    choice = choices[0] if choices else {}
    return {
        "price": _text(choice.get("price") or choice.get("lowPrice")),
        "currency": _text(choice.get("priceCurrency")),
        "availability": _text(choice.get("availability")),
    }


def _values_from_property(product: dict, target: str) -> list[str]:
    values: list[str] = []
    direct = _text(product.get(target))
    if direct:
        values.append(direct)
    for p in _as_list(product.get("additionalProperty")):
        if isinstance(p, dict) and (p.get("name") or "").lower() in ({"size", "talla", "tamaño"} if target == "size" else {"color", "colour"}):
            val = _text(p.get("value"))
            if val:
                values.append(val)
    return values


def product_from_html(html: str | None, metadata: dict | None, url: str) -> dict:
    soup = BeautifulSoup((html or "")[:4_000_000], "html.parser")
    metadata = metadata if isinstance(metadata, dict) else {}
    products: list[dict] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        try:
            products.extend(_product_nodes(json.loads(raw)))
        except (ValueError, TypeError):
            continue
    node = products[0] if products else {}
    meta: dict[str, str] = {}
    for item in soup.select("meta[property], meta[name]"):
        key = (item.get("property") or item.get("name") or "").lower()
        if key and item.get("content"):
            meta[key] = item["content"]
    variants = [x for x in _as_list(node.get("hasVariant")) if isinstance(x, dict)]
    sizes = _values_from_property(node, "size")
    colors = _values_from_property(node, "color")
    for variant in variants:
        sizes.extend(_values_from_property(variant, "size"))
        colors.extend(_values_from_property(variant, "color"))
    images = []
    for image in _as_list(node.get("image")):
        img = image.get("url") if isinstance(image, dict) else image
        if isinstance(img, str) and img.strip():
            images.append(urljoin(url, img.strip()))
    if not images and meta.get("og:image"):
        images.append(urljoin(url, meta["og:image"]))
    offer = _offer(node)
    if not offer["price"]:
        offer["price"] = _text(meta.get("product:price:amount"))
    if not offer["currency"]:
        offer["currency"] = _text(meta.get("product:price:currency"))
    title = _text(node.get("name")) or _text(meta.get("og:title")) or _text(metadata.get("title"))
    description = _text(node.get("description")) or _text(meta.get("description")) or _text(metadata.get("description"))
    unique = lambda xs: list(dict.fromkeys(x for x in xs if x))
    result = {
        "source_url": url,
        "name": title,
        "brand": _text(node.get("brand")),
        "description": description,
        "sku": _text(node.get("sku")),
        "category": _text(node.get("category")),
        "material": _text(node.get("material")),
        "color": unique(colors),
        "sizes": unique(sizes),
        "images": unique(images),
        "price": offer["price"],
        "currency": offer["currency"],
        "availability": offer["availability"],
        "variants": [{
            "sku": _text(v.get("sku")), "size": _text(v.get("size")),
            "color": _text(v.get("color")), "price": _offer(v)["price"]
        } for v in variants],
        "fit": None,
        "provenance": {
            "method": "jsonld" if node else ("html_metadata" if meta else "engine_metadata"),
            "extraction": "deterministic_local",
        },
    }
    result["missing_fields"] = [field for field in ("name", "brand", "price", "currency", "sizes", "material", "fit") if not result[field]]
    return result
