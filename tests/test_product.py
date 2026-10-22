from app.product import product_from_html

HTML = '''<html><head><meta property="og:image" content="/img.jpg"><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product", "name":"Pantalón vaquero", "brand":{"name":"Example"},
"sku":"JEAN-123", "material":"cotton", "color":"navy", "image":["/a.jpg"],
"offers":{"@type":"Offer","price":"39.95","priceCurrency":"EUR","availability":"https://schema.org/InStock"},
"hasVariant":[{"@type":"Product","sku":"X-S", "size":"S", "color":"blue"},
{"@type":"Product","sku":"X-M", "size":"M", "color":"black"}]}
</script></head></html>'''


def test_jsonld_product_variants():
    p = product_from_html(HTML, {"title":"Fallback"}, "https://shop.example.org/jeans")
    assert p["name"] == "Pantalón vaquero"
    assert p["price"] == "39.95"
    assert p["currency"] == "EUR"
    assert p["sizes"] == ["S", "M"]
    assert p["color"] == ["navy", "blue", "black"]
    assert len(p["variants"]) == 2
    assert p["images"] == ["https://shop.example.org/a.jpg"]
    assert "fit" in p["missing_fields"]
    assert p["provenance"]["extraction"] == "deterministic_local"


def test_missing_attributes_not_hallucinated():
    p = product_from_html("<html></html>", {"title":"T-shirt"}, "https://example.org")
    assert p["name"] == "T-shirt"
    assert p["price"] is None
    assert p["sizes"] == []
    assert p["fit"] is None
    assert set(["price", "sizes", "fit"]).issubset(p["missing_fields"])


def test_broken_jsonld_fallback():
    p = product_from_html('<script type="application/ld+json">not json</script><meta property="og:title" content="Item">', {}, "https://example.org")
    assert p["name"] == "Item"
