"""Render the system architecture diagram (docs/architecture.png).

A single clean figure of the closed loop across the three pillars, matching the
product's visual language. Embedded in the README and the deck.

    python scripts/make_diagram.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from chimera.config import REPO_ROOT

INK = "#06070a"; PANEL = "#0e1016"; EDGE = "#252b38"; MIST = "#e7e9ee"; MUTE = "#8a909f"
DEFENSE = "#39d3b6"; THREAT = "#ff5c49"; AGENTIC = "#8b8cf0"; SIGNAL = "#5ea0ff"


def box(ax, x, y, w, h, title, lines, accent):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                linewidth=1.2, edgecolor=EDGE, facecolor=PANEL))
    ax.add_patch(plt.Rectangle((x + 0.06, y + h - 0.16), 0.5, 0.05, color=accent))
    ax.text(x + 0.18, y + h - 0.34, title, color=accent, fontsize=12, fontweight="bold")
    for i, ln in enumerate(lines):
        ax.text(x + 0.18, y + h - 0.62 - i * 0.28, ln, color=MIST, fontsize=9)


def arrow(ax, xy1, xy2, color=MUTE, label=None, rad=0.0):
    ax.add_patch(FancyArrowPatch(xy1, xy2, arrowstyle="-|>", mutation_scale=14,
                                 linewidth=1.4, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx, my = (xy1[0] + xy2[0]) / 2, (xy1[1] + xy2[1]) / 2
        ax.text(mx, my + 0.12, label, color=MUTE, fontsize=8, ha="center")


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=170)
    fig.patch.set_facecolor(INK); ax.set_facecolor(INK)
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")

    ax.text(0.3, 5.85, "Chimera", color=MIST, fontsize=17, fontweight="bold")
    ax.text(2.15, 5.87, "closed-loop adversarial payment-fraud lab", color=MUTE, fontsize=10)

    box(ax, 0.3, 3.4, 3.4, 1.9, "IDENTIFY", [
        "ATT&CK-style taxonomy (15)", "RAG intel corpus", "LangGraph + Groq", "ideation agent"], AGENTIC)
    box(ax, 4.3, 3.4, 3.4, 1.9, "GENERATE", [
        "multi-rail simulator", "entity graph + hard negatives", "8 attack synthesizers",
        "adversarial evasion search"], THREAT)
    box(ax, 8.3, 3.4, 3.4, 1.9, "DEFEND", [
        "LightGBM + novelty channel", "(isolation forest + PCA)", "SHAP reason codes",
        "PR-AUC / FPR@recall eval"], DEFENSE)

    arrow(ax, (3.7, 4.35), (4.3, 4.35), AGENTIC, "attack specs")
    arrow(ax, (7.7, 4.35), (8.3, 4.35), THREAT, "labelled stream")

    # Feedback loop
    box(ax, 3.1, 1.0, 5.8, 1.2, "CLOSED LOOP", [
        "identify -> generate (evolve evasion) -> detect -> evaluate -> retrain on breaches -> re-ideate",
        "measured by the hardening curve: breach recall vs recovered recall per round"], SIGNAL)
    arrow(ax, (10.0, 3.4), (8.9, 2.2), SIGNAL, rad=-0.25)
    arrow(ax, (3.1, 1.9), (2.0, 3.4), SIGNAL, "gaps feed next round", rad=-0.25)

    # Web prototype strip
    ax.text(0.3, 0.45, "Web console: threat matrix · attack lab · closed-loop · network graph · detection & explainability",
            color=MUTE, fontsize=9)

    fig.tight_layout()
    out = REPO_ROOT / "docs" / "architecture.png"
    fig.savefig(out, facecolor=INK, bbox_inches="tight"); plt.close(fig)
    print(f"Saved diagram -> {out}")


if __name__ == "__main__":
    main()
