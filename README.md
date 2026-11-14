# Olist Delivery & Product Quality Dashboard

Proyek analisis data E-Commerce Public Dataset (Olist) untuk menjawab dua pertanyaan bisnis:

1. **Keterlambatan pengiriman per state** — berapa persentase pesanan `delivered` yang tiba melewati estimasi selama Januari–Agustus 2018, dan state mana yang tertinggi?
2. **Performa kategori produk** — kategori mana dengan rata-rata `review_score` terendah pada volume minimal 100 item, dan bagaimana kaitannya dengan durasi pengiriman?

Analisis lanjutan yang diterapkan: **RFM segmentation** dan **geospatial analysis** (sebaran keterlambatan per state).

## Struktur Direktori

```
submission
├── dashboard
│   ├── main_data.csv
│   └── dashboard.py
├── data
│   ├── customers_dataset.csv
│   ├── geolocation_dataset.csv
│   ├── order_items_dataset.csv
│   ├── order_payments_dataset.csv
│   ├── order_reviews_dataset.csv
│   ├── orders_dataset.csv
│   ├── product_category_name_translation.csv
│   ├── products_dataset.csv
│   └── sellers_dataset.csv
├── notebook.ipynb
├── README.md
└── requirements.txt
```

## Setup Environment - Anaconda

```
conda create --name main-ds python=3.13
conda activate main-ds
pip install -r requirements.txt
```

## Run streamlit app

Dashboard membaca `main_data.csv` dari direktori kerja, jadi jalankan dari dalam folder `dashboard`:

```
cd dashboard
streamlit run dashboard.py
```

## Menjalankan Notebook

```
jupyter notebook notebook.ipynb
```

Notebook menggunakan data mentah dari folder `data/` dan menulis ulang `dashboard/main_data.csv` pada cell terakhir, sehingga dashboard selalu memakai data hasil cleaning terbaru.

## Dataset

[E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 99.441 pesanan, 9 tabel relasional, periode September 2016 – Oktober 2018.
