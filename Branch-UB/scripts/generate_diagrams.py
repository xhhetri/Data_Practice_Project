"""
scripts/generate_diagrams.py
-----------------------------
One-off script that draws the two diagrams the assessment brief asks for
(architecture + workflow), matching the actual current pipeline in
src/analysis/. Not part of run_pipeline.py -- these change rarely, only
when the architecture itself changes, so they're generated on demand:

    python scripts/generate_diagrams.py

Uses matplotlib only (already a dependency) rather than adding graphviz,
since two static box-and-arrow diagrams don't need a graph-layout engine.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

REPO_ROOT = Path(__file__).resolve().parents[1]

BOX_STYLE = dict(boxstyle="round,pad=0.4", linewidth=1.3)
COLORS = {
    "source": "#E8EAF6",
    "bronze": "#FFF3E0",
    "clean": "#E1F5FE",
    "output": "#E8F5E9",
    "consumer": "#FCE4EC",
    "orchestrator": "#F5F5F5",
}


def _box(ax, xy, w, h, text, color, fontsize=9):
    x, y = xy
    box = FancyBboxPatch(
        (x, y), w, h, facecolor=color, edgecolor="black", **BOX_STYLE
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)
    return (x + w / 2, y + h / 2, x, y, w, h)


def _arrow(ax, start_box, end_box, start_side="bottom", end_side="top"):
    sx, sy, sx0, sy0, sw, sh = start_box
    ex, ey, ex0, ey0, ew, eh = end_box
    side_point = {
        "top": lambda x, y, x0, y0, w, h: (x, y0 + h),
        "bottom": lambda x, y, x0, y0, w, h: (x, y0),
        "left": lambda x, y, x0, y0, w, h: (x0, y),
        "right": lambda x, y, x0, y0, w, h: (x0 + w, y),
    }
    p1 = side_point[start_side](sx, sy, sx0, sy0, sw, sh)
    p2 = side_point[end_side](ex, ey, ex0, ey0, ew, eh)
    arrow = FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=14,
        linewidth=1.2, color="#333333",
    )
    ax.add_patch(arrow)


def draw_architecture_diagram(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12)
    ax.axis("off")
    ax.set_title(
        "System Architecture — Transport Emissions Decision Support (Australia)\n"
        "(current: src/analysis/, single flat pipeline, 7 sources)",
        fontsize=12, fontweight="bold",
    )

    sources = _box(ax, (0.3, 10.2), 11.4, 0.9,
                    "7 source files (fixtures/ or real downloads)\n"
                    "petroleum stats · GHG inventories · NGA factors ·\n"
                    "BITRE yearbook · vehicle registrations · quarterly GHG · population",
                    COLORS["source"], fontsize=8)

    bronze = _box(ax, (4.2, 8.6), 3.6, 0.9,
                   "data/bronze/<source>/<date>/\n(raw landing zone, dated)",
                   COLORS["bronze"])
    _arrow(ax, sources, bronze)

    clean = _box(ax, (4.2, 7.0), 3.6, 1.0,
                  "src/analysis/clean.py\nload -> standardise -> merge\n(_locate() auto-picks real data over samples)",
                  COLORS["clean"])
    _arrow(ax, bronze, clean)

    out1 = _box(ax, (1.0, 5.2), 3.3, 1.2, "annual_master.csv\n(main model input)", COLORS["output"], 8)
    out2 = _box(ax, (4.5, 5.2), 3.3, 1.2, "annual_master_\nwith_population.csv\n(per-capita)", COLORS["output"], 8)
    out3 = _box(ax, (8.0, 5.2), 3.3, 1.2, "monthly_fuel_\nseries.csv\n(forecast input)", COLORS["output"], 8)
    for o in (out1, out2, out3):
        _arrow(ax, clean, o)

    eda = _box(ax, (0.3, 2.8), 3.7, 1.3,
                "src/analysis/eda.py\n-> reports/figures/*.png\n(7 figures)", COLORS["consumer"], 8)
    model = _box(ax, (4.3, 2.8), 3.7, 1.3,
                  "src/analysis/model.py\n-> reports/model_results/\n(regression + fuel forecast)", COLORS["consumer"], 8)
    validate = _box(ax, (8.3, 2.8), 3.3, 1.3,
                     "src/analysis/validate.py\n-> reports/validation/\n(fuel x factor check)",
                     COLORS["consumer"], 8)
    for o in (out1, out2):
        _arrow(ax, o, eda, start_side="bottom", end_side="top")
    for o in (out1, out3):
        _arrow(ax, o, model, start_side="bottom", end_side="top")
    _arrow(ax, out1, validate, start_side="bottom", end_side="top")

    orch = _box(ax, (3.2, 0.4), 5.6, 1.0,
                 "run_pipeline.py — orchestrates clean -> eda -> model -> validate\n"
                 "(single command, no scheduler/orchestration layer)",
                 COLORS["orchestrator"], 8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_path}")


def draw_workflow_diagram(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 11))
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 15)
    ax.axis("off")
    ax.set_title("Team Workflow", fontsize=12, fontweight="bold")

    steps = [
        "1. Download real source file\n(see README §Data sources)",
        "2. Drop into\ndata/bronze/<source>/<date>/\n(filename must NOT contain 'SAMPLE')",
        "3. Run: python run_pipeline.py\n(clean.py auto-detects real data)",
        "4. Review reports/figures/,\nreports/model_results/,\nreports/validation/",
        "5. Commit on a feature branch\n(individual commits — see README\n§Git Workflow)",
        "6. Open PR into main",
        "7. CI runs automatically:\npytest + full pipeline smoke test\n(.github/workflows/ci.yml)",
        "8. Review + squash-merge",
        "9. Write findings into\nAssessment 2 report",
    ]

    y = 14.0
    boxes = []
    for i, step in enumerate(steps):
        b = _box(ax, (0.5, y - 1.0), 5.0, 1.0, step, COLORS["consumer"] if i % 2 else COLORS["clean"], 8)
        boxes.append(b)
        y -= 1.5

    for i in range(len(boxes) - 1):
        _arrow(ax, boxes[i], boxes[i + 1])

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    arch_dir = REPO_ROOT / "docs" / "architecture"
    workflow_dir = REPO_ROOT / "docs" / "workflow"
    arch_dir.mkdir(parents=True, exist_ok=True)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    # v3: scoped to "Transport Emissions" (was "Road Transport Emissions"),
    # 7 sources (was 9) after descoping the OData API and NSW traffic
    # sources -- see CHANGELOG.md. v2 kept in docs/ as historical record,
    # not deleted -- see README's diagram-versioning convention.
    draw_architecture_diagram(arch_dir / "architecture_v3.png")
    draw_workflow_diagram(workflow_dir / "workflow_v3.png")