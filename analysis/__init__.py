"""Analysis of recorded experiment output.

The scripts here read the structured logs the runner wrote under ``results/``
and turn them into summary statistics and (once a plotting library is available)
figures. They never fabricate data: they read only what a run recorded, and they
say plainly when there is nothing to summarise.
"""
