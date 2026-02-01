import streamlit as st

def aplicar_estilos_globales():
    st.markdown("""
    <style>

    /* =========================
       TIPOGRAFÍA GENERAL
    ========================= */
    html, body {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #ffffff;
        color: #1f2933;
    }

    .block-container {
        padding-top: 1.5rem;
    }

    /* =========================
       TARJETAS BASE
    ========================= */
    .card {
        background: #e9fff1;
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
        border-left: 6px solid #76B583;
        margin-bottom: 12px;
    }

    /* =========================
       MÉTRICAS
    ========================= */
    .metric-title {
        font-size: 0.85rem;
        color: #475569;
        letter-spacing: 0.02em;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2933;
        margin-top: 6px;
    }

    /* =========================
       SALUD FINANCIERA
    ========================= */
    .health-title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 6px;
        color: #065f46;
    }

    .health-text {
        font-size: 0.95rem;
        color: #064e3b;
    }

    .health.red {
        border-left-color: #dc2626;
        background: #fff1f2;
    }

    .health.yellow {
        border-left-color: #f59e0b;
        background: #fffbeb;
    }

    /* =========================
       ALERTAS / INSIGHTS
    ========================= */
    .alert {
        background: #f0fdf4;
        border-radius: 14px;
        padding: 16px;
        border-left: 6px solid #76B583;
        margin-bottom: 10px;
    }

    .alert-title {
        font-weight: 600;
        color: #065f46;
        margin-bottom: 4px;
    }

    .alert-action {
        font-size: 0.9rem;
        color: #14532d;
    }

    .alert.red {
        background: #fff1f2;
        border-left-color: #dc2626;
    }

    .alert.yellow {
        background: #fffbeb;
        border-left-color: #f59e0b;
    }

    /* =========================
       DATAFRAME
    ========================= */
    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    </style>
    """, unsafe_allow_html=True)
