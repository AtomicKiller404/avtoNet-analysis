import glob
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

plt.style.use("seaborn-v0_8-whitegrid")

PRICE_STEP = 1000

# No duplicates — "Skoda"/"Citroen" removed in favour of diacritic versions
MAKE_ORDER = [
    "Mercedes-Benz",
    "Volkswagen",
    "BMW",
    "Audi",
    "Škoda",
    "Opel",
    "Ford",
    "Renault",
    "Peugeot",
    "Citroën",
    "Toyota",
    "Nissan",
    "Hyundai",
    "Kia",
    "Volvo",
    "Mazda",
    "Honda",
    "Fiat",
    "Suzuki",
    "Dacia",
    "Jeep",
    "Mini",
    "Lexus",
    "Subaru",
    "Mitsubishi",
    "Porsche",
    "Jaguar",
    "Tesla",
    "Cupra",
    "Land Rover",
    "Alfa Romeo",
    "DS",
    "Seat",
]

BODY_LABELS = ["SUV", "Sedan", "Hatchback", "Wagon", "MPV/Van", "Coupe", "Cabrio", "Pickup", "Microcar", "Other"]

BODY_MAP = {
    "suv": "SUV",
    "terensko vozilo": "SUV",
    "limuzina": "Sedan",
    "sedan": "Sedan",
    "kombilimuzina": "Hatchback",
    "hatchback": "Hatchback",
    "karavan": "Wagon",
    "wagon": "Wagon",
    "estate": "Wagon",
    "enoprostorec": "MPV/Van",
    "minivan": "MPV/Van",
    "coupe": "Coupe",
    "cabrio": "Cabrio",
    "convertible": "Cabrio",
    "pickup": "Pickup",
    "microcar": "Microcar",
}

# Title-level hints for avto.net listings (checked in order, longest/most specific first)
_BODY_HINTS = [
    # MPV/Van — specific model names (longer patterns first)
    ("grand scenic",    "MPV/Van"),
    ("grand picasso",   "MPV/Van"),
    ("grand c-max",     "MPV/Van"),
    ("partner tepee",   "MPV/Van"),
    ("active tourer",   "MPV/Van"),
    ("berlingo",        "MPV/Van"),
    ("scenic",          "MPV/Van"),
    ("picasso",         "MPV/Van"),
    ("zafira",          "MPV/Van"),
    ("touran",          "MPV/Van"),
    ("sharan",          "MPV/Van"),
    ("galaxy",          "MPV/Van"),
    ("carens",          "MPV/Van"),
    ("c-max",           "MPV/Van"),
    # SUV — specific model names
    ("peugeot 2008",    "SUV"),
    ("peugeot 3008",    "SUV"),
    ("peugeot 5008",    "SUV"),
    ("x-trail",         "SUV"),
    ("tiguan",          "SUV"),
    ("tucson",          "SUV"),
    ("qashqai",         "SUV"),
    ("sportage",        "SUV"),
    ("kuga",            "SUV"),
    ("karoq",           "SUV"),
    ("kodiaq",          "SUV"),
    ("t-roc",           "SUV"),
    ("t-cross",         "SUV"),
    ("ix35",            "SUV"),
    ("rav4",            "SUV"),
    ("captur",          "SUV"),
    ("crossland",       "SUV"),
    ("500x",            "SUV"),
    ("4x4",             "SUV"),
    # Wagon — common title suffixes/identifiers (longer patterns first)
    ("grandtour",       "Wagon"),
    ("grand tour",      "Wagon"),
    ("combi",           "Wagon"),
    ("variant",         "Wagon"),
    (" sw ",            "Wagon"),
    ("touring",         "Wagon"),
    ("tourer",          "Wagon"),
    ("sportbrake",      "Wagon"),
    # Hatchback
    ("sportback",       "Hatchback"),
    # Cabrio
    ("cabriolet",       "Cabrio"),
    # Van (word-boundary guarded — must be preceded by a space)
    (" van ",           "MPV/Van"),
]

FUEL_MAP = {
    "diesel": "Diesel",
    "bencin": "Petrol",
    "petrol": "Petrol",
    "hibrid": "Hybrid",
    "hybrid": "Hybrid",
    "elektr": "Electric",
    "ev": "Electric",
    "lpg": "LPG",
    "cng": "CNG",
    "plin": "Gas",
}

FUEL_COLORS = {
    "Diesel": "#2563eb",
    "Petrol": "#f97316",
    "Hybrid": "#16a34a",
    "Electric": "#7c3aed",
    "LPG": "#8b5cf6",
    "CNG": "#0f766e",
    "Gas": "#a855f7",
    "Other": "#64748b",
}

# Commercial keywords that identify dealer sellers
_DEALER_TOKENS = ["d.o.o", "s.p.", "d.d.", "j.v.s.", "k.d.", "avtocenter",
                  "auto center", "salon", "salona", "prodajna", "auto d"]


def load_latest(data_dir="data/"):
    files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not files:
        raise FileNotFoundError(f"No CSV files in {data_dir}")
    path = files[-1]
    print(f"Loading {path}")
    return pd.read_csv(path)


def filter_df(df, brand=None, model=None):
    if brand:
        mask = df["title"].str.contains(brand, case=False, na=False)
        if "make" in df.columns:
            mask = mask | df["make"].str.contains(brand, case=False, na=False)
        df = df[mask]
    if model:
        mask = df["title"].str.contains(model, case=False, na=False)
        if "model_guess" in df.columns:
            mask = mask | df["model_guess"].str.contains(model, case=False, na=False)
        df = df[mask]
    return df


def parse_price(val):
    if pd.isna(val):
        return np.nan
    cleaned = re.sub(r"[^0-9.]", "", str(val).replace(",", ".").split("€")[0])
    try:
        return float(cleaned) if cleaned else np.nan
    except ValueError:
        return np.nan


def parse_km(val):
    if pd.isna(val):
        return np.nan
    match = re.search(r"[\d.]+", str(val))
    return float(match.group().replace(".", "")) if match else np.nan


def parse_year(val):
    if pd.isna(val):
        return np.nan
    match = re.search(r"\d{4}", str(val))
    return float(match.group()) if match else np.nan


def parse_kw(val):
    if pd.isna(val):
        return np.nan
    match = re.search(r"(\d+)\s*kW", str(val), flags=re.IGNORECASE)
    return float(match.group(1)) if match else np.nan


def normalize_text(value):
    return (
        str(value or "")
        .lower()
        .replace("č", "c")
        .replace("š", "s")
        .replace("ž", "z")
        .replace("ć", "c")
        .replace("đ", "d")
    )


def normalize_fuel(value):
    text = normalize_text(value)
    for key, label in FUEL_MAP.items():
        if key in text:
            return label
    return "Other"


def infer_make(title):
    text = str(title or "").strip()
    if not text:
        return "Unknown"
    lowered = normalize_text(text)
    for make in sorted(MAKE_ORDER, key=len, reverse=True):
        if lowered.startswith(normalize_text(make)):
            return make
    return text.split()[0]


def infer_model(title, make):
    text = str(title or "").strip()
    if not text:
        return "Unknown"
    remainder = re.sub(rf"^{re.escape(make)}\s*", "", text, flags=re.IGNORECASE).strip()
    remainder = re.split(r"[|,:/\-]", remainder)[0].strip()
    tokens = [t for t in remainder.split() if t]
    return " ".join(tokens[:2]) if tokens else "Unknown"


def infer_body_type(text):
    lowered = normalize_text(text)
    for key, label in _BODY_HINTS:
        if key in lowered:
            return label
    # "avant" → Wagon (Audi Avant), guarded against "avantgarde" trim name
    if " avant" in lowered and "avantgarde" not in lowered:
        return "Wagon"
    for key, label in BODY_MAP.items():
        if key in lowered:
            return label
    return "Other"


def classify_seller(row):
    """
    Dealer signals (requires fetch_details: true):
      1. internal_number is set (dealers use stock/internal numbers)
      2. seller_name contains a commercial suffix/keyword
    If seller_name is present but has no commercial markers → Private.
    Falls back to "Unknown" when neither field is available.
    """
    internal = row.get("internal_number")
    if pd.notna(internal) and str(internal).strip():
        return "Dealer"

    name = row.get("seller_name")
    if pd.notna(name) and str(name).strip() and str(name).strip().lower() != "nan":
        name_norm = normalize_text(str(name))
        if any(t in name_norm for t in _DEALER_TOKENS):
            return "Dealer"
        return "Private"

    return "Unknown"


def pretty_money(value):
    if pd.isna(value):
        return "—"
    return f"€{float(value):,.0f}".replace(",", " ")


def pretty_int(value):
    if pd.isna(value):
        return "—"
    return f"{int(round(float(value))):,}".replace(",", " ")


def enrich(df):
    df = df.copy()

    # Handle both new (numeric) and old (string) CSV formats for price and km
    if pd.api.types.is_numeric_dtype(df["price"]):
        df["price_eur"] = df["price"].astype(float)
    else:
        df["price_eur"] = df["price"].apply(parse_price)

    if pd.api.types.is_numeric_dtype(df["km"]):
        df["km_num"] = df["km"].astype(float)
    else:
        df["km_num"] = df["km"].apply(parse_km)

    df["year_num"]    = df["year"].apply(parse_year)
    df["kw_num"]      = df["engine"].apply(parse_kw)
    df["make"]        = df["title"].apply(infer_make)
    df["model_guess"] = [infer_model(t, m) for t, m in zip(df["title"], df["make"])]

    # Detect whether the CSV was produced with fetch_details: true
    has_detail = "body_shape" in df.columns

    if has_detail:
        # Prefer detail body_shape; fall back to title inference
        df["body_type"] = [
            infer_body_type(bs if (isinstance(bs, str) and bs) else title)
            for bs, title in zip(df["body_shape"].fillna(""), df["title"])
        ]
        # Prefer detail fuel over listing-card fuel
        if "fuel_detail" in df.columns:
            df["fuel_norm"] = [
                normalize_fuel(fd if (isinstance(fd, str) and fd) else fu)
                for fd, fu in zip(df["fuel_detail"].fillna(""), df["fuel"])
            ]
        else:
            df["fuel_norm"] = df["fuel"].apply(normalize_fuel)
        # Classify sellers using signals available in detail data
        has_seller_data = "internal_number" in df.columns or "seller_name" in df.columns
        df["seller_type"] = df.apply(classify_seller, axis=1) if has_seller_data else "Unknown"
    else:
        df["fuel_norm"]   = df["fuel"].apply(normalize_fuel)
        df["body_type"]   = df["title"].apply(infer_body_type)
        df["seller_type"] = "Unknown"

    # Value scoring
    df["make_model_median"] = df.groupby(["make", "model_guess"])["price_eur"].transform("median")
    df["price_gap"]         = df["make_model_median"] - df["price_eur"]

    yr_range = df["year_num"].max() - df["year_num"].min() + 1
    km_range = df["km_num"].max()   - df["km_num"].min()   + 1
    gp_range = df["price_gap"].max() - df["price_gap"].min() + 1

    year_norm     = (df["year_num"]  - df["year_num"].min())  / yr_range
    km_norm       = (df["km_num"]    - df["km_num"].min())    / km_range
    discount_norm = (df["price_gap"] - df["price_gap"].min()) / gp_range

    df["value_score"] = 0.35 * (1 - year_norm) + 0.35 * (1 - km_norm) + 0.30 * discount_norm

    return df


def add_trend_residuals(df):
    df = df.copy()
    valid = df[["km_num", "price_eur"]].dropna()
    if len(valid) < 3:
        df["residual"] = np.nan
        return df
    coeffs = np.polyfit(valid["km_num"], valid["price_eur"], 1)
    df["trend_price"] = coeffs[0] * df["km_num"] + coeffs[1]
    df["residual"]    = df["price_eur"] - df["trend_price"]
    return df


def top_listings(df, body_filter="All"):
    data = df.dropna(subset=["value_score", "price_eur", "year_num", "km_num"])
    if body_filter != "All":
        data = data[data["body_type"] == body_filter]
    if data.empty:
        return data
    base_cols = ["title", "make", "model_guess", "body_type", "year_num", "km_num",
                 "price_eur", "make_model_median", "price_gap", "value_score",
                 "seller_type", "on_sale", "url"]
    cols = [c for c in base_cols if c in data.columns]
    return data.sort_values("value_score", ascending=False).head(50)[cols].reset_index(drop=True)


def brand_choices(df):
    values = [v for v in df["make"].dropna().unique().tolist() if v not in {"Unknown", "Other"}]
    return ["All"] + sorted(values, key=lambda item: item.lower())


# ---------------------------------------------------------------------------
# Pure plot functions — each takes an enriched DataFrame and returns a Figure
# ---------------------------------------------------------------------------

def plot_price_vs_mileage(df):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["km_num", "price_eur"])
    if data.empty:
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
        ax.axis("off")
        return fig

    data = add_trend_residuals(data)
    bargain_cut = data["residual"].quantile(0.15) if data["residual"].notna().any() else np.nan

    for fuel in ["Diesel", "Petrol", "Hybrid", "Electric", "LPG", "CNG", "Gas", "Other"]:
        subset = data[data["fuel_norm"] == fuel]
        if subset.empty:
            continue
        ax.scatter(subset["km_num"], subset["price_eur"], s=30, alpha=0.7,
                   color=FUEL_COLORS.get(fuel, FUEL_COLORS["Other"]), label=fuel)

    if data["residual"].notna().any():
        bargain = data[data["residual"] <= bargain_cut]
        ax.scatter(bargain["km_num"], bargain["price_eur"], s=115, marker="*",
                   color="#111827", edgecolor="white", linewidth=0.6, label="Bargain (bottom 15%)")

    # Highlight on_sale listings (from new scraper output)
    if "on_sale" in data.columns:
        sale = data[data["on_sale"] == True]
        if not sale.empty:
            ax.scatter(sale["km_num"], sale["price_eur"], s=90, marker="D",
                       color="gold", edgecolor="#111827", linewidth=0.7, zorder=5, label="On sale")

    xs = np.linspace(data["km_num"].min(), data["km_num"].max(), 200)
    coeffs = np.polyfit(data["km_num"], data["price_eur"], 1)
    ax.plot(xs, coeffs[0] * xs + coeffs[1], color="#111827", linewidth=2, alpha=0.75)
    ax.set_title("Price vs mileage scatter by fuel type")
    ax.set_xlabel("Mileage (km)")
    ax.set_ylabel("Price (€)")
    ax.legend(loc="best", ncols=2, frameon=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_depreciation_by_make(df):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["make", "year_num", "price_eur"])
    if data.empty:
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
        ax.axis("off")
        return fig

    top_makes = data["make"].value_counts().head(10).index.tolist()
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_makes)))
    for color, make in zip(colors, top_makes):
        make_data = data[data["make"] == make]
        counts = make_data.groupby("year_num")["price_eur"].count()
        series = make_data.groupby("year_num")["price_eur"].median().sort_index()
        series = series[counts >= 2]
        if series.empty:
            continue
        ax.plot(series.index, series.values, marker="o", linewidth=2, color=color, label=make)
    ax.set_title("Depreciation curve by make  (years with ≥2 listings)")
    ax.set_xlabel("Registration year")
    ax.set_ylabel("Median price (€)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
    ax.tick_params(axis="x", rotation=45)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: str(int(x))))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_km_heatmap(df):
    """Median mileage heatmap: make × price bracket — shows typical km for a price point."""
    fig, ax = plt.subplots(figsize=(13, 8))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["make", "price_eur", "km_num"])
    if data.empty:
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        ax.axis("off")
        return fig

    top_makes = data["make"].value_counts().head(12).index.tolist()
    data = data[data["make"].isin(top_makes)].copy()
    data["price_bucket"] = (data["price_eur"] // (2 * PRICE_STEP)).astype(int) * (2 * PRICE_STEP)
    pivot = (
        data.pivot_table(index="make", columns="price_bucket", values="km_num", aggfunc="median")
        .reindex(top_makes)
    )
    pivot = pivot.sort_index(axis=1)
    if pivot.empty or pivot.isnull().all().all():
        ax.text(0.5, 0.5, "Not enough data for heatmap", ha="center", va="center")
        ax.axis("off")
        return fig

    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn_r")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"€{int(col / 1000)}k" for col in pivot.columns], rotation=45, ha="right")
    ax.set_title("Median mileage heatmap — make × price bracket  (red = high km, green = low km)")
    ax.set_xlabel("Price bracket")
    ax.set_ylabel("Make")
    fig.colorbar(im, ax=ax, label="Median mileage (km)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{int(val / 1000)}k", ha="center", va="center",
                        fontsize=7, color="black", fontweight="bold")
    return fig


def plot_price_histogram(df):
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.tight_layout(pad=2)
    prices = df["price_eur"].dropna()
    if prices.empty:
        ax.text(0.5, 0.5, "No price data", ha="center", va="center")
        ax.axis("off")
        return fig
    min_price = int(prices.min() // PRICE_STEP) * PRICE_STEP
    max_price = int(np.ceil(prices.max() / PRICE_STEP) * PRICE_STEP)
    bins = np.arange(min_price, max_price + PRICE_STEP, PRICE_STEP)
    counts, edges = np.histogram(prices, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    ax.bar(centers, counts, width=PRICE_STEP * 0.85, color="#2c7fb8")
    ax.set_title("Sweet spot histogram — volume by price bracket")
    ax.set_xlabel("Price bracket")
    ax.set_ylabel("Listings")
    ax.set_xlim(left=min_price - PRICE_STEP, right=max_price + PRICE_STEP)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"€{int(x / 1000)}k"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_brand_model_prices(df, brand="All"):
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.tight_layout(pad=2)
    if brand == "All":
        data   = df.dropna(subset=["make", "price_eur"]).copy()
        groups = data["make"].value_counts().head(10).index.tolist()
        title  = "Price distribution by brand"
        xlabel = "Brand"
    else:
        data   = df[df["make"] == brand].dropna(subset=["model_guess", "price_eur"]).copy()
        groups = data["model_guess"].value_counts().head(10).index.tolist()
        title  = f"Price distribution for {brand}"
        xlabel = "Model"

    if data.empty or not groups:
        ax.text(0.5, 0.5, "No data for this selection", ha="center", va="center")
        ax.axis("off")
        return fig

    series = []
    labels = []
    for group in groups:
        mask   = data["make"].eq(group) if brand == "All" else data["model_guess"].eq(group)
        values = data.loc[mask, "price_eur"].dropna().values
        if len(values):
            series.append(values)
            labels.append(group)

    if not series:
        ax.text(0.5, 0.5, "No price distribution available", ha="center", va="center")
        ax.axis("off")
        return fig

    bp = ax.boxplot(series, tick_labels=labels, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 2})
    colors = plt.cm.Set2(np.linspace(0, 1, len(bp["boxes"])))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Price (€)")
    ax.tick_params(axis="x", rotation=25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_brand_explorer(df, brand="All"):
    filtered = df if brand == "All" else df[df["make"] == brand]
    filtered = filtered.dropna(subset=["price_eur", "km_num", "year_num"])

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(14, 7))
    fig.tight_layout(pad=2)

    if filtered.empty:
        for ax in (ax_left, ax_right):
            ax.text(0.5, 0.5, "No data for this brand", ha="center", va="center")
            ax.axis("off")
        return fig

    for fuel in ["Diesel", "Petrol", "Hybrid", "Electric", "LPG", "CNG", "Gas", "Other"]:
        subset = filtered[filtered["fuel_norm"] == fuel]
        if subset.empty:
            continue
        ax_left.scatter(subset["km_num"], subset["price_eur"], s=26, alpha=0.7,
                        color=FUEL_COLORS.get(fuel, FUEL_COLORS["Other"]), label=fuel)

    if len(filtered) >= 3:
        coeffs = np.polyfit(filtered["km_num"], filtered["price_eur"], 1)
        xs = np.linspace(filtered["km_num"].min(), filtered["km_num"].max(), 100)
        ax_left.plot(xs, coeffs[0] * xs + coeffs[1], color="#111827", linewidth=2)

    ax_left.set_title(f"{brand} — price vs mileage")
    ax_left.set_xlabel("Mileage (km)")
    ax_left.set_ylabel("Price (€)")
    ax_left.legend(loc="best", frameon=False, fontsize=8)
    ax_left.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    ax_left.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))

    model_counts = filtered["model_guess"].value_counts().head(10).sort_values()
    ax_right.barh(model_counts.index, model_counts.values, color="#2c7fb8")
    right_title = "Top models overall" if brand == "All" else f"Top models — {brand}"
    ax_right.set_title(right_title)
    ax_right.set_xlabel("Listings")
    ax_right.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    n = len(filtered)
    fig.suptitle(
        f"{n} listings  |  median price {pretty_money(filtered['price_eur'].median())}"
        f"  |  median km {pretty_int(filtered['km_num'].median())}",
        fontsize=9, color="#6b7280", y=0.01,
    )
    return fig


def plot_price_heatmap(df):
    fig, ax = plt.subplots(figsize=(13, 8))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["year_num", "km_num", "price_eur"])
    if data.empty:
        ax.text(0.5, 0.5, "No year/km/price data", ha="center", va="center")
        ax.axis("off")
        return fig

    data = data.copy()
    data["year_bucket"] = (data["year_num"] // 2) * 2
    data["km_bucket"]   = (data["km_num"] // 25_000) * 25_000

    pivot = data.pivot_table(index="year_bucket", columns="km_bucket",
                              values="price_eur", aggfunc="median")
    pivot = pivot.sort_index().sort_index(axis=1)

    if pivot.empty:
        ax.text(0.5, 0.5, "No heatmap data available", ha="center", va="center")
        ax.axis("off")
        return fig

    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{int(v)}-{int(v + 1)}" for v in pivot.index])
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{int(v / 1000)}k" for v in pivot.columns], rotation=45, ha="right")
    ax.set_title("Price heatmap by year and mileage")
    ax.set_xlabel("Mileage bucket")
    ax.set_ylabel("Year bucket")
    fig.colorbar(im, ax=ax, label="Median price (€)")
    return fig


def plot_mileage_by_body(df):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["body_type", "km_num"])
    if data.empty:
        ax.text(0.5, 0.5, "No body type data", ha="center", va="center")
        ax.axis("off")
        return fig
    order  = [b for b in BODY_LABELS if b in set(data["body_type"])]
    values = [data.loc[data["body_type"] == b, "km_num"].dropna().values for b in order]
    bp     = ax.boxplot(values, tick_labels=order, patch_artist=True,
                        medianprops={"color": "black", "linewidth": 2})
    colors = plt.cm.Set3(np.linspace(0, 1, len(bp["boxes"])))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ymax = max((v.max() for v in values if len(v)), default=0)
    for i, vals in enumerate(values):
        n = len(vals)
        label = f"n={n}" if n >= 3 else f"n={n} (!)"
        ax.text(i + 1, ymax * 1.02, label, ha="center", va="bottom", fontsize=8, color="#6b7280")
    ax.set_title("Mileage distribution by body type")
    ax.set_ylabel("Mileage (km)")
    ax.tick_params(axis="x", rotation=25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_private_vs_dealer(df):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.tight_layout(pad=2)

    # Filter out Unknown before pivoting
    data = df[df["seller_type"].isin({"Private", "Dealer"})].dropna(subset=["make", "price_eur"])

    if data.empty:
        msg = (
            "No seller classification data available.\n\n"
            "Run with fetch_details: true in config.yaml to enable\n"
            "seller type detection (requires internal_number / seller_name fields)."
        )
        ax.text(0.5, 0.5, msg, ha="center", va="center", wrap=True, fontsize=11)
        ax.axis("off")
        return fig

    pivot = data.pivot_table(index="make", columns="seller_type", values="price_eur", aggfunc="mean")
    if not {"Private", "Dealer"}.issubset(pivot.columns):
        ax.text(0.5, 0.5, "Need both dealer and private listings to compare", ha="center", va="center")
        ax.axis("off")
        return fig

    pivot["gap"] = pivot["Dealer"] - pivot["Private"]
    pivot = pivot.dropna(subset=["gap"]).sort_values("gap", ascending=False).head(12)
    colors = ["#16a34a" if v >= 0 else "#dc2626" for v in pivot["gap"]]
    ax.barh(pivot.index[::-1], pivot["gap"][::-1], color=colors[::-1])
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Private vs dealer price gap by make")
    ax.set_xlabel("Average dealer premium (€)")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
    return fig


def plot_fuel_mix_by_year(df):
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.tight_layout(pad=2)
    data = df.dropna(subset=["year_num", "fuel_norm"])
    if data.empty:
        ax.text(0.5, 0.5, "No year/fuel data", ha="center", va="center")
        ax.axis("off")
        return fig
    pivot = (
        data.pivot_table(index="year_num", columns="fuel_norm", aggfunc="size", fill_value=0)
        .sort_index()
    )
    fuel_order = [f for f in ["Diesel", "Petrol", "Hybrid", "Electric", "LPG", "CNG", "Gas", "Other"]
                  if f in pivot.columns]
    bottom = np.zeros(len(pivot.index))
    for fuel in fuel_order:
        values = pivot[fuel].values
        ax.bar(pivot.index.astype(int), values, bottom=bottom, label=fuel,
               color=FUEL_COLORS.get(fuel, FUEL_COLORS["Other"]))
        bottom += values
    ax.set_title("Fuel type mix by year")
    ax.set_xlabel("Registration year")
    ax.set_ylabel("Listings")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
    ax.tick_params(axis="x", rotation=45)
    return fig


# ---------------------------------------------------------------------------
# When run directly: save all plots as PNGs into the data/ directory
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    brand = cfg.get("brand") or None
    model = cfg.get("model") or None

    df = load_latest()
    df = filter_df(df, brand=brand, model=model)

    if df.empty:
        print("No listings for the current filter.")
    else:
        df = enrich(df)
        suffix = "_".join(filter(None, [brand, model])).replace(" ", "_").lower()

        plots = [
            ("price_vs_mileage",     plot_price_vs_mileage),
            ("depreciation_by_make", plot_depreciation_by_make),
            ("brand_explorer",       plot_brand_explorer),
            ("brand_model_prices",   plot_brand_model_prices),
            ("km_heatmap",           plot_km_heatmap),
            ("price_histogram",      plot_price_histogram),
            ("price_heatmap",        plot_price_heatmap),
            ("mileage_by_body",      plot_mileage_by_body),
            ("private_vs_dealer",    plot_private_vs_dealer),
            ("fuel_mix_by_year",     plot_fuel_mix_by_year),
        ]

        has_seller_data = df["seller_type"].isin({"Private", "Dealer"}).any()

        out_dir = "data"
        print(f"{len(df)} listings — saving plots to {out_dir}/")
        for name, fn in plots:
            if name == "private_vs_dealer" and not has_seller_data:
                print("  skipping private_vs_dealer (no seller data; set fetch_details: true in config.yaml)")
                continue
            filename = f"{name}{'_' + suffix if suffix else ''}.png"
            path = os.path.join(out_dir, filename)
            fig = fn(df)
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  saved {path}")
