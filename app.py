import streamlit as st
import pandas as pd

st.set_page_config(page_title="Project FORESIGHT", layout="wide")

@st.cache_data
def load_data():
    weekly = pd.read_csv("data/weekly_full.csv", parse_dates=["Date"])
    latest = pd.read_csv("data/latest_risk_snapshot.csv", parse_dates=["Date"])
    return weekly, latest

weekly, latest = load_data()

st.title("Project FORESIGHT — Demand & Inventory Intelligence")

page = st.sidebar.radio("Navigate", ["Executive Summary", "Inventory & Risk", "Sales Trend"])

if page == "Executive Summary":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total SKUs", len(latest))
    col2.metric("At Stockout Risk", int(latest["stockout_risk"].sum()))
    col3.metric("Overstocked SKUs", int(latest["overstock_risk"].sum()))
    col4.metric("Est. Lost Revenue (Rs)", f"{latest['potential_lost_revenue'].sum():,.0f}")
    st.metric("Capital Tied Up in Excess Stock (Rs)", f"{latest['excess_capital_tied_up'].sum():,.0f}")

    st.subheader("Category-wise Revenue")
    cat_rev = weekly.groupby("Category")["Revenue"].sum().sort_values(ascending=False)
    st.bar_chart(cat_rev)

elif page == "Inventory & Risk":
    st.subheader("SKU Risk Table")
    category_filter = st.multiselect(
        "Filter by Category",
        options=latest["Category"].unique(),
        default=list(latest["Category"].unique())
    )
    filtered = latest[latest["Category"].isin(category_filter)]
    st.dataframe(filtered[["SKU", "Product_Name", "Category", "Current_Stock", "Reorder_Point",
                            "weeks_of_cover", "stockout_risk", "overstock_risk",
                            "potential_lost_revenue", "excess_capital_tied_up"]])

elif page == "Sales Trend":
    sku_list = sorted(weekly["SKU"].unique())
    selected_sku = st.selectbox("Select SKU", sku_list)
    sku_data = weekly[weekly["SKU"] == selected_sku].sort_values("Date")
    st.line_chart(sku_data.set_index("Date")["Units_Sold"])