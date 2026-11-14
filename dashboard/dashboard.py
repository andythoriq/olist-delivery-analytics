from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency

sns.set_theme(style="whitegrid")

# ---------------------------------------------------------------
# Helper function untuk menyiapkan dataframe
# ---------------------------------------------------------------


def create_late_by_state_df(df):
    late_by_state_df = (
        df.groupby("customer_state")
        .agg(
            total_order=("order_id", "nunique"),
            late_order=("is_late", "sum"),
            avg_delivery_days=("delivery_days", "mean"),
        )
        .assign(late_rate=lambda d: d.late_order / d.total_order * 100)
        .sort_values("late_rate", ascending=False)
        .reset_index()
    )
    return late_by_state_df


def create_monthly_df(df):
    monthly_df = (
        df.groupby("purchase_month")
        .agg(
            order_count=("order_id", "nunique"),
            late_rate=("is_late", "mean"),
            avg_review=("review_score", "mean"),
        )
        .assign(late_rate=lambda d: d.late_rate * 100)
        .reset_index()
    )
    return monthly_df


def create_category_df(df):
    # Ambang volume menyesuaikan ukuran data agar tabel tidak kosong saat filter dipersempit
    min_items = 100 if len(df) >= 5000 else 20
    category_df = (
        df.groupby("product_category")
        .agg(
            total_item=("n_items", "sum"),
            avg_review=("review_score", "mean"),
            avg_delivery_days=("delivery_days", "mean"),
            late_rate=("is_late", "mean"),
            revenue=("total_price", "sum"),
        )
        .query("total_item >= @min_items")
        .assign(late_rate=lambda d: d.late_rate * 100)
        .sort_values("avg_review")
        .reset_index()
    )
    return category_df


def create_state_geo_df(df):
    state_geo_df = (
        df.groupby("customer_state")
        .agg(
            late_rate=("is_late", "mean"),
            orders=("order_id", "nunique"),
            lat=("lat", "median"),
            lng=("lng", "median"),
        )
        .assign(late_rate=lambda d: d.late_rate * 100)
        .reset_index()
    )
    return state_geo_df


def create_rfm_df(df):
    snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

    rfm_df = (
        df.groupby("customer_unique_id")
        .agg(
            last_order=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("total_price", "sum"),
        )
        .reset_index()
    )
    rfm_df["recency"] = (snapshot_date - rfm_df["last_order"]).dt.days

    rfm_df["r_score"] = pd.qcut(rfm_df["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
    rfm_df["f_score"] = pd.qcut(
        rfm_df["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]
    ).astype(int)
    rfm_df["m_score"] = pd.qcut(rfm_df["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)

    def segment_customer(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 3 and f >= 3 and m >= 3:
            return "Champions"
        if r >= 3 and f <= 2:
            return "New / Potential"
        if r == 2 and f >= 3:
            return "At Risk (High Value)"
        if r == 1 and f >= 3:
            return "Hibernating (High Value)"
        if r == 1:
            return "Lost"
        return "Need Attention"

    rfm_df["segment"] = rfm_df.apply(segment_customer, axis=1)
    return rfm_df


# ---------------------------------------------------------------
# Load data
# ---------------------------------------------------------------
# Path relatif terhadap lokasi file ini, bukan working directory,
# agar tetap jalan di lokal maupun di Streamlit Community Cloud
DATA_PATH = Path(__file__).resolve().parent / "main_data.csv"
all_df = pd.read_csv(DATA_PATH)

datetime_columns = [
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
all_df = all_df.sort_values("order_purchase_timestamp").reset_index(drop=True)

for column in datetime_columns:
    all_df[column] = pd.to_datetime(all_df[column])

all_df["purchase_month"] = all_df["order_purchase_timestamp"].dt.to_period("M").astype(str)
all_df["is_late"] = all_df["is_late"].astype(bool)

# ---------------------------------------------------------------
# Sidebar filter
# ---------------------------------------------------------------
min_date = all_df["order_purchase_timestamp"].min().date()
max_date = all_df["order_purchase_timestamp"].max().date()

with st.sidebar:
    start_date, end_date = st.date_input(
        label="Rentang Waktu",
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date],
        key="date_range",
    )

main_df = all_df[
    (all_df["order_purchase_timestamp"] >= str(start_date))
    & (all_df["order_purchase_timestamp"] <= f"{end_date} 23:59:59")
]

if main_df.empty:
    st.warning("Tidak ada pesanan pada rentang tanggal tersebut. Silakan pilih rentang lain.")
    st.stop()

if len(main_df) < 200:
    st.warning(
        "Rentang tanggal terlalu sempit untuk analisis yang stabil "
        f"({len(main_df):,} pesanan). Silakan perlebar rentang tanggal."
    )
    st.stop()

# ---------------------------------------------------------------
# Siapkan dataframe
# ---------------------------------------------------------------
late_by_state_df = create_late_by_state_df(main_df)
monthly_df = create_monthly_df(main_df)
category_df = create_category_df(main_df)
state_geo_df = create_state_geo_df(main_df)
rfm_df = create_rfm_df(main_df)

# ---------------------------------------------------------------
# Header & metrik utama
# ---------------------------------------------------------------
st.header("Olist Delivery & Product Quality Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Orders", value=f"{main_df['order_id'].nunique():,}")

with col2:
    revenue = main_df["total_price"].sum()
    st.metric("Total Revenue", value=format_currency(revenue, "BRL", locale="pt_BR"))

with col3:
    st.metric("Late Delivery Rate", value=f"{main_df['is_late'].mean():.2%}")

with col4:
    st.metric("Avg Review Score", value=f"{main_df['review_score'].mean():.2f}")

st.divider()

# ---------------------------------------------------------------
# Pertanyaan 1: keterlambatan per state
# ---------------------------------------------------------------
st.subheader("Pertanyaan 1 — Keterlambatan Pengiriman per State")

col1, col2 = st.columns(2)

with col1:
    top10 = late_by_state_df.head(10).sort_values("late_rate")
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(
        data=top10,
        y="customer_state",
        x="late_rate",
        hue="customer_state",
        palette="Reds_r",
        legend=False,
        ax=ax,
    )
    ax.axvline(
        main_df["is_late"].mean() * 100,
        color="navy",
        linestyle="--",
        linewidth=1.5,
        label=f"Rata-rata ({main_df['is_late'].mean():.1%})",
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title("10 State dengan Keterlambatan Tertinggi")
    ax.set_xlabel("Order terlambat (%)")
    ax.set_ylabel("State")
    st.pyplot(fig)
    plt.close(fig)

with col2:
    fig, ax = plt.subplots(figsize=(9, 6))
    scatter = ax.scatter(
        state_geo_df["lng"],
        state_geo_df["lat"],
        s=state_geo_df["orders"] / 30,
        c=state_geo_df["late_rate"],
        cmap="Reds",
        alpha=0.8,
        edgecolor="black",
        linewidth=0.6,
    )
    for _, row in state_geo_df.iterrows():
        ax.annotate(
            row["customer_state"],
            (row["lng"], row["lat"]),
            fontsize=7,
            ha="center",
            va="center",
            xytext=(0, 10),
            textcoords="offset points",
        )
    plt.colorbar(scatter, ax=ax, label="Order terlambat (%)")
    ax.set_title("Sebaran Spasial Keterlambatan")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    st.pyplot(fig)
    plt.close(fig)

fig, ax = plt.subplots(figsize=(16, 5))
sns.lineplot(
    data=monthly_df,
    x="purchase_month",
    y="late_rate",
    marker="o",
    linewidth=2,
    color="#c0392b",
    ax=ax,
)
ax.set_title("Tren Keterlambatan Pengiriman per Bulan")
ax.set_xlabel("Bulan")
ax.set_ylabel("Order terlambat (%)")
ax.tick_params(axis="x", rotation=60)
st.pyplot(fig)
plt.close(fig)

st.divider()

# ---------------------------------------------------------------
# Pertanyaan 2: performa kategori produk
# ---------------------------------------------------------------
st.subheader("Pertanyaan 2 — Performa Kategori Produk")

col1, col2 = st.columns(2)

with col1:
    bottom8 = category_df.head(8).sort_values("avg_review")
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(
        data=bottom8,
        y="product_category",
        x="avg_review",
        hue="product_category",
        palette="Reds_r",
        legend=False,
        ax=ax,
    )
    ax.axvline(4.0, color="navy", linestyle="--", linewidth=1.5, label="Ambang 4.0")
    ax.set_xlim(1, 5)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title("8 Kategori dengan Review Terendah")
    ax.set_xlabel("Rata-rata review score")
    ax.set_ylabel("Kategori produk")
    st.pyplot(fig)
    plt.close(fig)

with col2:
    fig, ax = plt.subplots(figsize=(9, 6))
    scatter = ax.scatter(
        category_df["avg_delivery_days"],
        category_df["avg_review"],
        s=category_df["total_item"] / 6,
        c=category_df["late_rate"],
        cmap="Reds",
        alpha=0.75,
        edgecolor="grey",
        linewidth=0.5,
    )
    ax.axhline(4.0, color="navy", linestyle="--", linewidth=1.2)
    ax.set_title("Durasi Kirim vs Review per Kategori")
    ax.set_xlabel("Rata-rata durasi pengiriman (hari)")
    ax.set_ylabel("Rata-rata review score")
    plt.colorbar(scatter, ax=ax, label="Order terlambat (%)")
    st.pyplot(fig)
    plt.close(fig)

st.divider()

# ---------------------------------------------------------------
# Analisis lanjutan: RFM
# ---------------------------------------------------------------
st.subheader("Analisis Lanjutan — RFM Segmentation")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Avg Recency (hari)", value=round(rfm_df["recency"].mean(), 1))

with col2:
    st.metric("Avg Frequency", value=round(rfm_df["frequency"].mean(), 2))

with col3:
    st.metric(
        "Avg Monetary",
        value=format_currency(rfm_df["monetary"].mean(), "BRL", locale="pt_BR"),
    )

segment_df = (
    rfm_df.groupby("segment")
    .agg(
        customers=("customer_unique_id", "count"),
        total_revenue=("monetary", "sum"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
    )
    .assign(
        revenue_share=lambda d: d["total_revenue"] / d["total_revenue"].sum() * 100
    )
    .sort_values("total_revenue", ascending=False)
    .reset_index()
)

col1, col2 = st.columns(2)

with col1:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=segment_df,
        y="segment",
        x="customers",
        hue="segment",
        palette="Blues_r",
        legend=False,
        ax=ax,
    )
    ax.set_title("Jumlah Pelanggan per Segmen")
    ax.set_xlabel("Jumlah pelanggan")
    ax.set_ylabel(None)
    st.pyplot(fig)
    plt.close(fig)

with col2:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=segment_df,
        y="segment",
        x="revenue_share",
        hue="segment",
        palette="Greens_r",
        legend=False,
        ax=ax,
    )
    ax.set_title("Kontribusi Pendapatan per Segmen")
    ax.set_xlabel("Porsi pendapatan (%)")
    ax.set_ylabel(None)
    st.pyplot(fig)
    plt.close(fig)

with st.expander("Lihat tabel ringkasan segmen"):
    st.dataframe(
        segment_df.rename(
            columns={
                "segment": "Segmen",
                "customers": "Pelanggan",
                "total_revenue": "Total Revenue",
                "avg_recency": "Avg Recency",
                "avg_frequency": "Avg Frequency",
                "revenue_share": "Revenue Share (%)",
            }
        ),
        hide_index=True,
    )
