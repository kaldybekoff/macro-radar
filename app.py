from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from macro_radar.analytics import (
    comparison,
    freshness_status,
    latest_per_indicator,
    prepare_frame,
    previous_change,
)
from macro_radar.config import load_settings
from macro_radar.ingestion import run_ingestion
from macro_radar.models import INDICATORS
from macro_radar.reports import build_excel, build_powerpoint
from macro_radar.repository import SupabaseRepository


st.set_page_config(page_title="Macro Radar Kazakhstan", page_icon="📊", layout="wide")


def _secret_values() -> dict[str, object]:
    keys = (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "REQUEST_TIMEOUT",
        "MANUAL_BASE_RATE",
        "MANUAL_TONIA_RATE",
    )
    values: dict[str, object] = {}
    for key in keys:
        try:
            if key in st.secrets:
                values[key] = st.secrets[key]
        except FileNotFoundError:
            break
    return values


settings = load_settings(_secret_values())


@st.cache_resource
def get_repository(url: str, key: str) -> SupabaseRepository:
    return SupabaseRepository(url, key)


def format_delta(value: float | None) -> str | None:
    return None if value is None else f"{value:+.2f}"


st.title("Macro Radar Kazakhstan")
st.caption("Личный мониторинг макроэкономических показателей")

if not settings.supabase_configured:
    st.error("Supabase не настроен.")
    st.code(
        'SUPABASE_URL = "https://your-project.supabase.co"\n'
        'SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"',
        language="toml",
    )
    st.info("Добавьте значения в Streamlit Secrets или переменные окружения.")
    st.stop()

repository = get_repository(settings.supabase_url, settings.supabase_service_role_key)

with st.sidebar:
    st.header("Управление")
    if st.button("Обновить данные", type="primary", use_container_width=True):
        with st.spinner("Получаем и проверяем данные..."):
            result = run_ingestion(repository, settings, trigger_type="manual")
        if result.status == "success":
            st.success(f"Обновлено записей: {result.records_received}")
        elif result.status == "partial":
            st.warning(f"Частичное обновление: {result.records_received} записей")
            for error in result.errors:
                st.error(error)
        else:
            st.error("Обновить данные не удалось")
            for error in result.errors:
                st.error(error)
        st.cache_data.clear()

    history_days = st.selectbox("Период графиков", (90, 180, 365, 730), index=2)


@st.cache_data(ttl=300)
def load_records(since_iso: str) -> list[dict[str, object]]:
    return repository.get_observations(since=date.fromisoformat(since_iso))


records = load_records((date.today() - timedelta(days=int(history_days))).isoformat())
frame = prepare_frame(records)

if frame.empty:
    st.warning("В Supabase пока нет данных. Нажмите «Обновить данные» в боковом меню.")
    st.stop()

latest = latest_per_indicator(frame)
freshness = freshness_status(frame)
stale = [INDICATORS.get(code, {"label": code})["label"] for code, item in freshness.items() if item["is_stale"]]
if stale:
    st.warning("Устаревшие данные: " + ", ".join(stale) + ". Показаны последние успешные значения.")
else:
    st.success("Все доступные источники актуальны.")

metric_codes = ("USD_KZT", "CPI_YOY", "NBK_BASE_RATE", "TONIA", "BRENT_USD")
columns = st.columns(5)
for column, code in zip(columns, metric_codes):
    with column:
        if code not in latest.index:
            st.metric(INDICATORS[code]["label"], "Нет данных")
            continue
        row = latest.loc[code]
        st.metric(
            INDICATORS[code]["label"],
            f"{float(row['value']):.2f} {row['unit']}",
            format_delta(previous_change(frame, code)),
            help=f"Период: {pd.Timestamp(row['period']).date()} · Источник: {row['source']}",
        )

st.subheader("Изменения")
comparison_rows = []
for code in metric_codes:
    if code not in latest.index:
        continue
    comparison_rows.append(
        {
            "Показатель": INDICATORS[code]["label"],
            "Последнее наблюдение": float(latest.loc[code, "value"]),
            "К предыдущему": previous_change(frame, code),
            "За неделю": comparison(frame, code, 7),
            "За месяц": comparison(frame, code, 30),
            "Период": pd.Timestamp(latest.loc[code, "period"]).date(),
        }
    )
st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader("USD/KZT")
    fx = frame.loc[frame["indicator_code"] == "USD_KZT", ["period", "value"]]
    if not fx.empty:
        st.line_chart(fx.set_index("period"), y="value")
with right:
    st.subheader("Brent")
    oil = frame.loc[frame["indicator_code"] == "BRENT_USD", ["period", "value"]]
    if not oil.empty:
        st.line_chart(oil.set_index("period"), y="value")

st.subheader("Инфляция")
inflation_codes = ["CPI_YOY", "CPI_FOOD_YOY", "CPI_NON_FOOD_YOY", "CPI_SERVICES_YOY"]
inflation = frame.loc[frame["indicator_code"].isin(inflation_codes), ["period", "indicator_code", "value"]]
if not inflation.empty:
    inflation_wide = inflation.pivot_table(index="period", columns="indicator_code", values="value", aggfunc="last")
    inflation_wide = inflation_wide.rename(columns={code: INDICATORS[code]["label"] for code in inflation_codes})
    st.line_chart(inflation_wide)

st.subheader("Экспорт")
export_left, export_right = st.columns(2)
with export_left:
    st.download_button(
        "Скачать Excel",
        data=build_excel(records),
        file_name=f"macro_radar_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with export_right:
    st.download_button(
        "Скачать PowerPoint",
        data=build_powerpoint(records, settings.template_path),
        file_name=f"macro_radar_{date.today().isoformat()}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )

with st.expander("Последние запуски обновления"):
    runs = repository.get_recent_runs()
    if runs:
        st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
    else:
        st.caption("Запусков пока нет.")

with st.expander("Исходные данные"):
    display_columns = ["indicator_code", "period", "value", "unit", "source", "quality_status"]
    st.dataframe(frame[display_columns].sort_values("period", ascending=False), use_container_width=True, hide_index=True)
