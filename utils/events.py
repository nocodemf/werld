"""
Events — lightweight event collection for a simulation tick.

Not a full pub/sub bus — just a list that systems append to during a tick,
and the logger drains at the end.
"""

from __future__ import annotations

from typing import List


class TickEvents:
    """Collects event descriptions during a single simulation tick."""

    __slots__ = ("signals", "births", "deaths", "misc")

    def __init__(self) -> None:
        self.signals: List[str] = []
        self.births: List[str] = []
        self.deaths: List[str] = []
        self.misc: List[str] = []

    def clear(self) -> None:
        self.signals.clear()
        self.births.clear()
        self.deaths.clear()
        self.misc.clear()

    def all_events(self) -> List[str]:
        return self.signals + self.births + self.deaths + self.misc

