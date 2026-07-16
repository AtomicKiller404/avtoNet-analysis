"""
avto.net URL Parameter Lookup Table
====================================
All values verified from real avto.net URLs + results page screenshots.

Confidence:
    ✓  confirmed — seen in real URL + matching screenshot/sidebar
    ~  inferred  — pattern-based, not screenshot-verified
    ?  unknown   — not yet confirmed

HOW THE URL WORKS
-----------------
Base: https://www.avto.net/Ads/results.asp  (GET params)

avto.net has TWO parallel ways to filter some fields:
  1. Main search params (oblika, bencin, starost) — set in the search form
  2. Sidebar sub-params (subDESIGN, subBENZL, subTRANS, subLOCATION)
     — appended by the results page sidebar. Can also be pre-applied in the URL.

For scraping: always prefer main params. Use sub* params only when the
main param doesn't cover the body type (karavan, kabriolet).

IMPORTANT QUIRKS
----------------
  letnikMax=2090    sentinel for "no upper year limit" (NOT blank, NOT 9999)
  kmMax=9999999     sentinel for "no upper km limit"
  kmMax=0           "only 0 km cars" (new/undriven)
  starost2=999      "any listing age" — always include this
  lokacija=100      special: Slovenia only (not a postal prefix)
  subLOCATION=99    special: foreign only (tujina)
  EQ4 = 9 digits    (100000000) all others 10 digits
  EQ12 = 120000000  9 digits, anomalous constant — hardcode as-is
  EQ9  pos[9]=2     always "required" — do not change
  EQ7  pos[8]=2     always "required" — do not change
  subTRANS=1        = AUTOMATIC (confirmed screenshot — counterintuitive)
  bencin uses 200-series when active (201=petrol, not 1)
  barva uses Slovenian colour names (URL-encoded, no diacritics)
"""

# ---------------------------------------------------------------------------
# RENT TYPE
# ---------------------------------------------------------------------------
RENT = {
    "prodam": 0,
    "oddam": 1,
}

# ---------------------------------------------------------------------------
# FUEL TYPE  — param: bencin
# ---------------------------------------------------------------------------
FUEL = {
    "vse":       0,
    "bencin":    201,
    "diesel":    202,
    "plin":      203,
    "hibrid":    205,
    "elektrika": 207,
    "lpg":       208,
    "cng":       209,
}
FUEL_LABEL = {v: k for k, v in FUEL.items()}

# ---------------------------------------------------------------------------
# VEHICLE AGE
# ---------------------------------------------------------------------------
AGE = {
    "vse":      0,
    "novo":     301,
    "testno":   302,
    "rabljeno": 303,
}
AGE_LABEL = {v: k for k, v in AGE.items()}

# ---------------------------------------------------------------------------
# BODY TYPE
# ---------------------------------------------------------------------------
SUB_DESIGN = {
    "vse":            0,
    "limuzina":       11,
    "kombilimuzina":  12,
    "karavan":        13,
    "enoprostorec":   14,
    "suv":            15,
    "coupe":          16,
    "cabrio":         17,
    "pickup":         18,
    "microcar":       19,

}
SUB_DESIGN_LABEL = {v: k for k, v in SUB_DESIGN.items()}

# ---------------------------------------------------------------------------
# TRANSMISSION 
# ---------------------------------------------------------------------------
TRANSMISSION = {
    "vse":        None,
    "avtomatski": 1,
    "rocni":      2,
}

# ---------------------------------------------------------------------------
# LOCATION
# ---------------------------------------------------------------------------
SUB_LOCATION = {
    "vse":           0,
    "ljubljana":     1,
    "maribor":       2,
    "celje":         3,
    "kranj":         4,
    "nova_gorica":   5,
    "koper":         6,
    "novo_mesto":    8,
    "murska_sobota": 9,
    "slovenija":     100,
    "tujina":        99,
}

SUB_LOCATION_LABEL = {v: k for k, v in SUB_LOCATION.items()}

# ---------------------------------------------------------------------------
# COLOUR  — param: barva  (exterior), barvaint  (interior)
# ---------------------------------------------------------------------------
COLOUR = {
    "vse":        None,
    "bela":       1,
    "crna":       2,
    "srebrna":    3,
    "modra":      4,
    "siva":       5,
    "rumena":     6,
    "rdeca":      7,
    "zelena":     8,
    "turkizna":   9,
    "beige":      10,
    "oranzna":    11,
    "rjava":      12,
    "vijolcna":   13,
    "zlata":      14,
}

# ---------------------------------------------------------------------------
# SELLER TYPE
# ---------------------------------------------------------------------------
SELLER = {
    "vse":           None,
    "fizicna_oseba": 0,
    "trgovec":       1,
}

# ---------------------------------------------------------------------------
# SORT ORDER  — params: presort + tipsort
# ---------------------------------------------------------------------------
SORT_BY = {
    "cena":   1,   # price          ~ inferred
    "datum":  3,   # date posted    ✓ used in all real URLs
    "km":     4,   # mileage        ~ inferred
    "letnik": 5,   # year           ~ inferred
}
SORT_DIR = {
    "desc": "DESC",  # newest/most expensive first  ✓
    "asc":  "ASC",   # oldest/cheapest first        ✓
}

# ---------------------------------------------------------------------------
# EQ FLAG CONSTANTS  — hardcode exactly as shown
# ---------------------------------------------------------------------------
EQ_DEFAULTS = {
    "EQ1":  "1000000000",
    "EQ2":  "1000000000",
    "EQ3":  "1000000000",
    "EQ4":  "100000000",
    "EQ5":  "1000000000",
    "EQ6":  "1000000000",
    "EQ7":  "1110100122",
    "EQ8":  "1010000000",
    "EQ9":  "1000000020",
    "EQ10": "1000000000",
    "EQ11": "1000000000",
    "EQ12": "120000000", 
}
EQ3_NAV_REQUIRED = "1002000000"  # confirmed from URL3

# ---------------------------------------------------------------------------
# STATIC PARAMS  — include in every request, values never change
# ---------------------------------------------------------------------------
STATIC_PARAMS = {
    "KAT":              "1010000000",  # personal cars category ✓
    "tip":              "",
    "znamka2": "", "model2": "", "tip2": "",
    "znamka3": "", "model3": "", "tip3": "",
    "modelID":          "",
    "motortakt":        "0",
    "motorvalji":       "0",
    "sirina":           "0",
    "dolzina":          "",
    "dolzinaMIN":       "0",
    "dolzinaMAX":       "100",
    "nosilnostMIN":     "0",
    "nosilnostMAX":     "999999",
    "sedezevMIN":       "0",
    "sedezevMAX":       "9",
    "lezisc":  "", "presek": "0", "premer": "0",
    "col":     "0", "vijakov": "0",
    "BkType":  "0", "BkOkvir": "0", "BkOkvirType": "0", "Bk4": "0",
    "EToznaka":         "0",
    "vozilo":           "",
    "airbag":           "",
    "barva":            "",
    "barvaint":         "",
    "doseg":            "0",
    "akcija":           "0",
    "paketgarancije":   "",
    "broker":           "0",
    "prikazkategorije": "0",
    "kategorija":       "0",
    "ONLvid":           "0",
    "ONLnak":           "0",
    "zaloga":           "10",   # 10=in stock; 0=all incl. unavailable
    "arhiv":            "0",
    "starost2":         "999",  # listing age sentinel — always 999
    "PIA": "", "PIAzero": "", "PIAOut": "", "PSLO": "",
}

# ---------------------------------------------------------------------------
# RANGE DEFAULTS  — "no limit" sentinel values
# ---------------------------------------------------------------------------
RANGE_DEFAULTS = {
    "letnikMin": 0,
    "letnikMax": 2090,      # ← sentinel, NOT blank or 9999  ✓
    "cenaMin":   0,
    "cenaMax":   999999,
    "kmMin":     0,
    "kmMax":     9999999,
    "ccmMin":    0,
    "ccmMax":    99999,
    "kwMin":     0,
    "kwMax":     999,
    "mocMin":    0,         # power in HP (separate from kW)
    "mocMax":    999999,
}

# ---------------------------------------------------------------------------
# STILL UNKNOWN — params not yet confirmed from real URLs
# ---------------------------------------------------------------------------
# Paste a URL with each filter active to decode these:
#
#  coupe oblika code         → select "Coupe" in search form → copy URL
#  microcar oblika code      → select "Microcar" → copy URL
#  subDESIGN=16,18,19        → unknown body types from earlier URLs
#  seller type param         → filter "fizična oseba" only → copy URL
#  EQ7 pos[1],[2],[4]        → tick one ownership box at a time → compare EQ7
#  subTRANS=2 = manual?      → click "ročni" in results sidebar → copy URL
#  diesel subBENZL code      → click "diesel" in results sidebar → copy URL
#  barva diacritics          → does barva=rdeca work or barva=rde%C4%8Da?