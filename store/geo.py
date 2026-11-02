import math, re, time
import requests

UA = {"User-Agent": "StepUp-Ecommerce/1.0 (student shop project; contact stepup@gmail.com)"}
def in_india(lat, lng): return 6.0 <= lat <= 37.7 and 68.0 <= lng <= 97.6

def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))

CITIES = {
 "chennai": (13.0827, 80.2707), "madras": (13.0827, 80.2707), "tambaram": (12.9249, 80.1000), "chengalpattu": (12.6819, 79.9888), "kanchipuram": (12.8342, 79.7036), "kancheepuram": (12.8342, 79.7036),
 "coimbatore": (11.0168, 76.9558), "madurai": (9.9252, 78.1198), "tiruchirappalli": (10.7905, 78.7047), "trichy": (10.7905, 78.7047), "tiruchi": (10.7905, 78.7047), "trichirappalli": (10.7905, 78.7047),
 "salem": (11.6643, 78.1460), "tirunelveli": (8.7139, 77.7567), "nellai": (8.7139, 77.7567), "tiruppur": (11.1085, 77.3411), "erode": (11.3410, 77.7172), "vellore": (12.9165, 79.1325),
 "thoothukudi": (8.7642, 78.1348), "tuticorin": (8.7642, 78.1348), "thanjavur": (10.7870, 79.1378), "tanjore": (10.7870, 79.1378), "dindigul": (10.3673, 77.9803), "cuddalore": (11.7480, 79.7714),
 "karur": (10.9601, 78.0766), "namakkal": (11.2189, 78.1674), "nagercoil": (8.1833, 77.4119), "kanyakumari": (8.0883, 77.5385), "kaniyakumari": (8.0883, 77.5385), "kanniyakumari": (8.0883, 77.5385),
 "tenkasi": (8.9604, 77.3152), "hosur": (12.7409, 77.8253), "krishnagiri": (12.5186, 78.2137), "dharmapuri": (12.1211, 78.1582), "pudukkottai": (10.3833, 78.8001), "sivakasi": (9.4533, 77.7979),
 "virudhunagar": (9.5680, 77.9624), "ramanathapuram": (9.3639, 78.8395), "theni": (10.0104, 77.4768), "nagapattinam": (10.7672, 79.8449), "kumbakonam": (10.9617, 79.3881), "pollachi": (10.6609, 77.0048),
 "ooty": (11.4102, 76.6950), "udhagamandalam": (11.4102, 76.6950), "tiruvannamalai": (12.2253, 79.0747), "villupuram": (11.9401, 79.4861), "viluppuram": (11.9401, 79.4861), "sivaganga": (9.8433, 78.4809),
 "pondicherry": (11.9416, 79.8083), "puducherry": (11.9416, 79.8083),
 "bengaluru": (12.9716, 77.5946), "bangalore": (12.9716, 77.5946), "mysuru": (12.2958, 76.6394), "mysore": (12.2958, 76.6394), "mangaluru": (12.9141, 74.8560), "mangalore": (12.9141, 74.8560),
 "hyderabad": (17.3850, 78.4867), "visakhapatnam": (17.6868, 83.2185), "vizag": (17.6868, 83.2185), "vijayawada": (16.5062, 80.6480),
 "kochi": (9.9312, 76.2673), "cochin": (9.9312, 76.2673), "ernakulam": (9.9816, 76.2999), "thiruvananthapuram": (8.5241, 76.9366), "trivandrum": (8.5241, 76.9366), "kozhikode": (11.2588, 75.7804), "calicut": (11.2588, 75.7804), "thrissur": (10.5276, 76.2144),
 "mumbai": (19.0760, 72.8777), "bombay": (19.0760, 72.8777), "pune": (18.5204, 73.8567), "nagpur": (21.1458, 79.0882), "ahmedabad": (23.0225, 72.5714), "surat": (21.1702, 72.8311),
 "delhi": (28.6139, 77.2090), "new delhi": (28.6139, 77.2090), "kolkata": (22.5726, 88.3639), "calcutta": (22.5726, 88.3639), "jaipur": (26.9124, 75.7873), "lucknow": (26.8467, 80.9462),
 "chandigarh": (30.7333, 76.7794), "bhopal": (23.2599, 77.4126), "indore": (22.7196, 75.8577), "patna": (25.5941, 85.1376), "bhubaneswar": (20.2961, 85.8245), "guwahati": (26.1445, 91.7362),
}
STATES = {
 "tamil nadu": (11.1271, 78.6569), "kerala": (10.8505, 76.2711), "karnataka": (15.3173, 75.7139), "andhra pradesh": (15.9129, 79.7400), "telangana": (18.1124, 79.0193),
 "maharashtra": (19.7515, 75.7139), "gujarat": (22.2587, 71.1924), "rajasthan": (27.0238, 74.2179), "uttar pradesh": (26.8467, 80.9462), "madhya pradesh": (22.9734, 78.6569),
 "delhi": (28.7041, 77.1025), "west bengal": (22.9868, 87.8550), "odisha": (20.9517, 85.0985), "bihar": (25.0961, 85.3131), "punjab": (31.1471, 75.3412), "haryana": (29.0588, 76.0856),
 "assam": (26.2006, 92.9376), "puducherry": (11.9416, 79.8083), "jharkhand": (23.6102, 85.2799), "chhattisgarh": (21.2787, 81.8661), "uttarakhand": (30.0668, 79.0193),
 "himachal pradesh": (31.1048, 77.1734), "goa": (15.2993, 74.1240), "jammu and kashmir": (33.7782, 76.5762),
}
STATE_ALIASES = {"tn": "tamil nadu", "tamilnadu": "tamil nadu", "pondicherry": "puducherry", "ap": "andhra pradesh", "andhra": "andhra pradesh", "ts": "telangana", "telengana": "telangana", "up": "uttar pradesh", "mp": "madhya pradesh", "wb": "west bengal", "kl": "kerala", "ka": "karnataka", "mh": "maharashtra", "new delhi": "delhi"}
PIN2 = {"11": "delhi", "12": "haryana", "13": "haryana", "14": "punjab", "15": "punjab", "16": "punjab", "17": "himachal pradesh", "18": "jammu and kashmir", "19": "jammu and kashmir",
 "20": "uttar pradesh", "21": "uttar pradesh", "22": "uttar pradesh", "23": "uttar pradesh", "24": "uttar pradesh", "25": "uttar pradesh", "26": "uttarakhand", "27": "uttar pradesh", "28": "uttar pradesh",
 "30": "rajasthan", "31": "rajasthan", "32": "rajasthan", "33": "rajasthan", "34": "rajasthan", "36": "gujarat", "37": "gujarat", "38": "gujarat", "39": "gujarat",
 "40": "maharashtra", "41": "maharashtra", "42": "maharashtra", "43": "maharashtra", "44": "maharashtra", "45": "madhya pradesh", "46": "madhya pradesh", "47": "madhya pradesh", "48": "madhya pradesh", "49": "chhattisgarh",
 "50": "telangana", "51": "andhra pradesh", "52": "andhra pradesh", "53": "andhra pradesh", "56": "karnataka", "57": "karnataka", "58": "karnataka", "59": "karnataka",
 "60": "tamil nadu", "61": "tamil nadu", "62": "tamil nadu", "63": "tamil nadu", "64": "tamil nadu", "67": "kerala", "68": "kerala", "69": "kerala",
 "70": "west bengal", "71": "west bengal", "72": "west bengal", "73": "west bengal", "74": "west bengal", "75": "odisha", "76": "odisha", "77": "odisha", "78": "assam", "79": "assam",
 "80": "bihar", "81": "bihar", "82": "bihar", "83": "jharkhand", "84": "bihar", "85": "jharkhand"}
PIN3_TN = {"600": "chennai", "601": "chennai", "602": "chennai", "603": "chengalpattu", "604": "villupuram", "605": "puducherry", "606": "tiruvannamalai", "607": "cuddalore", "608": "cuddalore", "609": "nagapattinam",
 "610": "vellore", "611": "nagapattinam", "612": "kumbakonam", "613": "thanjavur", "614": "thanjavur", "620": "tiruchirappalli", "621": "tiruchirappalli", "622": "pudukkottai", "623": "ramanathapuram", "624": "dindigul",
 "625": "madurai", "626": "virudhunagar", "627": "tirunelveli", "628": "thoothukudi", "629": "nagercoil", "630": "sivaganga", "631": "kanchipuram", "632": "vellore", "635": "krishnagiri", "636": "salem",
 "637": "namakkal", "638": "erode", "639": "karur", "641": "coimbatore", "642": "pollachi", "643": "ooty"}

_norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", (s or "").lower())).strip()

def _state(pin, state):
    s = _norm(state); s = re.sub(r"\bstate\b", "", s).strip(); s = STATE_ALIASES.get(s, s)
    return s if s in STATES else PIN2.get((pin or "")[:2], "")

def _city(city):
    c = re.sub(r"\b(city|district|dist|dt|town)\b", "", _norm(city)).strip(); c = re.sub(r"\s+", " ", c)
    if c in CITIES: return c, c
    first = c.split(" ")[0] if c else ""
    return (first, c) if first in CITIES else ("", c)

def _json(url, params, until):
    left = until - time.monotonic()
    if left <= 0.5: return None
    try:
        r = requests.get(url, params=params, headers=UA, timeout=min(3.5, left))
        return r.json() if r.ok else None
    except Exception: return None

def _locate(pin, city, state):
    until = time.monotonic() + 9; st = _state(pin, state); ckey, craw = _city(city)
    def ok(lat, lng, src):
        try: lat, lng = float(lat), float(lng)
        except (TypeError, ValueError): return None
        if not in_india(lat, lng): return None
        if st in STATES and km((lat, lng), STATES[st]) > 1100: return None   # wrong state / sea / other country
        return (lat, lng, src)
    if re.fullmatch(r"[1-9]\d{5}", pin or ""):
        j = _json("https://nominatim.openstreetmap.org/search", {"postalcode": pin, "country": "India", "format": "json", "limit": 1}, until)
        r = ok(j[0].get("lat"), j[0].get("lon"), "pincode") if isinstance(j, list) and j else None
        if r: return r
        j = _json(f"https://api.zippopotam.us/in/{pin}", None, until)
        p = (j or {}).get("places") if isinstance(j, dict) else None
        r = ok(p[0].get("latitude"), p[0].get("longitude"), "pincode") if p else None
        if r: return r
    if ckey:
        r = ok(*CITIES[ckey], "city")
        if r: return r
    if craw:
        j = _json("https://geocoding-api.open-meteo.com/v1/search", {"name": craw, "count": 5, "country_code": "IN", "language": "en", "format": "json"}, until)
        for x in ((j or {}).get("results") or []) if isinstance(j, dict) else []:
            r = ok(x.get("latitude"), x.get("longitude"), "city")
            if r: return r
        j = _json("https://nominatim.openstreetmap.org/search", {"q": f"{craw}, {state or ''}, India", "countrycodes": "in", "format": "json", "limit": 1}, until)
        r = ok(j[0].get("lat"), j[0].get("lon"), "city") if isinstance(j, list) and j else None
        if r: return r
    if st == "tamil nadu" and (pin or "")[:3] in PIN3_TN:
        r = ok(*CITIES[PIN3_TN[pin[:3]]], "district")
        if r: return r
    if st in STATES: return (*STATES[st], "state")
    from django.conf import settings
    return (settings.STORE["lat"], settings.STORE["lng"], "unknown")

_CACHE = {}
def locate(pincode="", city="", state=""):
    """Returns (lat, lng, source). source: pincode | city | district | state | unknown. Never lands in the sea."""
    key = (re.sub(r"\D", "", pincode or "")[:6], (city or "").strip().lower()[:60], (state or "").strip().lower()[:40])
    if key in _CACHE: return _CACHE[key]
    res = _locate(*key)
    if res[2] in ("pincode", "city", "district"): _CACHE[key] = res
    return res

def geocode(*parts):  # kept for compatibility
    r = locate("", parts[-2] if len(parts) > 1 else parts[0], parts[-1] if len(parts) > 1 else "")
    return (r[0], r[1])

def courier_pos(o):
    """Admin / courier GPS position wins; otherwise interpolate store -> customer by order status."""
    from django.conf import settings
    if o.current_lat is not None: return {"lat": o.current_lat, "lng": o.current_lng}
    if o.dest_lat is None: return None
    t = {"confirmed": 0, "shipped": .25, "out_for_delivery": .75, "delivered": 1, "cancelled": 0}.get(o.status, 0); s = settings.STORE
    return {"lat": s["lat"] + (o.dest_lat - s["lat"]) * t, "lng": s["lng"] + (o.dest_lng - s["lng"]) * t}
