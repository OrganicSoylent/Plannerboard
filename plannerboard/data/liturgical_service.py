from datetime import date, timedelta


def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm for Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _last_sunday_on_or_before(d: date) -> date:
    return d - timedelta((d.weekday() + 1) % 7)


def get_liturgical_calendar(year: int) -> dict:
    """Return {date: feast_name} for traditional Catholic liturgical feasts."""
    feasts: dict[date, str] = {}

    def add(d: date, name: str):
        if d.year == year:
            feasts[d] = name

    e = _easter(year)

    # Pre-Lenten season (traditional calendar)
    add(e - timedelta(63), "Septuagesima Sunday")
    add(e - timedelta(56), "Sexagesima Sunday")
    add(e - timedelta(49), "Quinquagesima Sunday")

    # Lent
    add(e - timedelta(46), "Ash Wednesday")
    add(e - timedelta(42), "1st Sunday of Lent")
    add(e - timedelta(35), "2nd Sunday of Lent")
    add(e - timedelta(28), "3rd Sunday of Lent")
    add(e - timedelta(21), "Laetare Sunday")
    add(e - timedelta(14), "Passion Sunday")
    add(e - timedelta(7),  "Palm Sunday")

    # Holy Week
    add(e - timedelta(6), "Holy Monday")
    add(e - timedelta(5), "Holy Tuesday")
    add(e - timedelta(4), "Spy Wednesday")
    add(e - timedelta(3), "Holy Thursday")
    add(e - timedelta(2), "Good Friday")
    add(e - timedelta(1), "Holy Saturday")

    # Eastertide
    add(e,                  "Easter Sunday")
    add(e + timedelta(7),   "Divine Mercy Sunday")
    add(e + timedelta(39),  "Ascension Thursday")
    add(e + timedelta(49),  "Pentecost")
    add(e + timedelta(56),  "Trinity Sunday")
    add(e + timedelta(60),  "Corpus Christi")
    add(e + timedelta(68),  "Sacred Heart of Jesus")

    # Christ the King — last Sunday of October (traditional calendar)
    add(_last_sunday_on_or_before(date(year, 10, 31)), "Christ the King")

    # Advent
    xmas = date(year, 12, 25)
    adv1 = _last_sunday_on_or_before(xmas) - timedelta(21)
    add(adv1,                  "1st Sunday of Advent")
    add(adv1 + timedelta(7),   "2nd Sunday of Advent")
    add(adv1 + timedelta(14),  "Gaudete Sunday")
    add(adv1 + timedelta(21),  "4th Sunday of Advent")

    # Fixed feasts
    for month, day, name in [
        (1,  1,  "Solemnity of Mary"),
        (1,  6,  "Epiphany"),
        (2,  2,  "Candlemas"),
        (3,  19, "St. Joseph"),
        (3,  25, "Annunciation"),
        (6,  24, "Nativity of St. John the Baptist"),
        (6,  29, "Sts. Peter & Paul"),
        (8,  6,  "Transfiguration"),
        (8,  15, "Assumption"),
        (8,  22, "Queenship of Mary"),
        (9,  8,  "Nativity of Mary"),
        (9,  14, "Exaltation of the Holy Cross"),
        (9,  29, "St. Michael the Archangel"),
        (10, 2,  "Guardian Angels"),
        (11, 1,  "All Saints"),
        (11, 2,  "All Souls"),
        (12, 8,  "Immaculate Conception"),
        (12, 25, "Christmas"),
        (12, 26, "St. Stephen"),
        (12, 27, "St. John the Apostle"),
        (12, 28, "Holy Innocents"),
    ]:
        add(date(year, month, day), name)

    return feasts
