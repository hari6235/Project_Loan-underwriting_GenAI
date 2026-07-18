# FILE: eval/dashboard.py
"""Streamlit eval dashboard page (Section 3.5's "trend graphs" +
Section 5.2's "eval dashboard" requirement). Rendered as a page/tab inside
app.py (the main Streamlit UI) via render_eval_dashboard(), not a
standalone app, so it shares auth/session state with the rest of the UI.
"""
from __future__ import annotations

import glob
import json
import os

import streamlit as st


def _load_history(history_dir: str = "reports/regression_history") -> list[dict]:
    reports = []
    for path in sorted(glob.glob(os.path.join(history_dir, "*.json"))):
        try:
            with open(path, "r") as f:
                reports.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return reports


def render_eval_dashboard() -> None:
    st.subheader("Evaluation Dashboard")

    history = _load_history()
    if not history:
        st.info(
            "No regression runs recorded yet. Trigger one via POST /eval/regression "
            "(or the button below) to populate trend data."
        )
        if st.button("Run regression suite now"):
            with st.spinner("Running regression suite against the golden set..."):
                from eval.regression_suite import run_regression_suite
                report = run_regression_suite()
            st.success(f"Regression run complete -- overall_pass={report.get('overall_pass')}")
            st.rerun()
        return

    latest = history[-1]
    st.markdown(f"**Latest run:** {latest.get('timestamp')} -- "
                f"overall_pass = `{latest.get('overall_pass')}` "
                f"({latest.get('overall_pass_rate', 0):.0%} of checked metrics passing)"
                if latest.get("overall_pass_rate") is not None else "**Latest run:** (no metrics available)")

    metric_names = sorted({m for report in history for m in report.get("checks", {})})
    selected_metric = st.selectbox("Metric", metric_names)

    if selected_metric:
        rows = []
        for report in history:
            check = report.get("checks", {}).get(selected_metric)
            if check and check.get("value") is not None:
                rows.append({"timestamp": report.get("timestamp"), "value": check["value"]})
        if rows:
            try:
                import pandas as pd
                df = pd.DataFrame(rows).set_index("timestamp")
                st.line_chart(df)
            except ImportError:
                st.table(rows)
        else:
            st.info(f"No recorded values for '{selected_metric}' yet.")

    st.markdown("---")
    st.markdown("**Latest check details:**")
    st.json(latest.get("checks", {}))

    if len(history) >= 2:
        st.markdown("---")
        st.markdown("**Compare last two runs:**")
        from eval.comparator import compare_reports
        comparison = compare_reports(history[-2], history[-1], "previous", "latest")
        st.json(comparison)

    if st.button("Run regression suite again"):
        with st.spinner("Running regression suite..."):
            from eval.regression_suite import run_regression_suite
            run_regression_suite()
        st.rerun()