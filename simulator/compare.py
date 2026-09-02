"""
A/B comparison of two configurations.

============================================================================
YOU BUILD THIS.  Search for "TODO(" to find your tasks.
============================================================================

"Is this better?" is the question a simulator exists to answer, and answering it
means holding two configurations at once and showing what differs.

The design point: comparison is not two apps side by side. It is one app that
knows two configs, computes both, and highlights the DELTA.
"""
from __future__ import annotations

__all__ = ["diff_configs", "compare", "ComparisonResult"]


def diff_configs(a, b) -> dict[str, tuple]:
    """
    Which fields differ, as {field: (value_a, value_b)}.

    TODO(W10-3a): Implement. Ignore `label` — two configs named differently but
    otherwise identical are the same experiment.

    Use this to drive a "what changed" caption above the comparison figure. When
    a user changes six things at once and the result gets worse, that caption is
    the difference between insight and confusion.
    """
    raise NotImplementedError("TODO(W10-3a) in simulator/compare.py")


def compare(config_a, config_b, preview: bool = False):
    """
    Run both configs and return a ComparisonResult holding both plus the deltas.

    TODO(W10-3b): Implement.
      - engine.run on each (the cache means re-comparing is instant)
      - metric deltas: b - a for each field of PSFMetrics
      - be careful with nan: if either PSLR is nan the delta is meaningless, so
        report "n/a" rather than nan propagating silently into a table

      DECIDE AND DOCUMENT which direction counts as "better" for each metric.
      Resolution: lower is better. PSLR: lower (more negative) is better. Coherent
      gain: HIGHER is better. Getting that table right is what stops the app
      cheerfully reporting an improvement when things got worse.
    """
    raise NotImplementedError("TODO(W10-3b) in simulator/compare.py")


class ComparisonResult:
    """
    Holds two Results and the differences between them.

    TODO(W10-3c): Design and implement this yourself — it is deliberately left
    open. It needs to carry both Results, the config diff, and the metric deltas,
    and expose whatever the GUI needs to render a comparison table.

    Think about what the table should show: the two values, the delta, and which
    way is better. Three columns is not enough; five is probably right.
    """
    pass
