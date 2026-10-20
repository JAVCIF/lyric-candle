"""Undo/redo snapshots (project plus marking state)."""
from __future__ import annotations

import copy
import time

from ..model import from_dict, to_dict


class HistoryMixin:
    """Mixin for MainWindow: undo/redo snapshots (project plus marking state)."""

    def record(self, group=None):
        """Snapshot for undo. Consecutive changes of the same control within a second
        (held +/- buttons, repeated clicks) share one undo step."""
        if self.loading:
            return
        now = time.monotonic()
        if (group is not None and group == self._history_group and self.history
                and now - self._history_time < 1.0):
            self._history_time = now
            self.future.clear()
            self.dirty = True
            return
        self._history_group, self._history_time = group, now
        self.history.append(self.snapshot())
        self.history = self.history[-80:]
        self.future.clear()
        self.dirty = True

    def snapshot(self):
        """Undo entry: the project plus where marking stood (from_dict ignores the extra key)."""
        data = copy.deepcopy(to_dict(self.project))
        data['_marking'] = self.marking_state()
        return data

    def undo(self):
        if self.history:
            self._history_group = None
            self.future.append(self.snapshot())
            data = self.history.pop()
            self.project = from_dict(data, strict=False)
            self.dirty = True
            self.refresh_all()
            self.restore_marking(data.get('_marking'))
            self.set_media_source()

    def redo(self):
        if self.future:
            self._history_group = None
            self.history.append(self.snapshot())
            data = self.future.pop()
            self.project = from_dict(data, strict=False)
            self.dirty = True
            self.refresh_all()
            self.restore_marking(data.get('_marking'))
            self.set_media_source()
