"""
Fig. 11 — thermal environment of a domestic refrigerator, measured by the node.

Uses only the steady-state window of the 02-04.10.2026 run (the first 3.6 h of
placement and pull-down transient are excluded). No produce was present in this
run: the CO2 channel is shown to document that it decays towards ambient in the
absence of a respiring load, which is the control condition for the breach trial.
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "figures")
RAW = os.path.join(HERE, "RTEU_Tracer", "refrigerator _7CDFA1FE05B5_05102026.csv")
STEADY_FROM = "2026-10-02 18:00"

INK, BLUE, ORANGE, GREEN, GREY = "#1a1a1a", "#0072B2", "#E69F00", "#009E73", "#8c8c8c"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5,
                     "axes.linewidth": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42})


def load_fridge():
    df = pd.read_csv(RAW, header=None, names=["T", "RH", "CO2", "ts", "flag"], dtype=str)
    for c in ["T", "RH", "CO2", "flag"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(df["ts"], format="%d-%m-%y %H:%M", errors="coerce")
    df = df.dropna(subset=["ts"])
    # the export interleaves two logging streams; the refrigerated one never exceeds 10 C
    d = df[df["T"] < 10].groupby("ts", as_index=False).mean(numeric_only=True)
    d = d[d["CO2"] < 3000].sort_values("ts")          # drop a single door-opening spike
    return d[d.ts >= STEADY_FROM].reset_index(drop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    d = load_fridge()
    hours = (d.ts.iloc[-1] - d.ts.iloc[0]).total_seconds() / 3600

    fig, ax = plt.subplots(3, 1, figsize=(7.0, 5.6), sharex=True,
                           gridspec_kw={"height_ratios": [2.0, 1.0, 1.2], "hspace": 0.18})

    # ---- temperature + compressor cycles
    ax[0].plot(d.ts, d["T"], lw=0.8, color=BLUE)
    mean = d["T"].mean()
    ax[0].axhline(mean, color=INK, lw=0.9, ls="--")
    ax[0].axhline(4.0, color=ORANGE, lw=0.9, ls=":")
    r = d.set_index("ts")["T"].resample("2min").mean().interpolate()
    pk, _ = find_peaks(r.values, prominence=1.5)
    tr, _ = find_peaks(-r.values, prominence=1.5)
    ax[0].plot(r.index[pk], r.values[pk], "v", ms=3.5, color=ORANGE, mec=INK, mew=0.4)
    ax[0].plot(r.index[tr], r.values[tr], "^", ms=3.5, color=GREEN, mec=INK, mew=0.4)
    ax[0].fill_between(d.ts, 4.0, d["T"], where=d["T"] > 4.0, color=ORANGE, alpha=0.18, lw=0)
    ax[0].set_ylabel("Temperature (°C)")
    ax[0].text(0.012, 0.93,
               f"mean {mean:.2f} °C · cycles between {r.values[tr].mean():.1f} and "
               f"{r.values[pk].mean():.1f} °C · period {np.median(np.diff(r.index[pk].values).astype('timedelta64[m]').astype(float)):.0f} min",
               transform=ax[0].transAxes, fontsize=7.4, va="top")
    ax[0].text(0.012, 0.055, f"{100*(d['T']>4).mean():.0f} % of the time above the 4 °C set point "
                             "(shaded)", transform=ax[0].transAxes, fontsize=7.2, color=ORANGE)
    ax[0].set_ylim(-0.6, 9.6)

    # ---- relative humidity
    ax[1].plot(d.ts, d["RH"], lw=0.8, color=GREEN)
    ax[1].set_ylabel("RH (%)")
    ax[1].text(0.012, 0.88, f"tracks temperature, r = {d['T'].corr(d['RH']):.3f}",
               transform=ax[1].transAxes, fontsize=7.4, va="top")

    # ---- CO2
    ax[2].plot(d.ts, d["CO2"], lw=0.8, color=GREY)
    t_h = (d.ts - d.ts.iloc[0]).dt.total_seconds() / 3600
    k = np.polyfit(t_h, d["CO2"], 1)
    ax[2].plot(d.ts, np.polyval(k, t_h), lw=1.1, color=INK, ls="--")
    ax[2].set_ylabel("CO₂ (ppm)")
    ax[2].text(0.012, 0.16,
               f"no produce present: {k[0]:+.1f} ppm/h, decaying towards ambient",
               transform=ax[2].transAxes, fontsize=7.4, va="top")
    ax[2].set_xlabel(f"{d.ts.iloc[0]:%d %b %Y %H:%M} → {d.ts.iloc[-1]:%d %b %H:%M}  "
                     f"({hours:.0f} h continuous, 1 min sampling)")
    ax[2].xaxis.set_major_locator(HourLocator(interval=6))
    ax[2].xaxis.set_major_formatter(DateFormatter("%d %b" + chr(10) + "%H:%M"))

    for a in ax:
        a.grid(alpha=0.25, lw=0.5)
        a.tick_params(labelsize=7.6)

    for ext, kw in (("pdf", {}), ("png", {"dpi": 600})):
        fig.savefig(os.path.join(OUT, f"fig11_fridge_dynamics.{ext}"),
                    bbox_inches="tight", facecolor="white", **kw)
    plt.close(fig)
    print("wrote fig11_fridge_dynamics")
    print(f"  window {d.ts.iloc[0]} .. {d.ts.iloc[-1]} ({hours:.1f} h, {len(d)} points)")
    print(f"  T mean {mean:.2f}  min {d['T'].min():.1f}  max {d['T'].max():.1f}")


if __name__ == "__main__":
    main()
