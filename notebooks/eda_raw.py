# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "google-cloud-storage>=2.0",
#     "python-dotenv>=1.0",
#     "pandas>=2.0",
#     "matplotlib>=3.7",
#     "google-genai==2.5.0",
#     "aiohttp==3.13.5",
#     "pyopenssl==26.2.0",
#     "protobuf==7.35.0",
#     "mcp>=1",
#     "pydantic>=2",
#     "google-genai>=2.5.0",
# ]
# ///

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def setup_imports():
    import logging
    import os
    import sys
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import pandas as pd
    from dotenv import load_dotenv
    from google.cloud import storage

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return Path, load_dotenv, mo, os, pd, plt, storage, sys


@app.cell(hide_code=True)
def gcs_setup(Path, load_dotenv, os, storage, sys):
    _root = str(Path(__file__).parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from ingestion.utils.loaders import load_open_meteo, load_smard

    load_dotenv()
    _client = storage.Client()
    bucket = _client.bucket(os.environ["GCS_BUCKET_NAME"])
    return bucket, load_open_meteo, load_smard


@app.cell(hide_code=True)
def plot_style():
    PT_MUTED = [
        "#CC6677",  # rose
        "#332288",  # indigo
        "#DDCC77",  # sand
        "#117733",  # green
        "#88CCEE",  # cyan
        "#882255",  # wine
        "#44AA99",  # teal
        "#999933",  # olive
        "#AA4499",  # purple
    ]
    return (PT_MUTED,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Exploratory Data Analysis (raw data)
    In this notebook I'm having a first look at the raw data provided from the smart-api and meteo-api.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 1. Price Overview
    """)
    return


@app.cell
def price_data(bucket, load_smard):
    price_df = load_smard(bucket, 4169)
    price_df['year'] = price_df['timestamp'].dt.year
    price_df['month'] = price_df['timestamp'].dt.month
    price_df['day_of_year'] = price_df['timestamp'].dt.day_of_year
    return (price_df,)


@app.cell
def _(PT_MUTED, plt, price_df):
    MONTH_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig_day_year, _ax = plt.subplots(figsize=(12, 4))
    for _i, (_year, group) in enumerate(price_df.groupby('year')):
        _ax.scatter(group['day_of_year'], group['value'],
                 label=_year, alpha=0.7, color=PT_MUTED[_i % len(PT_MUTED)], s=1)
    _ax.set_xticks(MONTH_STARTS)
    _ax.set_xticklabels(MONTH_NAMES)
    _ax.set_xlim(1, 366)
    _ax.set_title("Day-Ahead Price by Year (aligned by calendar day)")
    _ax.set_ylabel("EUR/MWh")
    _ax.legend()
    plt.tight_layout()
    fig_day_year
    return MONTH_NAMES, MONTH_STARTS


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observations
    - Visible price difference for hour of day. Interesting would be here to look at the differences (min/max) within a day.
    - Year 2022 had extreme high price periods. (energy crisis, start of Russia/Ukraine war probably) This might affect averages.
    - Difficult to see any real trends with this visualization, since there are 24 dots per day.
    """)
    return


@app.cell
def _(price_df):
    price_daily_df = price_df.set_index('timestamp').resample("D").median()
    price_daily_df
    return (price_daily_df,)


@app.cell
def _(MONTH_NAMES, MONTH_STARTS, PT_MUTED, plt, price_daily_df):
    fig_avg_day_year, _ax = plt.subplots(figsize=(12, 4))
    for _i, (_year, _group) in enumerate(price_daily_df.groupby('year')):
        _ax.plot(_group['day_of_year'], _group['value'],
                 label=_year, alpha=0.7, color=PT_MUTED[_i % len(PT_MUTED)])
    _ax.set_xticks(MONTH_STARTS)
    _ax.set_xticklabels(MONTH_NAMES)
    _ax.set_xlim(1, 366)
    _ax.set_title("Day-Ahead Median Price by Year (aligned by calendar day)")
    _ax.set_ylabel("EUR/MWh")
    _ax.legend()
    plt.tight_layout()
    fig_avg_day_year
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observations
    - Year 2022 extreme distribution shift. Might make sense to exclude 2022 from the data.
    - Cannot see much seasonality besides that
    - There are certain spikes where prices fall from one day to the other. This could be weather related or day of week
    - Decline during end of December -> holidays? NOTE: holidays will be out-of-scope for this analysis. Holidays that are on a fix day of the year however might be picked up as seasonality.
    """)
    return


@app.cell
def price_timeseries(PT_MUTED, plt, price_df):
    fig_ts, _ax = plt.subplots(figsize=(14, 4))
    _ax.plot(price_df["timestamp"], price_df["value"], linewidth=0.3, color=PT_MUTED[4], alpha=0.8)
    _ax.axhline(0, color=PT_MUTED[0], linewidth=0.8, linestyle="--", label="Zero")
    _ax.set_title("Day-Ahead Price: Germany/Luxembourg")
    _ax.set_ylabel("EUR/MWh")
    _ax.legend(fontsize=8)
    plt.tight_layout()
    fig_ts
    return


@app.cell
def price_histogram(PT_MUTED, plt, price_df):
    fig_hist, _ax = plt.subplots(figsize=(8, 4))
    _ax.hist(price_df["value"].dropna(), bins=100, color=PT_MUTED[4], edgecolor="none")
    _ax.axvline(0, color=PT_MUTED[0], linewidth=1, linestyle="--", label="Zero")
    _ax.set_xlabel("Price (EUR/MWh)")
    _ax.set_ylabel("Count")
    _ax.set_title("Price Distribution")
    _ax.legend()
    plt.tight_layout()
    fig_hist
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observation
    - Interesting distribution, far from normal distributed. Could this come from distribution shift?
    - The asymmetry reflects the asymmetry of the market. Negative prices are basically the shut-down costs and therefore capped. (noob interpretation)
    """)
    return


@app.cell
def _(PT_MUTED, plt, price_df_adj):
    fig_hist_adj, _ax = plt.subplots(figsize=(8, 4))
    _ax.hist(price_df_adj["value"].dropna(), bins=100, color=PT_MUTED[4], edgecolor="none")
    _ax.axvline(0, color=PT_MUTED[0], linewidth=1, linestyle="--", label="Zero")
    _ax.set_xlabel("Price (EUR/MWh)")
    _ax.set_ylabel("Count")
    _ax.set_title("Price Distribution (excl. 2022)")
    _ax.legend()
    plt.tight_layout()
    fig_hist_adj
    return


@app.cell
def _(mo, price_df):
    # Trying out here the marimo data frame feature to filter and compare
    edit_price_df = mo.ui.dataframe(price_df)
    edit_price_df
    return (edit_price_df,)


@app.cell
def price_stats(edit_price_df, mo, price_df):
    s_edit = edit_price_df.value["value"]
    s_orig = price_df["value"]

    pct_neg_edit = (s_edit < 0).mean() * 100
    pct_neg_orig = (s_orig < 0).mean() * 100

    mo.md(f"""
    | Statistic | Edited Price | All Years Avg Price |
    |---|---|---|
    | Count | {len(s_edit):,} | {len(s_orig):,} |
    | Mean | {s_edit.mean():.2f} EUR/MWh | {s_orig.mean():.2f} EUR/MWh |
    | Std | {s_edit.std():.2f} EUR/MWh | {s_orig.std():.2f} EUR/MWh |
    | Min | {s_edit.min():.2f} EUR/MWh | {s_orig.min():.2f} EUR/MWh |
    | Max | {s_edit.max():.2f} EUR/MWh | {s_orig.max():.2f} EUR/MWh |
    | Negative prices | {pct_neg_edit:.1f}% of hours | {pct_neg_orig:.1f}% of hours |
    """)
    return


@app.cell
def _(PT_MUTED, plt, price_df):
    fig_boxplot_year, _ax = plt.subplots(figsize=(10, 6))

    # Get unique years for x-axis labels and data grouping
    years = price_df["year"].sort_values().unique()

    # Prepare data for boxplot: a list of arrays, one for each year's 'value'
    boxplot_data = [price_df[price_df["year"] == year]["value"].dropna().values for year in years]

    # Create the boxplot
    # `patch_artist=True` allows customizing the box fill color
    bp = _ax.boxplot(
        boxplot_data,
        tick_labels=[str(year) for year in years],
        patch_artist=True,
        medianprops={"color": "black"},
        flierprops={"marker": "o", "markersize": 2, "alpha": 0.3},
    )

    # Apply PT_MUTED colors to the boxes
    for _i, box in enumerate(bp["boxes"]):
        box.set_facecolor(PT_MUTED[_i % len(PT_MUTED)])
        box.set_edgecolor(PT_MUTED[_i % len(PT_MUTED)])

    _ax.set_title("Day-Ahead Price Distribution by Year")
    _ax.set_xlabel("Year")
    _ax.set_ylabel("Price (EUR/MWh)")
    _ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.gca()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Decision: Discard 2022 Data
    Due to the heavy distribution shift I think 2022 data will add no value and might be harmful.
    2022 was with the gas crisis due to Russian attack on Ukraine definitely an exaptional year.
    Still, we need to keep in mind that we have in this field also a **natural distribution shift** driven by the rise of renewable energy.
    """)
    return


@app.cell
def _(price_df):
    price_df_adj = price_df[price_df["year"] > 2022]
    return (price_df_adj,)


@app.cell
def _(mo):
    mo.md("""
    ## 2. Seasonality
    """)
    return


@app.cell
def seasonality_prep(price_df_adj):
    price_ts = price_df_adj.copy()
    price_ts["hour"] = price_ts["timestamp"].dt.hour
    price_ts["dow"] = price_ts["timestamp"].dt.dayofweek
    price_ts["month"] = price_ts["timestamp"].dt.month
    return (price_ts,)


@app.cell
def hourly_seasonality(PT_MUTED, plt, price_ts):
    hourly_avg = price_ts.groupby("hour")["value"].mean()
    fig_hour, _ax = plt.subplots(figsize=(9, 4))
    _ax.bar(hourly_avg.index, hourly_avg.values, color=PT_MUTED[4])
    _ax.set_title("Average Price by Hour of Day (UTC)")
    _ax.set_xlabel("Hour")
    _ax.set_ylabel("EUR/MWh")
    _ax.set_xticks(range(0, 24, 2))
    plt.tight_layout()
    fig_hour
    return


@app.cell
def weekly_seasonality(PT_MUTED, plt, price_ts):
    dow_avg = price_ts.groupby("dow")["value"].mean()
    fig_dow, _ax = plt.subplots(figsize=(7, 4))
    _ax.bar(dow_avg.index, dow_avg.values, color=PT_MUTED[4])
    _ax.set_title("Average Price by Day of Week")
    _ax.set_xlabel("Day")
    _ax.set_ylabel("EUR/MWh")
    _ax.set_xticks(range(7))
    _ax.set_xticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    plt.tight_layout()
    fig_dow
    return


@app.cell
def monthly_seasonality(PT_MUTED, plt, price_ts):
    month_avg = price_ts.groupby("month")["value"].mean()
    fig_month, _ax = plt.subplots(figsize=(8, 4))
    _ax.bar(month_avg.index, month_avg.values, color=PT_MUTED[4])
    _ax.set_title("Average Price by Month")
    _ax.set_xlabel("Month")
    _ax.set_ylabel("EUR/MWh")
    _ax.set_xticks(range(1, 13))
    _ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    plt.tight_layout()
    fig_month
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observation
    - Clear Seasonality, potentially due to solar energy, or due to energy intensive heating in cold months
    - May-Jul price is cheapest, Nov, Jan & Feb most expensive
    - December is exceptionally cheap, might be related to holidays.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Summary Seasonality
    - Hour of day seasonality - price cheapest during noon (UTC) -> hour of day critical component
    - Weekday seasonality - cheapest during weekend -> should also add "day_of_week" categorical, or even a weekend flag
    - Literal seasonaliy - (summer vs winter) -> Should add a month_of_year or week_number categorical
    - Holidays - The analysis should consider fix-date holidays -> Add a day_of_year categorical
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Generation Mix
    """)
    return


@app.cell
def generation_data(bucket, load_smard, pd):
    GENERATION_FILTERS = {
        1223: "Lignite",
        1224: "Nuclear",
        1225: "Wind Offshore",
        1226: "Hydro",
        1228: "Other Renewables",
        4066: "Biomass",
        4067: "Wind Onshore",
        4068: "Solar",
        4069: "Hard Coal",
        4070: "Pumped Storage",
        4071: "Natural Gas",
        1227: "Other Conv.",
    }
    gen_series = {}
    for _code, _name in GENERATION_FILTERS.items():
        _df = load_smard(bucket, _code)
        if not _df.empty:
            gen_series[_name] = _df.set_index("timestamp")["value"]

    gen_df = pd.DataFrame(gen_series).sort_index().clip(lower=0)
    gen_df = gen_df[gen_df.index.year > 2022 ]

    # Group definitions
    GROUPS = {
        "Biomass":       ["Biomass"],
        "Hydro":         ["Hydro"],
        "Solar":         ["Solar"],
        "Wind":          ["Wind Onshore", "Wind Offshore"],
        "Gas":           ["Natural Gas"],
        "Coal":          ["Hard Coal", "Lignite"],
        "Nuclear":       ["Nuclear"],
        "Other":         ["Pumped Storage", "Other Renewables", "Other Conv."]
    }

    # Add group columns
    for group_name, sources in GROUPS.items():
        available = [s for s in sources if s in gen_df.columns]
        gen_df[f"grp_{group_name}"] = gen_df[available].sum(axis=1)

    # Add total
    gen_df["total"] = gen_df[[f"grp_{g}" for g in GROUPS]].sum(axis=1)

    gen_daily = gen_df.resample("D").mean()
    return gen_daily, gen_df


@app.cell
def _():
    return


@app.cell
def _(gen_df):
    gen_df[:1000]
    return


@app.cell
def generation_chart(PT_MUTED, gen_daily, plt):
    _grp_cols = [c for c in gen_daily.columns if c.startswith("grp_")]
    fig_gen, _ax = plt.subplots(figsize=(14, 6))
    _ax.stackplot(
        gen_daily.index,
        gen_daily[_grp_cols].fillna(0).values.T,
        labels=_grp_cols,
        colors=PT_MUTED[:len(_grp_cols)],
    )
    _ax.set_title("Daily Average Generation Mix (MW)")
    _ax.set_ylabel("MW")
    _ax.legend(loc="upper left", fontsize=8, ncol=2)
    plt.tight_layout()
    fig_gen
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observation
    - There is a clear saisonality with Solar energy
    - Nuclear exit in 2023
    - Decline of coal is visible, besides that in stacked visualizations it is hard to see distirbution shift
    - Spikes in wind
    - Biomass as fix production (due to contracts?)
    - Hydro in Germany is also always running (rivers) and therefore unflexible production.
    """)
    return


@app.cell
def _(PT_MUTED, gen_daily, plt):
    _grp_cols = [c for c in gen_daily.columns if c.startswith("grp_")]
    fig_gen_line, _ax = plt.subplots(figsize=(14, 6))

    # Loop through each group column and plot it as an individual line
    for _i, _col in enumerate(_grp_cols):
        _ax.plot(
            gen_daily.index,
            gen_daily[_col].fillna(0),
            label=_col,
            color=PT_MUTED[_i],
            linewidth=1.5,
            alpha=0.7
        )

    _ax.set_title("Daily Average Generation Mix (MW)")
    _ax.set_ylabel("MW")
    _ax.legend(loc="upper left", fontsize=8, ncol=2)

    # Optional addition: A light grid helps tracking overlapping lines
    _ax.grid(True, linestyle="--", alpha=0.2) 

    plt.tight_layout()
    fig_gen_line
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Observation
    - Here we can see more clearly the seasonalities of wind. We can however not see in the data what part of this is metereology and what is curtailment. Maybe when adding the weather information we can find days with high wind speed but low production to get an idea for this.
    - Coal/gas have a seasonality as well, but clearly counter-balances wind
    - "Other" seems to be stable as well, would probably deep dive what makes this so stable / unflexible.
    - Interesting to see that coal and gas are never at zero. Even though we had days with "100% renewable energy" already.
    """)
    return


@app.cell
def _(PT_MUTED, gen_daily, plt):
    _grp_cols = [c for c in gen_daily.columns if c.startswith("grp_")]
    gen_daily_pct = gen_daily[_grp_cols].div(gen_daily["total"], axis=0) * 100

    fig_gen_pct_line, _ax = plt.subplots(figsize=(14, 6))

    _ax.stackplot(
        gen_daily_pct.index,
        gen_daily_pct[_grp_cols].fillna(0).values.T,
        labels=_grp_cols,
        colors=PT_MUTED[:len(_grp_cols)],
    )

    _ax.set_title("Daily Average Generation Mix (% of Total)")
    _ax.set_ylabel("Percentage (%)")
    _ax.legend(loc="upper left", fontsize=8, ncol=2)
    _ax.set_ylim(0, 100) # Ensure y-axis is from 0 to 100 for percentages

    plt.tight_layout()
    plt.gca()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Weather Overview
    """)
    return


@app.cell
def weather_data(bucket, load_open_meteo):
    weather_north = load_open_meteo(bucket, "north")
    weather_central = load_open_meteo(bucket, "central")
    weather_south = load_open_meteo(bucket, "south")
    return weather_central, weather_north, weather_south


@app.cell
def weather_temperature(
    PT_MUTED,
    plt,
    weather_central,
    weather_north,
    weather_south,
):
    fig_temp, _axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    for _i, (_ax, _df, _loc) in enumerate(zip(
        _axes,
        [weather_north, weather_central, weather_south],
        ["North (54°N 9.9°E)", "Central (51.2°N 10.4°E)", "South (48.5°N 10.0°E)"],
    )):
        _ax.plot(_df["timestamp"], _df["temperature_2m"], linewidth=0.4, color=PT_MUTED[_i])
        _ax.set_ylabel("°C")
        _ax.set_title(f"Temperature – {_loc}")
    plt.tight_layout()
    fig_temp
    return


@app.cell
def weather_wind(PT_MUTED, plt, weather_central, weather_north, weather_south):
    fig_wind, _axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    for _i, (_ax, _df, _loc) in enumerate(zip(
        _axes,
        [weather_north, weather_central, weather_south],
        ["North", "Central", "South"],
    )):
        _ax.plot(_df["timestamp"], _df["wind_speed_100m"], linewidth=0.4, color=PT_MUTED[_i])
        _ax.set_ylabel("m/s")
        _ax.set_title(f"Wind Speed 100m – {_loc}")
    plt.tight_layout()
    fig_wind
    return


@app.cell
def _(mo):
    mo.md("""
    ## 5. Price vs Weather Correlation (Central Location)
    """)
    return


@app.cell
def price_weather_merge(pd, price_df_adj, weather_central):
    price_h = price_df_adj.set_index("timestamp")["value"].rename("price")
    weather_h = weather_central.set_index("timestamp")
    pw_merged = pd.concat([price_h, weather_h], axis=1).dropna(subset=["price"])
    return (price_h,)


@app.cell
def correlation_scatters(
    PT_MUTED,
    pd,
    plt,
    price_h,
    weather_central,
    weather_north,
    weather_south,
):
    WEATHER_PAIRS = [
        ("temperature_2m", "Temperature (°C)"),
        ("wind_speed_100m", "Wind Speed 100m (m/s)"),
        ("shortwave_radiation", "Shortwave Radiation (W/m²)"),
    ]
    # Define a list of weather dataframes with their corresponding labels and colors
    _weather_locations = [
        (weather_north, "North", PT_MUTED[0]),
        (weather_central, "Central", PT_MUTED[3]),
        (weather_south, "South", PT_MUTED[6]),
    ]
    fig_corr, _axes = plt.subplots(1, 3, figsize=(15, 5))
    for _ax, (_col, _label) in zip(_axes, WEATHER_PAIRS):
        for _w_df, _loc_label, _color in _weather_locations:
            # Merge price data with current location's weather data
            _pw_merged_loc = pd.concat([price_h, _w_df.set_index("timestamp")], axis=1).dropna(subset=["price", _col])
            _ax.scatter(
                _pw_merged_loc[_col],
                _pw_merged_loc["price"],
                alpha=0.4,
                s=0.05,
                color=_color,
                rasterized=True,
                label=_loc_label # Add label for legend
            )
        _ax.set_xlabel(_label)
        _ax.set_ylabel("Price (EUR/MWh)")
        _ax.set_title(f"Price vs {_col.replace('_', ' ').title()}")
        _ax.legend(fontsize=8, markerscale=5) # Add legend to each subplot
    plt.tight_layout()
    plt.gca()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 6. Data Quality
    """)
    return


@app.cell
def data_quality(bucket, load_smard, mo, pd):
    ALL_FILTERS = {
        4169: "Price DE/LU",
        1223: "Lignite",
        1224: "Nuclear",
        1225: "Wind Offshore",
        1226: "Hydro",
        1227: "Other Conv.",
        1228: "Other Renewables",
        4066: "Biomass",
        4067: "Wind Onshore",
        4068: "Solar",
        4069: "Hard Coal",
        4070: "Pumped Storage Gen.",
        4071: "Natural Gas",
        410: "Consumption Total",
        4359: "Residual Load",
        4387: "Pumped Storage Cons.",
    }
    rows = []
    for _code, _name in ALL_FILTERS.items():
        _df = load_smard(bucket, _code)
        if _df.empty:
            rows.append({"Filter": _code, "Series": _name, "Rows": 0, "Nulls": 0, "Max Gap": "–", "Gaps > 2h": 0})
            continue
        _nulls = int(_df["value"].isna().sum())
        _diffs = _df["timestamp"].diff().dropna()
        _max_gap = str(_diffs.max())
        _gaps_over_2h = int((_diffs > pd.Timedelta("2h")).sum())
        rows.append({
            "Filter": _code,
            "Series": _name,
            "Rows": len(_df),
            "Nulls": _nulls,
            "Max Gap": _max_gap,
            "Gaps > 2h": _gaps_over_2h,
        })
    quality_df = pd.DataFrame(rows)
    mo.ui.table(quality_df)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    - Smard-api data seems to be quite consistent. Missing data from nuclear is because of the end of nuclear energy in 2023.
    - Pricing data is available for 30 more days
    - No data gaps
    """)
    return


if __name__ == "__main__":
    app.run()
