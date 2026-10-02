import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Amazon Sales & Business Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = Path(__file__).parent / "data" / "Amazon Sales Data India.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(DATA_PATH)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    numeric_cols = [
        "Quantity", "Unit_Price_INR", "Discount_Pct",
        "Total_Sales_INR", "Profit_INR"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Month"] = df["Order_Date"].dt.to_period("M").astype(str)
    df["Profit_Margin_Pct"] = np.where(
        df["Total_Sales_INR"] != 0,
        df["Profit_INR"] / df["Total_Sales_INR"] * 100,
        0
    )
    return df

df = load_data()

# -------------------- Helpers --------------------
def inr(x):
    if pd.isna(x):
        return "₹0"
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"

def pct(x):
    return f"{x:.2f}%"

def metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)

# -------------------- Styling --------------------
st.markdown("""
<style>
.main-title {
    font-size: 2.1rem;
    font-weight: 750;
    margin-bottom: 0;
}
.subtitle {
    color: #6b7280;
    margin-top: 0.15rem;
    margin-bottom: 1.2rem;
}
.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-top: 1.3rem;
}
.small-note {
    color: #6b7280;
    font-size: 0.85rem;
}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.18);
    border-radius: 12px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Header --------------------
st.markdown('<div class="main-title">📊 Amazon Sales & Business Performance Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Management overview of sales, profit, products, orders, payments, fulfillment and geography</div>',
    unsafe_allow_html=True
)

# -------------------- Sidebar filters --------------------
st.sidebar.header("Dashboard Filters")

min_date = df["Order_Date"].min().date()
max_date = df["Order_Date"].max().date()

date_range = st.sidebar.date_input(
    "Order Date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

categories = sorted(df["Category"].dropna().unique().tolist())
states = sorted(df["Ship_State"].dropna().unique().tolist())
statuses = sorted(df["Order_Status"].dropna().unique().tolist())
payments = sorted(df["Payment_Method"].dropna().unique().tolist())
fulfillments = sorted(df["Fulfillment"].dropna().unique().tolist())

sel_categories = st.sidebar.multiselect("Category", categories, default=categories)
sel_states = st.sidebar.multiselect("State", states, default=states)
sel_statuses = st.sidebar.multiselect("Order Status", statuses, default=statuses)
sel_payments = st.sidebar.multiselect("Payment Method", payments, default=payments)
sel_fulfillments = st.sidebar.multiselect("Fulfillment", fulfillments, default=fulfillments)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    (df["Order_Date"].dt.date >= start_date) &
    (df["Order_Date"].dt.date <= end_date) &
    (df["Category"].isin(sel_categories)) &
    (df["Ship_State"].isin(sel_states)) &
    (df["Order_Status"].isin(sel_statuses)) &
    (df["Payment_Method"].isin(sel_payments)) &
    (df["Fulfillment"].isin(sel_fulfillments))
)
d = df.loc[mask].copy()

if d.empty:
    st.warning("No records match the selected filters. Please broaden the filters.")
    st.stop()

# -------------------- KPIs --------------------
total_sales = d["Total_Sales_INR"].sum()
total_profit = d["Profit_INR"].sum()
total_orders = d["Order_ID"].nunique()
total_units = d["Quantity"].sum()
aov = total_sales / total_orders if total_orders else 0
margin = total_profit / total_sales * 100 if total_sales else 0

st.markdown('<div class="section-title">1. Overall Sales & Profit Performance</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: metric_card("Total Sales", inr(total_sales))
with c2: metric_card("Total Profit", inr(total_profit))
with c3: metric_card("Total Orders", f"{total_orders:,}")
with c4: metric_card("Units Sold", f"{total_units:,.0f}")
with c5: metric_card("Average Order Value", inr(aov))
with c6: metric_card("Profit Margin", pct(margin))

# -------------------- Sales / Profit Trend --------------------
monthly = (
    d.groupby("Month", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"))
     .sort_values("Month")
)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=monthly["Month"], y=monthly["Sales"],
    mode="lines+markers", name="Sales",
    hovertemplate="Month: %{x}<br>Sales: ₹%{y:,.0f}<extra></extra>"
))
fig.add_trace(go.Scatter(
    x=monthly["Month"], y=monthly["Profit"],
    mode="lines+markers", name="Profit",
    hovertemplate="Month: %{x}<br>Profit: ₹%{y:,.0f}<extra></extra>"
))
fig.update_layout(
    title="Monthly Sales & Profit Trend",
    xaxis_title="Month",
    yaxis_title="Amount (INR)",
    hovermode="x unified",
    height=430
)
st.plotly_chart(fig, use_container_width=True)

# -------------------- Category & Product --------------------
st.markdown('<div class="section-title">2. Category & Product Performance</div>', unsafe_allow_html=True)

cat = (
    d.groupby("Category", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"),
          Profit=("Profit_INR", "sum"),
          Units=("Quantity", "sum"))
     .sort_values("Sales", ascending=False)
)

left, right = st.columns(2)
with left:
    fig_cat = px.bar(
        cat, x="Category", y="Sales", title="Category-wise Sales",
        text_auto=".2s"
    )
    fig_cat.update_layout(height=380)
    st.plotly_chart(fig_cat, use_container_width=True)

with right:
    fig_profit = px.bar(
        cat, x="Category", y="Profit", title="Category-wise Profit",
        text_auto=".2s"
    )
    fig_profit.update_layout(height=380)
    st.plotly_chart(fig_profit, use_container_width=True)

fig_units = px.bar(
    cat.sort_values("Units", ascending=False),
    x="Category", y="Units", title="Category-wise Units Sold",
    text_auto=".2s"
)
fig_units.update_layout(height=360)
st.plotly_chart(fig_units, use_container_width=True)

top_products = (
    d.groupby("Product", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"),
          Profit=("Profit_INR", "sum"),
          Units=("Quantity", "sum"))
     .sort_values("Sales", ascending=False)
     .head(10)
)

fig_top = px.bar(
    top_products.sort_values("Sales"),
    x="Sales", y="Product", orientation="h",
    title="Top 10 Products by Sales",
    text_auto=".2s"
)
fig_top.update_layout(height=430)
st.plotly_chart(fig_top, use_container_width=True)

# -------------------- Order Status & Revenue Loss --------------------
st.markdown('<div class="section-title">3. Order Status & Revenue Loss</div>', unsafe_allow_html=True)

status_counts = d.groupby("Order_Status", as_index=False).agg(Orders=("Order_ID", "nunique"))
returned = int(status_counts.loc[status_counts["Order_Status"].eq("Returned"), "Orders"].sum())
cancelled = int(status_counts.loc[status_counts["Order_Status"].eq("Cancelled"), "Orders"].sum())
return_rate = returned / total_orders * 100 if total_orders else 0
cancel_rate = cancelled / total_orders * 100 if total_orders else 0

s1, s2, s3, s4, s5, s6 = st.columns(6)
with s1: metric_card("Delivered", f"{int(status_counts.loc[status_counts.Order_Status.eq('Delivered'), 'Orders'].sum()):,}")
with s2: metric_card("Shipped", f"{int(status_counts.loc[status_counts.Order_Status.eq('Shipped'), 'Orders'].sum()):,}")
with s3: metric_card("Returned", f"{returned:,}")
with s4: metric_card("Cancelled", f"{cancelled:,}")
with s5: metric_card("Return Rate", pct(return_rate))
with s6: metric_card("Cancellation Rate", pct(cancel_rate))

left, right = st.columns(2)
with left:
    fig_status = px.pie(
        status_counts, names="Order_Status", values="Orders",
        title="Order Status Distribution", hole=.45
    )
    fig_status.update_layout(height=400)
    st.plotly_chart(fig_status, use_container_width=True)

cat_status = (
    d[d["Order_Status"].isin(["Returned", "Cancelled"])]
    .groupby(["Category", "Order_Status"], as_index=False)
    .agg(Orders=("Order_ID", "nunique"))
)
with right:
    fig_loss = px.bar(
        cat_status, x="Category", y="Orders", color="Order_Status",
        barmode="group", title="Category-wise Returns & Cancellations",
        text_auto=".2s"
    )
    fig_loss.update_layout(height=400)
    st.plotly_chart(fig_loss, use_container_width=True)

# -------------------- Payment / Fulfillment --------------------
st.markdown('<div class="section-title">4. Payment, Fulfillment & Geographic Performance</div>', unsafe_allow_html=True)

pay = (
    d.groupby("Payment_Method", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"), Profit=("Profit_INR", "sum"))
     .sort_values("Sales", ascending=False)
)

left, right = st.columns(2)
with left:
    fig_pay_sales = px.bar(
        pay, x="Payment_Method", y="Sales",
        title="Sales by Payment Method", text_auto=".2s"
    )
    fig_pay_sales.update_layout(height=390)
    st.plotly_chart(fig_pay_sales, use_container_width=True)

with right:
    fig_pay_profit = px.bar(
        pay, x="Payment_Method", y="Profit",
        title="Profit by Payment Method", text_auto=".2s"
    )
    fig_pay_profit.update_layout(height=390)
    st.plotly_chart(fig_pay_profit, use_container_width=True)

ful = (
    d.groupby("Fulfillment", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"),
          Profit=("Profit_INR", "sum"),
          Orders=("Order_ID", "nunique"))
     .sort_values("Sales", ascending=False)
)

left, right = st.columns(2)
with left:
    fig_ful_sales = px.bar(
        ful, x="Fulfillment", y="Sales",
        title="Sales by Fulfillment Method", text_auto=".2s"
    )
    fig_ful_sales.update_layout(height=390)
    st.plotly_chart(fig_ful_sales, use_container_width=True)

with right:
    fig_ful_profit = px.bar(
        ful, x="Fulfillment", y="Profit",
        title="Profit by Fulfillment Method", text_auto=".2s"
    )
    fig_ful_profit.update_layout(height=390)
    st.plotly_chart(fig_ful_profit, use_container_width=True)

# -------------------- Geography --------------------
geo = (
    d.groupby("Ship_State", as_index=False)
     .agg(Sales=("Total_Sales_INR", "sum"),
          Profit=("Profit_INR", "sum"),
          Orders=("Order_ID", "nunique"))
     .sort_values("Sales", ascending=False)
)

st.subheader("Geographic Performance")

left, right = st.columns(2)
with left:
    fig_geo_sales = px.bar(
        geo.sort_values("Sales"),
        x="Sales", y="Ship_State", orientation="h",
        title="State-wise Sales", text_auto=".2s"
    )
    fig_geo_sales.update_layout(height=450)
    st.plotly_chart(fig_geo_sales, use_container_width=True)

with right:
    fig_geo_profit = px.bar(
        geo.sort_values("Profit"),
        x="Profit", y="Ship_State", orientation="h",
        title="State-wise Profit", text_auto=".2s"
    )
    fig_geo_profit.update_layout(height=450)
    st.plotly_chart(fig_geo_profit, use_container_width=True)

fig_geo_orders = px.bar(
    geo.sort_values("Orders"),
    x="Orders", y="Ship_State", orientation="h",
    title="State-wise Orders", text_auto=".2s"
)
fig_geo_orders.update_layout(height=430)
st.plotly_chart(fig_geo_orders, use_container_width=True)

# -------------------- Automated Insights --------------------
st.markdown('<div class="section-title">Management Insights</div>', unsafe_allow_html=True)

best_cat = cat.iloc[0]["Category"]
best_cat_sales = cat.iloc[0]["Sales"]
best_product = top_products.iloc[0]["Product"] if not top_products.empty else "N/A"
best_payment = pay.iloc[0]["Payment_Method"]
best_fulfillment = ful.iloc[0]["Fulfillment"]
best_state = geo.iloc[0]["Ship_State"]

ins1, ins2 = st.columns(2)
with ins1:
    st.info(
        f"📈 **Sales:** Total sales are **{inr(total_sales)}** with a profit margin of **{pct(margin)}**."
    )
    st.info(
        f"🏆 **Category:** **{best_cat}** is the leading category by sales at **{inr(best_cat_sales)}**."
    )
    st.info(
        f"🛍️ **Product:** **{best_product}** is the top product by sales in the selected view."
    )

with ins2:
    st.warning(
        f"⚠️ **Order Risk:** Return rate is **{pct(return_rate)}** and cancellation rate is **{pct(cancel_rate)}**."
    )
    st.info(
        f"💳 **Payment:** **{best_payment}** generates the highest sales in the selected view."
    )
    st.info(
        f"🚚 **Fulfillment:** **{best_fulfillment}** leads fulfillment sales; **{best_state}** leads state-wise sales."
    )

# -------------------- Data Preview / Download --------------------
with st.expander("View Filtered Data"):
    st.dataframe(
        d.sort_values("Order_Date", ascending=False),
        use_container_width=True,
        hide_index=True
    )

csv = d.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download Filtered Data (CSV)",
    data=csv,
    file_name="filtered_amazon_sales_data.csv",
    mime="text/csv"
)

st.caption(
    f"Dashboard contains {len(d):,} filtered records from {len(df):,} total records. "
    f"Data period: {min_date} to {max_date}."
)
