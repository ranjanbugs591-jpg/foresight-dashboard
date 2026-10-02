from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Project FORESIGHT",
    page_icon="📦",
    layout="wide"
)


@st.cache_data
def load_data():
    weekly = pd.read_csv(
        ROOT / "data/weekly_full.csv",
        parse_dates=["Date"]
    )
    forecasts = pd.read_csv(
        ROOT / "data/forecasts.csv",
        parse_dates=["Date"]
    )
    risk = pd.read_csv(
        ROOT / "data/latest_risk_snapshot.csv",
        parse_dates=["Snapshot_Date"]
    )
    validation = pd.read_csv(
        ROOT / "reports/backtest_predictions.csv",
        parse_dates=["Date"]
    )
    metrics = json.loads(
        (ROOT / "reports/metrics.json").read_text(
            encoding="utf-8"
        )
    )
    return weekly, forecasts, risk, validation, metrics


st.title("📦 Project FORESIGHT")
st.caption("NorthBay Living · Demand forecasting and inventory planning")

try:
    with st.spinner("Loading project results..."):
        weekly, forecasts, risk, validation, metrics = load_data()
except (OSError, ValueError, KeyError) as error:
    st.error(f"Could not load project results: {error}")
    st.stop()

st.info(
    f"Historical planning exercise: eight-week forecast begins "
    f"{metrics['forecast_origin']}. These results describe the "
    f"supplied historical dataset."
)
st.warning(
    f"Inventory snapshots are {metrics['inventory_max_age_days']} "
    "days old at forecast origin. Confirm stock and incoming orders "
    "before acting."
)

page = st.sidebar.radio(
    "Navigate",
    [
        "Executive Summary",
        "Inventory & Risk",
        "Demand Forecast",
        "Sales Trend",
        "SKU Scoring",
        "Methodology"
    ]
)

categories = st.sidebar.multiselect(
    "Categories",
    sorted(risk["Category"].dropna().unique()),
    default=sorted(risk["Category"].dropna().unique())
)

choices = sorted(
    risk.loc[risk["Category"].isin(categories), "SKU"].unique()
)
sku_filter = st.sidebar.selectbox(
    "SKU filter", ["All SKUs"] + choices
)
selected = choices if sku_filter == "All SKUs" else [sku_filter]
filtered = risk[risk["SKU"].isin(selected)]

if filtered.empty:
    st.info("Select at least one category to view results.")
    st.stop()


def rupees(value):
    return f"₹{value:,.0f}"


def show_decisions(frame):
    columns = [
        "SKU", "Product_Name", "Category", "action",
        "recommended_order_units", "Current_Stock", "On_Order",
        "lead_time_demand", "weeks_of_cover",
        "potential_lost_revenue", "excess_capital_tied_up"
    ]
    st.dataframe(
        frame[columns],
        hide_index=True,
        use_container_width=True
    )
    st.download_button(
        "Download inventory decisions",
        frame[columns].to_csv(index=False),
        file_name="inventory_decisions.csv",
        mime="text/csv"
    )


if page == "Executive Summary":
    a, b, c, d = st.columns(4)
    a.metric("Selected SKUs", len(filtered))
    b.metric(
        "Reorder recommendations",
        int(filtered["stockout_risk"].sum())
    )
    c.metric(
        "Potential revenue shortfall",
        rupees(filtered["potential_lost_revenue"].sum())
    )
    d.metric(
        "Excess inventory at cost",
        rupees(filtered["excess_capital_tied_up"].sum())
    )
    st.caption(
        "Revenue shortfall covers supplier lead time. Excess stock "
        "covers inventory beyond eight weeks of forecast plus safety "
        "stock. These are separate planning estimates."
    )
    st.subheader("Products requiring action")
    priorities = filtered[filtered["action"] != "Healthy"]
    if priorities.empty:
        st.success("No action flags for the selected products.")
    else:
        show_decisions(priorities)

elif page == "Inventory & Risk":
    st.subheader("Stockout and overstock decision grid")
    fig = px.scatter(
        filtered,
        x="stockout_score",
        y="overstock_score",
        color="action",
        hover_name="SKU",
        hover_data=[
            "recommended_order_units",
            "potential_lost_revenue",
            "excess_capital_tied_up"
        ]
    )
    fig.add_vline(x=1, line_dash="dash")
    fig.add_hline(y=1, line_dash="dash")
    fig.update_layout(
        xaxis_title="Lead-time demand + safety / stock + on-order",
        yaxis_title="On-hand stock / eight-week demand + safety"
    )
    st.plotly_chart(fig, use_container_width=True)
    show_decisions(filtered)

elif page in ["Demand Forecast", "Sales Trend"]:
    chosen = st.selectbox("Select product", selected)
    history = weekly[weekly["SKU"] == chosen].sort_values("Date")

    fig = go.Figure()
    fig.add_scatter(
        x=history["Date"],
        y=history["Units_Sold"],
        name="Actual weekly sales",
        mode="lines"
    )

    if page == "Demand Forecast":
        future = forecasts[
            forecasts["SKU"] == chosen
        ].sort_values("Date")
        fig.add_scatter(
            x=future["Date"],
            y=future["forecast_units"],
            name="Selected forecast",
            mode="lines+markers"
        )
        fig.add_scatter(
            x=future["Date"],
            y=future["baseline_units"],
            name="Seasonal-naive baseline",
            line={"dash": "dash"}
        )

    fig.update_layout(
        title=f"{chosen}: weekly demand",
        xaxis_title="Week beginning",
        yaxis_title="Units"
    )
    st.plotly_chart(fig, use_container_width=True)

    if page == "Demand Forecast":
        st.dataframe(future, hide_index=True)
        st.subheader("Forecast versus actual: held-out test weeks")
        test = validation[
            validation["SKU"] == chosen
        ].sort_values(["fold", "Date"])
        test_fig = go.Figure()
        for column, label in [
            ("Units_Sold", "Actual"),
            ("forecast_units", "Random Forest"),
            ("baseline_units", "Seasonal naive")
        ]:
            test_fig.add_scatter(
                x=test["Date"],
                y=test[column],
                name=label,
                mode="lines"
            )
        st.plotly_chart(test_fig, use_container_width=True)

elif page == "SKU Scoring":
    st.subheader("Forecast and risk lookup")
    st.caption(
        "Look up the saved eight-week forecast and inventory "
        "recommendation for any supported SKU."
    )
    chosen = st.text_input(
        "SKU identifier", value=selected[0]
    ).strip().upper()

    if chosen not in set(risk["SKU"]):
        st.error("Unknown SKU. Try a supported identifier such as SKU001.")
    else:
        row = risk[risk["SKU"] == chosen].iloc[0]
        future = forecasts[
            forecasts["SKU"] == chosen
        ].sort_values("Date")

        st.metric("Recommended action", row["action"])
        st.metric(
            "Suggested order units",
            int(row["recommended_order_units"])
        )
        st.dataframe(future, hide_index=True)

        result = {
            "SKU": chosen,
            "method": metrics["method"],
            "forecast_origin": metrics["forecast_origin"],
            "action": row["action"],
            "recommended_order_units": int(
                row["recommended_order_units"]
            ),
            "snapshot_date": str(row["Snapshot_Date"].date()),
            "potential_lost_revenue": float(
                row["potential_lost_revenue"]
            ),
            "excess_capital_tied_up": float(
                row["excess_capital_tied_up"]
            ),
            "forecast": json.loads(
                future.to_json(
                    orient="records", date_format="iso"
                )
            )
        }
        st.json(result)
        st.download_button(
            "Download SKU result",
            json.dumps(result, indent=2),
            file_name=f"{chosen}_score.json",
            mime="application/json"
        )

else:
    st.subheader("Accuracy and assumptions")
    st.write("Selected method:", metrics["method"])
    a, b = st.columns(2)
    a.metric(
        "Random Forest WAPE",
        f"{metrics['model_wape']:.2%}"
    )
    b.metric(
        "Seasonal-naive WAPE",
        f"{metrics['baseline_wape']:.2%}"
    )
    st.dataframe(pd.DataFrame(metrics["folds"]), hide_index=True)
    st.write(
        "Three expanding training windows each predict eight weeks. "
        "Later forecast weeks use predicted demand for lag features. "
        "The baseline uses demand from 52 weeks earlier. Both methods "
        "are evaluated on the same held-out rows."
    )
    st.write(
        "WAPE is total absolute forecast error divided by total "
        "actual demand. Lower is better."
    )
    st.write(
        "Only complete Monday-to-Sunday sales weeks are included. "
        "The analysis covers 50 SKUs with sales and product metadata; "
        "150 additional inventory-only SKUs are excluded."
    )
    st.write(
        "Prices and costs stay fixed. Demand is assumed uniform within "
        "each week, and all on-order stock is assumed to arrive within "
        "lead time. Prediction intervals are not provided."
    )
    st.write(
        "Reorder when lead-time demand plus safety exceeds stock "
        "plus on-order units. Markdown when on-hand stock exceeds "
        "eight-week demand plus safety. Both flags mean Watch / "
        "Volatile; neither means Healthy."
    )