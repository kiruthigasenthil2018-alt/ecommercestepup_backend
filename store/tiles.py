import requests
from django.conf import settings
from django.http import Http404, HttpResponse

def tile(request, z, x, y):
    """Serves OpenStreetMap tiles through our own server (with a proper User-Agent) and caches them on disk."""
    if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z): raise Http404
    path = settings.BASE_DIR / "tilecache" / str(z) / str(x) / f"{y}.png"
    if not path.exists():
        try:
            r = requests.get(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png", timeout=8,
                             headers={"User-Agent": "StepUp-Ecommerce/1.0 (student shop project; contact stepup@gmail.com)"})
            if r.status_code != 200 or "image" not in r.headers.get("content-type", ""): return HttpResponse(status=502)
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(r.content)
        except requests.RequestException: return HttpResponse(status=502)
    return HttpResponse(path.read_bytes(), content_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
