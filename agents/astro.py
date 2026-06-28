"""Слоёная астрология на Swiss Ephemeris (локально, NASA/JPL точность).

Слои (как у проф-астрологов): глава жизни (Zodiacal Releasing, Firdaria) →
год (профекции + управитель года + соляр) → день (транзиты applying/separating,
электив: Луна, достоинства, управитель Асц, планетарные часы).

Каждая техника обёрнута в try/except: ошибка в одной не ломает остальные.
Возвращаем ФАКТЫ (числа), интерпретирует их Claude.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger("los.astro")

try:
    import swisseph as swe
    OK = True
except Exception:
    OK = False

UTC = ZoneInfo("UTC")
SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
         "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
# традиционные управители знаков (по индексу знака 0..11)
RULERS = ["Марс", "Венера", "Меркурий", "Луна", "Солнце", "Меркурий",
          "Венера", "Марс", "Юпитер", "Сатурн", "Сатурн", "Юпитер"]
LESSER = {"Сатурн": 30, "Юпитер": 12, "Марс": 15, "Солнце": 19,
          "Венера": 8, "Меркурий": 20, "Луна": 25}  # «малые годы» (для ZR)
EXALT = {"Солнце": 0, "Луна": 1, "Меркурий": 5, "Венера": 11,
         "Марс": 9, "Юпитер": 3, "Сатурн": 6}        # знак экзальтации
FIRD = {"Солнце": 10, "Венера": 8, "Меркурий": 13, "Луна": 9,
        "Сатурн": 11, "Юпитер": 12, "Марс": 7}        # годы фирдара
FIRD_DAY = ["Солнце", "Венера", "Меркурий", "Луна", "Сатурн", "Юпитер", "Марс"]
FIRD_NIGHT = ["Луна", "Сатурн", "Юпитер", "Марс", "Солнце", "Венера", "Меркурий"]
CHALDEAN = ["Сатурн", "Юпитер", "Марс", "Солнце", "Венера", "Меркурий", "Луна"]
WD_RULER = {0: "Луна", 1: "Марс", 2: "Меркурий", 3: "Юпитер",
            4: "Венера", 5: "Сатурн", 6: "Солнце"}     # пн..вс
ASPECTS = {0: "соединение", 60: "секстиль", 90: "квадрат", 120: "трин", 180: "оппозиция"}
BENEFICS = {"Венера", "Юпитер"}

if OK:
    PID = {"Солнце": swe.SUN, "Луна": swe.MOON, "Меркурий": swe.MERCURY,
           "Венера": swe.VENUS, "Марс": swe.MARS, "Юпитер": swe.JUPITER,
           "Сатурн": swe.SATURN, "Уран": swe.URANUS, "Нептун": swe.NEPTUNE,
           "Плутон": swe.PLUTO}
    TRANSIT = ["Солнце", "Луна", "Меркурий", "Венера", "Марс",
               "Юпитер", "Сатурн", "Уран", "Нептун", "Плутон"]


def _pos(jd, name):
    xx, _ = swe.calc_ut(jd, PID[name], swe.FLG_MOSEPH | swe.FLG_SPEED)
    return xx[0], xx[3]                     # долгота, скорость (°/сутки)


def _lon(jd, name):
    return _pos(jd, name)[0]


def _sign(lon):
    return f"{SIGNS[int(lon // 30) % 12]} {lon % 30:.0f}°"


def _jd(dt_utc):
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600)


def _natal_jd(birth):
    t = birth.get("time") or "12:00"
    d = datetime.strptime(f"{birth['date']} {t}", "%Y-%m-%d %H:%M")
    return _jd(d.replace(tzinfo=ZoneInfo(birth.get("tz") or "UTC")).astimezone(UTC))


def _age(birth, today):
    bd = datetime.strptime(birth["date"], "%Y-%m-%d").date()
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))


def _dignity(name, lon):
    s = int(lon // 30) % 12
    dom = [i for i in range(12) if RULERS[i] == name]
    if s in dom:
        return "в обители (силён)"
    if EXALT.get(name) == s:
        return "в экзальтации (силён)"
    if s in [(d + 6) % 12 for d in dom]:
        return "в изгнании (ослаблен)"
    if EXALT.get(name) is not None and s == (EXALT[name] + 6) % 12:
        return "в падении (ослаблен)"
    return "нейтрально"


def natal(birth):
    jd = _natal_jd(birth)
    pos = {n: _lon(jd, n) for n in TRANSIT}
    out = {"jd": jd, "pos": pos}
    try:
        lat, lon = float(birth["lat"]), float(birth["lon"])
        _, ascmc = swe.houses(jd, lat, lon, b"P")
        out["asc"] = ascmc[0]
        out["mc"] = ascmc[1]
        # секта: день, если Солнце над горизонтом
        try:
            az = swe.azalt(jd, swe.ECL2HOR, [lon, lat, 0], 0, 0, [pos["Солнце"], 0.0])
            out["day"] = az[1] > 0
        except Exception:
            out["day"] = 6 <= (datetime.strptime(birth.get("time", "12:00"), "%H:%M").hour) < 18
    except Exception as e:
        log.debug("natal houses: %s", e)
    return out


def _profections(nat, birth, today):
    age = _age(birth, today)
    asc_sign = int(nat["asc"] // 30)
    sign = (asc_sign + age % 12) % 12
    lord = RULERS[sign]
    lord_lon = nat["pos"].get(lord)
    return {"возраст": age, "дом_года": age % 12 + 1, "знак_года": SIGNS[sign],
            "управитель_года": lord,
            "управитель_в_знаке": (SIGNS[int(lord_lon // 30) % 12] if lord_lon is not None else "?")}


def _solar_return(nat, birth, now):
    natal_sun = nat["pos"]["Солнце"]
    bd = datetime.strptime(birth["date"], "%Y-%m-%d")
    y = now.year if (now.month, now.day) >= (bd.month, bd.day) else now.year - 1
    base = datetime(y, bd.month, bd.day, 12, tzinfo=UTC)

    def diff(jd):
        return ((_lon(jd, "Солнце") - natal_sun + 180) % 360) - 180

    j0 = _jd(base)
    lo, hi = j0 - 3, j0 + 3
    a = diff(lo)
    jd_sr = None
    x = lo
    while x < hi:
        b = diff(x + 0.25)
        if a == 0 or (a < 0 <= b) or (a > 0 >= b):
            x0, x1 = x, x + 0.25
            for _ in range(40):
                m = (x0 + x1) / 2
                if diff(x0) * diff(m) <= 0:
                    x1 = m
                else:
                    x0 = m
            jd_sr = (x0 + x1) / 2
            break
        a = b
        x += 0.25
    if jd_sr is None:
        return None
    res = {}
    try:
        lat, lon = float(birth["lat"]), float(birth["lon"])
        _, ascmc = swe.houses(jd_sr, lat, lon, b"P")
        res["асцендент_года"] = _sign(ascmc[0])
        # угловые планеты соляра (около Асц/MC ±6°)
        ang = []
        for n in ["Солнце", "Луна", "Меркурий", "Венера", "Марс", "Юпитер", "Сатурн"]:
            pl = _lon(jd_sr, n)
            for pt, lbl in ((ascmc[0], "Асц"), (ascmc[1], "MC")):
                d = abs((pl - pt + 180) % 360 - 180)
                if d <= 6:
                    ang.append(f"{n}@{lbl}")
        if ang:
            res["угловые"] = ang
    except Exception:
        pass
    res["дата"] = swe.revjul(jd_sr)[2]
    return res


def _transits(nat, now):
    jd = _jd(now.astimezone(UTC))
    targets = {"Солнце": nat["pos"]["Солнце"], "Луна": nat["pos"]["Луна"]}
    if "asc" in nat:
        targets["Асцендент"] = nat["asc"]
    out = []
    for tn in TRANSIT:
        tl, sp = _pos(jd, tn)
        for nn, nl in targets.items():
            d = abs((tl - nl + 180) % 360 - 180)
            for ang, an in ASPECTS.items():
                if abs(d - ang) <= 3:
                    # сходящийся/расходящийся: орб через сутки
                    tl2 = _lon(jd + 1, tn)
                    d2 = abs((tl2 - nl + 180) % 360 - 180)
                    appl = "сходящийся" if abs(d2 - ang) < abs(d - ang) else "расходящийся"
                    retro = " R" if sp < 0 else ""
                    out.append(f"{tn}{retro} {an} натальн. {nn} ({appl})")
    return out[:8]


def _moon_today(nat, now):
    jd = _jd(now.astimezone(UTC))
    sun, moon = _lon(jd, "Солнце"), _lon(jd, "Луна")
    d = (moon - sun) % 360
    phase = ("новолуние" if d < 22.5 or d >= 337.5 else "растущий серп" if d < 90
             else "первая четверть (растущая)" if d < 157.5 else "полнолуние" if d < 202.5
             else "убывающая Луна" if d < 270 else "последняя четверть")
    res = {"фаза": phase, "достоинство_луны": _dignity("Луна", moon)}
    # сходящиеся аспекты Луны сегодня (электив)
    appl = []
    for b in ("Солнце", "Меркурий", "Венера", "Марс", "Юпитер", "Сатурн"):
        bl = _lon(jd, b)
        dd = abs((moon - bl + 180) % 360 - 180)
        for ang, an in ASPECTS.items():
            if abs(dd - ang) <= 6:
                dd2 = abs((_lon(jd + 0.1, "Луна") - bl + 180) % 360 - 180)
                if abs(dd2 - ang) < abs(dd - ang):
                    good = "➕" if (an in ("трин", "секстиль") or b in BENEFICS) else "➖"
                    appl.append(f"{good} Луна {an} {b}")
    res["сходящиеся_аспекты_луны"] = appl or ["нет точных сходящихся аспектов"]
    return res


def _rise(jd, geo, flag):
    return swe.rise_trans(jd, swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER,
                          geo, 0.0, 0.0, flag)[1][0]


def _set(jd, geo, flag):
    return swe.rise_trans(jd, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER,
                          geo, 0.0, 0.0, flag)[1][0]


def _planetary_hours(now, lat=55.75, lon=37.62):
    jd0 = _jd(now.astimezone(UTC))
    geo = [lon, lat, 0]
    f = swe.FLG_MOSEPH
    r1 = _rise(jd0 - 1, geo, f)
    s1 = _set(r1, geo, f)
    r2 = _rise(s1, geo, f)
    if not (r1 <= jd0 < r2):
        r1 = _rise(jd0, geo, f); s1 = _set(r1, geo, f); r2 = _rise(s1, geo, f)
    if r1 <= jd0 < s1:
        idx = int((jd0 - r1) / ((s1 - r1) / 12)); daytime = True
    elif jd0 >= s1:
        idx = 12 + int((jd0 - s1) / ((r2 - s1) / 12)); daytime = False
    else:
        idx = 0; daytime = False
    day_ruler = WD_RULER[now.weekday()]
    hour_ruler = CHALDEAN[(CHALDEAN.index(day_ruler) + idx) % 7]
    return {"час_сейчас": hour_ruler, "управитель_дня": day_ruler,
            "сейчас": "день" if daytime else "ночь"}


def _lots(nat):
    asc, sun, moon = nat["asc"], nat["pos"]["Солнце"], nat["pos"]["Луна"]
    if nat.get("day", True):
        spirit = (asc + sun - moon) % 360
    else:
        spirit = (asc + moon - sun) % 360
    return spirit


def _zr_spirit(nat, birth, today):
    spirit = _lots(nat)
    age = _age(birth, today) + 0.5
    # L1 (годы)
    sign = int(spirit // 30)
    t = 0.0
    l1 = None
    for _ in range(40):
        yrs = LESSER[RULERS[sign]]
        if t <= age < t + yrs:
            l1 = (sign, t, t + yrs)
            break
        t += yrs
        sign = (sign + 1) % 12
    if not l1:
        return None
    l1_sign, l1_start, l1_end = l1
    # L2 (месяцы) внутри L1
    pos = l1_start + (age - l1_start)
    s2 = l1_sign
    tt = l1_start
    l2_sign = l1_sign
    for _ in range(200):
        months = LESSER[RULERS[s2]]
        step = months / 12.0
        if tt <= age < tt + step:
            l2_sign = s2
            break
        tt += step
        s2 = (s2 + 1) % 12
        if tt > l1_end:
            break
    return {"глава_L1": f"{SIGNS[l1_sign]} (упр. {RULERS[l1_sign]})",
            "L1_годы": f"{l1_start:.0f}–{l1_end:.0f} лет",
            "подпериод_L2": f"{SIGNS[l2_sign]} (упр. {RULERS[l2_sign]})"}


def _firdaria(nat, birth, today):
    age = _age(birth, today)
    order = FIRD_DAY if nat.get("day", True) else FIRD_NIGHT
    t = 0
    major = None
    for p in order:
        if t <= age < t + FIRD[p]:
            major = (p, t, FIRD[p])
            break
        t += FIRD[p]
    if not major:
        return None
    mp, mstart, mlen = major
    # подпериоды: 7 равных, порядок с управителя периода по кругу
    sub_len = mlen / 7
    si = order.index(mp)
    k = int((age - mstart) / sub_len)
    sub = order[(si + k) % 7]
    return {"период": mp, "подпериод": sub}


def facts(birth, now):
    """Полный набор астрофактов. Каждая техника — отдельно и под guard."""
    if not OK or not birth or not birth.get("date"):
        return {}
    today = now.date()
    out = {}
    try:
        nat = natal(birth)
    except Exception as e:
        log.warning("natal: %s", e)
        return {}
    try:
        out["натал"] = {"Солнце": _sign(nat["pos"]["Солнце"]),
                        "Луна": _sign(nat["pos"]["Луна"])}
        if "asc" in nat:
            out["натал"]["Асцендент"] = _sign(nat["asc"])
            out["натал"]["секта"] = "дневная" if nat.get("day") else "ночная"
    except Exception:
        pass
    for key, fn in (("транзиты", lambda: _transits(nat, now)),
                    ("луна_сегодня", lambda: _moon_today(nat, now)),
                    ("профекции_год", lambda: _profections(nat, birth, today)),
                    ("соляр_год", lambda: _solar_return(nat, birth, now)),
                    ("zodiacal_releasing", lambda: _zr_spirit(nat, birth, today)),
                    ("фирдар", lambda: _firdaria(nat, birth, today)),
                    ("планетарные_часы", lambda: _planetary_hours(now))):
        try:
            v = fn()
            if v:
                out[key] = v
        except Exception as e:
            log.debug("astro %s: %s", key, e)
    return out
