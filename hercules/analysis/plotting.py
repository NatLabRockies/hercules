"""Plotting of a single Hercules simulation.

Functions are named for their plotting library (e.g. ``plot_timeseries_plotly``).
"""

import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hercules.analysis.utilities import (
    _require_default_index,
    add_POI_limited_columns,
    POWER_EXPORT_POI_LIMITED,
)
from hercules.hercules_output import HerculesOutput

MAX_POINTS = 20000


def _shading_shapes(times: pd.Series, flags: pd.Series, color: str) -> list[dict]:
    """Return one translucent full-height rectangle per run of 1s in ``flags``."""
    padded = np.concatenate(([0], flags.to_numpy().astype(bool).astype(int), [0]))
    edges = np.diff(padded)
    x = times.to_numpy()
    shapes = []
    for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0], strict=True):
        shapes.append(
            {
                "type": "rect",
                "xref": "x",
                "yref": "paper",
                "x0": x[start],
                "x1": x[min(end, len(x) - 1)],
                "y0": 0,
                "y1": 1,
                "fillcolor": color,
                "opacity": 0.15,
                "line": {"width": 0},
                "layer": "below",
            }
        )
    return shapes


def plot_timeseries_plotly(
    ho: HerculesOutput,
    columns: list = (),
    date_range: tuple[str, str] | None = None,
    plot_dt: float | None = None,
    show_power_export: bool = True,
    LMP_columns: tuple[str, ...] = ("external_signals.LMP_DA", "external_signals.LMP_RT"),
    shade_columns: dict[str, str] | None = None,
    height_per_row: int = 250,
    title: str | None = None,
    save_file: str | None = None,
    open_browser: bool = False,
) -> go.Figure:
    """Plot columns of one simulation as plotly rows that share the time axis.

    Rows, top to bottom: one per entry of ``columns``; then (optionally) plant export with its
    POI-limited value and the interconnect limit; then the LMP columns that exist.

    Args:
        ho (HerculesOutput): Hercules output.
        columns (list): One row per entry; an entry that is a list puts several columns in
            one row. Defaults to no extra rows.
        date_range (tuple[str, str] | None): Inclusive first and last UTC dates
            (``"YYYY-MM-DD"``). Defaults to None (whole simulation).
        plot_dt (float | None): Time between plotted points (s). Defaults to None, which keeps
            at most 20000 points.
        show_power_export (bool): Add the ``plant.power_export`` row (kW). Defaults to True.
        LMP_columns (tuple[str, ...]): LMP columns ($/MWh) for the price row. Defaults to
            ``external_signals.LMP_DA`` and ``external_signals.LMP_RT``.
        shade_columns (dict[str, str] | None): 0/1 columns to shade over all rows, mapped to
            a color, e.g. ``{"controller.battery.in_peak": "gold"}``. Defaults to None.
        height_per_row (int): Figure height per row (px). Defaults to 250.
        title (str | None): Figure title. Defaults to None.
        save_file (str | None): HTML file to write. Defaults to None.
        open_browser (bool): Open ``save_file`` in a browser. Defaults to False.

    Returns:
        go.Figure: The figure.

    Raises:
        ValueError: If a column is missing or ``date_range`` selects no rows.
    """
    _require_default_index(ho)
    rows = [[c] if isinstance(c, str) else list(c) for c in columns]
    if show_power_export:
        if POWER_EXPORT_POI_LIMITED not in ho.df.columns:
            add_POI_limited_columns(ho)
        rows.append(["plant.power_export", POWER_EXPORT_POI_LIMITED])
    LMP_row = [c for c in LMP_columns if c in ho.df.columns]
    if LMP_row:
        rows.append(LMP_row)
    shade_columns = shade_columns or {}
    missing = [c for c in [*sum(rows, []), *shade_columns] if c not in ho.df.columns]
    if missing:
        raise ValueError(f"Columns not found in ho.df: {missing}")

    df = ho.df
    if date_range is not None:
        times = pd.DatetimeIndex(df["time_utc"])
        start = pd.Timestamp(date_range[0], tz="UTC")
        end = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
        df = df[(times >= start) & (times < end)]
        if df.empty:
            raise ValueError(f"date_range {date_range} selects no rows.")
    if plot_dt is None:
        stride = int(np.ceil(len(df) / MAX_POINTS))
    else:
        stride = max(round(plot_dt / float(ho.metadata["dt_sim"])), 1)
    df = df.iloc[::stride]

    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True, vertical_spacing=0.03)
    for i, row in enumerate(rows, start=1):
        for column in row:
            fig.add_trace(
                go.Scatter(x=df["time_utc"], y=df[column], name=column, mode="lines"),
                row=i,
                col=1,
            )
    if show_power_export:
        limit = ho.metadata["h_dict"]["plant"]["interconnect_limit"]
        fig.add_hline(y=limit, line_dash="dash", line_color="gray", row=len(columns) + 1, col=1)

    shapes = []
    for column, color in shade_columns.items():
        shapes += _shading_shapes(df["time_utc"], df[column], color)
        fig.add_trace(
            go.Scatter(x=[None], y=[None], mode="markers", name=column, marker_color=color),
            row=1,
            col=1,
        )
    fig.update_layout(
        shapes=list(fig.layout.shapes) + shapes,
        height=height_per_row * len(rows),
        title=title,
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="Time (UTC)", row=len(rows), col=1)

    if save_file is not None:
        fig.write_html(save_file)
        if open_browser:
            webbrowser.open(Path(save_file).resolve().as_uri())
    return fig
