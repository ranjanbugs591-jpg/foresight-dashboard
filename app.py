import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Project FORESIGHT", layout="wide", page_icon="📦")

st.markdown("""
<style>
.kpi-card { padding: 20px; border-radius: 10px; text-align: center; color: white; }
.kpi-value { font-size: 32px; font-weight: 700; }
.kpi-label { font-size: 14px; opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    weekly = pd.read_csv("data/weekly_full.csv", parse_dates=["Date"])
    latest = pd.read_csv("data/latest_risk_snapshot.csv", parse_dates=["Date"])
    return weekly, latest

weekly, latest = load_data()

st.title("📦 Project FORESIGHT — Demand & Inventory Intelligence")
st.caption("NorthBay Retail | AI-Powered Demand & Inventory Intelligence Platform")

page = st.sidebar.radio("Navigate", ["Executive Summary", "Inventory & Risk", "Sales Trend"])

def kpi_card(label, value, color):
    st.markdown(f"""
    <div class="kpi-card" style="background-color:{color};">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

if page == "Executive Summary":
    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Total SKUs", len(latest), "#0F7173")
    with col2: kpi_card("At Stockout Risk", int(latest["stockout_risk"].sum()), "#C0392B")
    with col3: kpi_card("Overstocked SKUs", int(latest["overstock_risk"].sum()), "#D68910")
    with col4: kpi_card("Est. Lost Revenue (Rs)", f"{latest['potential_lost_revenue'].sum():,.0f}", "#922B21")

    st.write("")
    kpi_card("Capital Tied Up in Excess Stock (Rs)", f"{latest['excess_capital_tied_up'].sum():,.0f}", "#B9770E")

    st.write("")
    st.subheader("Category-wise Revenue")
    cat_rev = weekly.groupby("Category")["Revenue"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(cat_rev, x="Category", y="Revenue", color="Category",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Inventory & Risk":
    st.subheader("SKU Risk Table")
    category_filter = st.multiselect(
        "Filter by Category",
        options=latest["Category"].unique(),
        default=list(latest["Category"].unique())
    )
    filtered = latest[latest["Category"].isin(category_filter)]

    def highlight_risk(row):
        if row["stockout_risk"] == 1:
            return ["background-color: #FADBD8"] * len(row)
        elif row["overstock_risk"] == 1:
            return ["background-color: #FDEBD0"] * len(row)
        return [""] * len(row)

    display_cols = ["SKU", "Product_Name", "Category", "Current_Stock", "Reorder_Point",
                     "weeks_of_cover", "stockout_risk", "overstock_risk",
                     "potential_lost_revenue", "excess_capital_tied_up"]

    styled = filtered[display_cols].style.apply(highlight_risk, axis=1).format(
        {"weeks_of_cover": "{:.1f}", "potential_lost_revenue": "{:,.0f}", "excess_capital_tied_up": "{:,.0f}"}
    )
    st.dataframe(styled, use_container_width=True)

elif page == "Sales Trend":
    sku_list = sorted(weekly["SKU"].unique())
    selected_sku = st.selectbox("Select SKU", sku_list)
    sku_data = weekly[weekly["SKU"] == selected_sku].sort_values("Date")

    fig = px.line(sku_data, x="Date", y="Units_Sold", title=f"Weekly Units Sold — {selected_sku}")
    fig.update_traces(line_color="#0F7173")
    st.plotly_chart(fig, use_container_width=True)