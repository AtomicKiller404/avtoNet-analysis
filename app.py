import tkinter as tk
import webbrowser
from tkinter import ttk

import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import plot as P


def embed(fig, parent):
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    toolbar = NavigationToolbar2Tk(canvas, parent)
    toolbar.update()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# ---------------------------------------------------------------------------
# Static tab wrappers — delegate to plot.py, embed the returned figure
# ---------------------------------------------------------------------------

def tab_price_vs_mileage(df, parent):
    embed(P.plot_price_vs_mileage(df), parent)


def tab_depreciation_by_make(df, parent):
    embed(P.plot_depreciation_by_make(df), parent)


def tab_km_heatmap(df, parent):
    embed(P.plot_km_heatmap(df), parent)


def tab_price_histogram(df, parent):
    embed(P.plot_price_histogram(df), parent)


def tab_price_heatmap(df, parent):
    embed(P.plot_price_heatmap(df), parent)


def tab_mileage_by_body(df, parent):
    embed(P.plot_mileage_by_body(df), parent)


def tab_private_vs_dealer(df, parent):
    embed(P.plot_private_vs_dealer(df), parent)


def tab_fuel_mix_by_year(df, parent):
    embed(P.plot_fuel_mix_by_year(df), parent)


# ---------------------------------------------------------------------------
# Interactive tabs — live dropdowns that re-render on selection change
# ---------------------------------------------------------------------------

def tab_brand_model_price_distribution(df, parent):
    container = ttk.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    controls = ttk.Frame(container)
    controls.pack(fill=tk.X, padx=10, pady=(10, 4))
    ttk.Label(controls, text="Brand:").pack(side=tk.LEFT)

    brand_var   = tk.StringVar(value="All")
    brand_combo = ttk.Combobox(controls, textvariable=brand_var, values=P.brand_choices(df),
                                state="readonly", width=20)
    brand_combo.pack(side=tk.LEFT, padx=8)

    hint_var = tk.StringVar(value="Top 10 brands by listing count")
    ttk.Label(controls, textvariable=hint_var).pack(side=tk.LEFT, padx=12)

    figure_frame = ttk.Frame(container)
    figure_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.tight_layout(pad=2)
    canvas = FigureCanvasTkAgg(fig, master=figure_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, figure_frame)
    toolbar.update()

    def refresh(*_):
        ax.clear()
        selected = brand_var.get()
        if selected == "All":
            data   = df.dropna(subset=["make", "price_eur"]).copy()
            groups = data["make"].value_counts().head(10).index.tolist()
            title  = "Price distribution by brand"
            xlabel = "Brand"
            hint_var.set("Top 10 brands by listing count")
        else:
            data   = df[df["make"] == selected].dropna(subset=["model_guess", "price_eur"]).copy()
            groups = data["model_guess"].value_counts().head(10).index.tolist()
            title  = f"Price distribution for {selected}"
            xlabel = "Model"
            hint_var.set("Top 10 models within selected brand")

        if data.empty or not groups:
            ax.text(0.5, 0.5, "No data for this selection", ha="center", va="center")
            ax.axis("off")
            canvas.draw()
            return

        series = []
        labels = []
        for group in groups:
            mask   = data["make"].eq(group) if selected == "All" else data["model_guess"].eq(group)
            values = data.loc[mask, "price_eur"].dropna().values
            if len(values):
                series.append(values)
                labels.append(group)

        if not series:
            ax.text(0.5, 0.5, "No price distribution available", ha="center", va="center")
            ax.axis("off")
            canvas.draw()
            return

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
        canvas.draw()

    brand_combo.bind("<<ComboboxSelected>>", refresh)
    refresh()


def tab_brand_explorer(df, parent):
    container = ttk.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    controls = ttk.Frame(container)
    controls.pack(fill=tk.X, padx=10, pady=(10, 4))
    ttk.Label(controls, text="Brand:").pack(side=tk.LEFT)
    brand_var   = tk.StringVar(value="All")
    brand_combo = ttk.Combobox(controls, textvariable=brand_var, values=P.brand_choices(df),
                                state="readonly", width=20)
    brand_combo.pack(side=tk.LEFT, padx=8)

    summary_var = tk.StringVar(value="")
    ttk.Label(controls, textvariable=summary_var).pack(side=tk.LEFT, padx=12)

    figure_frame = ttk.Frame(container)
    figure_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(14, 7))
    fig.tight_layout(pad=2)
    canvas = FigureCanvasTkAgg(fig, master=figure_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, figure_frame)
    toolbar.update()

    def refresh(*_):
        ax_left.clear()
        ax_right.clear()

        selected = brand_var.get()
        filtered = df if selected == "All" else df[df["make"] == selected]
        filtered = filtered.dropna(subset=["price_eur", "km_num", "year_num"])

        if filtered.empty:
            for ax in (ax_left, ax_right):
                ax.text(0.5, 0.5, "No data for this brand", ha="center", va="center")
                ax.axis("off")
            summary_var.set("")
            canvas.draw()
            return

        for fuel in ["Diesel", "Petrol", "Hybrid", "Electric", "LPG", "CNG", "Gas", "Other"]:
            subset = filtered[filtered["fuel_norm"] == fuel]
            if subset.empty:
                continue
            ax_left.scatter(subset["km_num"], subset["price_eur"], s=26, alpha=0.7,
                            color=P.FUEL_COLORS.get(fuel, P.FUEL_COLORS["Other"]), label=fuel)

        if len(filtered) >= 3:
            coeffs = np.polyfit(filtered["km_num"], filtered["price_eur"], 1)
            xs = np.linspace(filtered["km_num"].min(), filtered["km_num"].max(), 100)
            ax_left.plot(xs, coeffs[0] * xs + coeffs[1], color="#111827", linewidth=2)

        ax_left.set_title(f"{selected} — price vs mileage")
        ax_left.set_xlabel("Mileage (km)")
        ax_left.set_ylabel("Price (€)")
        ax_left.legend(loc="best", frameon=False, fontsize=8)
        ax_left.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))
        ax_left.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", " ")))

        model_counts = filtered["model_guess"].value_counts().head(10).sort_values()
        ax_right.barh(model_counts.index, model_counts.values, color="#2c7fb8")
        right_title = "Top models overall" if selected == "All" else f"Top models — {selected}"
        ax_right.set_title(right_title)
        ax_right.set_xlabel("Listings")
        ax_right.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

        summary_var.set(
            f"{len(filtered)} listings  |  median price {P.pretty_money(filtered['price_eur'].median())}"
            f"  |  median km {P.pretty_int(filtered['km_num'].median())}"
        )
        canvas.draw()

    brand_combo.bind("<<ComboboxSelected>>", refresh)
    refresh()


def tab_value_leaderboard(df, parent):
    container = ttk.Frame(parent)
    container.pack(fill=tk.BOTH, expand=True)

    controls = ttk.Frame(container)
    controls.pack(fill=tk.X, padx=10, pady=(10, 4))
    ttk.Label(controls, text="Filter by body type:").pack(side=tk.LEFT)
    body_names = ["All"] + sorted(set(df["body_type"].dropna()) - {"Other"})
    choice     = tk.StringVar(value="All")
    combo      = ttk.Combobox(controls, textvariable=choice, values=body_names,
                               state="readonly", width=18)
    combo.pack(side=tk.LEFT, padx=8)
    ttk.Label(controls, text="  Double-click a row to open listing in browser",
              foreground="#6b7280").pack(side=tk.LEFT, padx=12)

    tree_frame = ttk.Frame(container)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    columns = ("rank", "score", "title", "make", "model", "body", "year",
               "km", "price", "median", "gap", "seller")
    tree    = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
    yscroll = ttk.Scrollbar(tree_frame, orient="vertical",   command=tree.yview)
    xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    headings = {
        "rank": "#", "score": "Score", "title": "Listing", "make": "Make",
        "model": "Model", "body": "Body", "year": "Year", "km": "Km",
        "price": "Price (€)", "median": "Median (€)", "gap": "Gap (€)", "seller": "Seller",
    }
    widths = {
        "rank": 45, "score": 70, "title": 340, "make": 110, "model": 150,
        "body": 110, "year": 70, "km": 85, "price": 100, "median": 100,
        "gap": 90, "seller": 85,
    }
    for col in columns:
        tree.heading(col, text=headings[col])
        tree.column(col, width=widths[col],
                    anchor=tk.W if col in {"title", "make", "model", "body", "seller"} else tk.E)

    def refresh(*_):
        for item in tree.get_children():
            tree.delete(item)
        data = P.top_listings(df, choice.get())
        if data.empty:
            tree.insert("", tk.END, values=("", "", "No listings found", *[""] * (len(columns) - 3)))
            return
        for idx, row in data.iterrows():
            sale_flag = "* " if row.get("on_sale", False) else ""
            url       = str(row.get("url", "") or "")
            tree.insert(
                "", tk.END,
                values=(
                    idx + 1,
                    f"{row['value_score']:.3f}",
                    sale_flag + str(row["title"])[:85],
                    row["make"],
                    row["model_guess"],
                    row["body_type"],
                    P.pretty_int(row["year_num"]),
                    P.pretty_int(row["km_num"]),
                    P.pretty_money(row["price_eur"]),
                    P.pretty_money(row["make_model_median"]),
                    P.pretty_money(row["price_gap"]),
                    row["seller_type"],
                ),
                tags=(url,),
            )

    def on_double_click(event):
        item = tree.focus()
        if not item:
            return
        tags = tree.item(item, "tags")
        if tags and tags[0]:
            webbrowser.open(tags[0])

    tree.bind("<Double-1>", on_double_click)
    combo.bind("<<ComboboxSelected>>", refresh)
    refresh()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

def run(df, title_suffix=""):
    root = tk.Tk()
    root.title(f"avto.net analysis{' — ' + title_suffix if title_suffix else ''}")
    root.geometry("1400x860")

    nb = ttk.Notebook(root)
    nb.pack(fill=tk.BOTH, expand=True)

    tabs = [
        ("Price vs mileage",       tab_price_vs_mileage),
        ("Depreciation by make",   tab_depreciation_by_make),
        ("Brand explorer",         tab_brand_explorer),
        ("Brand/model prices",     tab_brand_model_price_distribution),
        ("Mileage heatmap",        tab_km_heatmap),
        ("Sweet spot histogram",   tab_price_histogram),
        ("Price heatmap",          tab_price_heatmap),
        ("Value leaderboard",      tab_value_leaderboard),
        ("Mileage by body type",   tab_mileage_by_body),
        ("Private vs dealer",      tab_private_vs_dealer),
        ("Fuel mix by year",       tab_fuel_mix_by_year),
    ]

    for label, builder in tabs:
        frame = ttk.Frame(nb)
        nb.add(frame, text=label)
        builder(df, frame)

    def _on_close():
        plt.close("all")
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    brand = cfg.get("brand") or None
    model = cfg.get("model") or None

    df = P.load_latest()
    df = P.filter_df(df, brand=brand, model=model)

    if df.empty:
        print("No listings for the current filter.")
    else:
        df = P.enrich(df)
        suffix = " ".join(filter(None, [brand, model]))
        print(f"{len(df)} listings")
        run(df, title_suffix=suffix)
