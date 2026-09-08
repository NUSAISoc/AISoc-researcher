"""Generate the report's conceptual (non-results) figures.

These figures are author-generated theory diagrams (for example a causal loop
diagram of the system under study). They are NOT experimental results. Label
every figure this module produces as author-generated and non-results in its
caption.

Results figures are produced separately, from real data in ``results/`` by the
scripts in ``analysis/``, and only after data exists. This module never reads or
invents experimental data.

Add one function per conceptual figure and call it from ``main``. Write outputs
to ``report/figures/``. The report build script hashes whatever exists there.
"""
from __future__ import annotations

from pathlib import Path

FIGURES_DIR = Path(__file__).resolve().parent / "figures"


def main() -> None:
    FIGURES_DIR.mkdir(exist_ok=True)
    # Example (uncomment and implement once matplotlib is available in your fork):
    #
    #   import matplotlib
    #   matplotlib.use("Agg")
    #   import matplotlib.pyplot as plt
    #   fig, ax = plt.subplots()
    #   ...  # draw the conceptual causal loop diagram
    #   fig.savefig(FIGURES_DIR / "system-cld.png", dpi=200, bbox_inches="tight")
    #
    # No conceptual figures are defined in the template. Add yours here.
    print(f"figures directory: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
