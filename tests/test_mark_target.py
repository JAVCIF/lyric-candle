"""0.2.6: Ctrl+M always changes the phrase the user can see, and provisional times never steer it."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')
from dataclasses import asdict
import json
import tempfile
import unittest
from pathlib import Path
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from lyric_candle import i18n
from lyric_candle.app import MainWindow
from lyric_candle.lyrics_import import uniform_cues
from lyric_candle.model import Project, Cue, save, load, to_dict, from_dict

APP = QApplication.instance() or QApplication([])


class MarkTargetTests(unittest.TestCase):
    def setUp(self):
        self.w = MainWindow(demo=False, recover=False)
        self.w.link_selection.setChecked(False)
        self.w.show(); APP.processEvents()

    def tearDown(self):
        self.w.dirty = False; self.w.close(); APP.processEvents()

    def load(self, cues, duration=40):
        w = self.w
        w.project = Project(duration=duration, cues=cues)
        w.mark_index, w.last_marked = 0, -1
        w.reset_text_editors(); w.refresh_all(); w.table.selectRow(0); APP.processEvents()
        w.history.clear(); w.future.clear(); w.dirty = False

    def timed(self, n=3):
        return [Cue(start=i*4, end=i*4+4, original=f'F{i}') for i in range(n)]

    def provisional(self, n=5):
        return uniform_cues([(f'F{i}', f'L{i}') for i in range(n)], 20)  # 4 s each, unmarked.

    def snapshots(self):
        return [asdict(cue) for cue in self.w.project.cues]

    # --- the reported failure, without zoom -------------------------------------------
    def test_ctrl_m_marks_the_row_selected_by_following(self):
        w = self.w; self.load(self.timed())
        w.link_selection.setChecked(True); w.set_position(9.0)
        self.assertEqual(w.selected_index(), 2)
        before = self.snapshots(); w.mark_next()
        self.assertEqual(w.project.cues[2].start, 9.0)
        self.assertEqual(self.snapshots()[:2], before[:2])  # Rows 1 and 2 untouched.

    def test_sequence_still_advances_while_following(self):
        w = self.w; self.load(self.timed())
        w.link_selection.setChecked(True); w.seek(.5); w.mark_next()
        w.set_position(2.0)  # Inside phrase 1 while the sequence waits for phrase 2.
        self.assertEqual(w.mark_index, 1); self.assertEqual(w.selected_index(), 1)
        w.set_position(4.2); w.mark_next()
        self.assertEqual((w.project.cues[0].end, w.project.cues[1].start), (4.2, 4.2))

    # --- first pass: provisional times must not steer selection or Ctrl+M ------------------
    def test_first_pass_with_link_ignores_provisional_times(self):
        w = self.w; self.load(self.provisional())
        w.link_selection.setChecked(True)
        for t in (2, 6, 10, 13.5):  # Long intro: playback crosses the placeholder ranges.
            w.set_position(t)
            self.assertEqual((w.selected_index(), w.mark_index), (0, 0))
        w.mark_next()
        cue = w.project.cues[0]
        self.assertEqual(cue.start, 13.5); self.assertTrue(cue.timed)
        self.assertFalse(any(c.timed for c in w.project.cues[1:]))
        self.assertEqual(w.selected_index(), 1)

    def test_clicking_a_provisional_row_does_not_jump_the_playhead(self):
        w = self.w; cues = self.provisional(); cues[0].timed = True; self.load(cues)
        w.link_selection.setChecked(True); w.seek(1.0)
        w.table.selectRow(3); APP.processEvents()
        self.assertEqual(w.position, 1.0); self.assertEqual(w.mark_index, 3)
        w.table.selectRow(0); APP.processEvents()
        self.assertEqual(w.position, 0)  # Confirmed phrase: linked selection seeks as before.

    # --- the provisional flag ------------------------------------------------------------
    def test_import_and_new_phrase_are_provisional_and_edits_confirm(self):
        w = self.w; self.load(self.provisional())
        w.seek(30); w.add_cue(); self.assertFalse(w.selected_cue().timed)
        edits = [lambda: w.cue_time('start', 1.0),
                 lambda: w.move_edge('end', 6.5),
                 lambda: w.table.item(w.selected_index(), 2).setText('11.5')]
        for row, edit in zip((0, 1, 2), edits):
            with self.subTest(row=row):
                w.table.selectRow(row); APP.processEvents()
                self.assertFalse(w.project.cues[row].timed)
                edit(); self.assertTrue(w.project.cues[row].timed)
        w.table.selectRow(3); w.seek(13); w.mark_end()
        self.assertTrue(w.project.cues[3].timed)

    def test_flag_is_saved_and_old_projects_count_as_timed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'p.lyric.json'); project = Project(duration=20, cues=self.provisional())
            project.cues[0].timed = True; save(project, path)
            self.assertEqual([c.timed for c in load(path).cues], [True, False, False, False, False])
            data = json.loads(path.read_text(encoding='utf-8'))
            for cue in data['cues']:
                cue.pop('timed')  # Files from 0.2.5 and earlier.
            self.assertTrue(all(c.timed for c in from_dict(data).cues))

    def test_provisional_rows_are_dimmed_in_the_table(self):
        w = self.w; cues = self.provisional(); cues[0].timed = True; self.load(cues)
        self.assertFalse(w.table.item(0, 1).font().italic())
        self.assertTrue(w.table.item(1, 1).font().italic())
        self.assertIn('provisional', w.table.item(1, 1).toolTip())

    # --- visible target ----------------------------------------------------------------
    def test_arrow_shows_what_ctrl_m_will_change(self):
        w = self.w; self.load(self.timed())
        w.tick(); self.assertEqual(w.table.item(0, 0).text(), '▶ 1')
        w.seek(.5); w.mark_next(); w.tick()
        self.assertEqual((w.table.item(0, 0).text(), w.table.item(1, 0).text()), ('1', '▶ 2'))
        w.table.selectRow(2); w.zoom.setChecked(True); w.tick()
        self.assertEqual(w.table.item(2, 0).text(), '▶ 3')
        w.zoom.setChecked(False); w.seek(9); w.mark_next(); w.tick()  # Last phrase started.
        self.assertFalse(any(w.table.item(r, 0).text().startswith('▶') for r in range(3)))

    def test_every_mark_reports_the_phrase_it_changed(self):
        w = self.w; self.load(self.timed())
        w.seek(.5); w.mark_next()
        self.assertEqual(w.statusBar().currentMessage(), 'Frase 1: inicio en 00:00.500.')
        w.seek(3.2); w.mark_end()
        self.assertEqual(w.statusBar().currentMessage(), 'Frase 1: final en 00:03.200.')
        i18n.set_language('en')
        try:
            w.table.selectRow(1); w.zoom.setChecked(True); w.seek(4.4); w.mark_next()
            self.assertEqual(w.statusBar().currentMessage(), 'Line 2: start at 00:04.400.')
        finally:
            i18n.set_language('es')

    # --- review findings: one source of truth for the target ------------------------------
    def test_playback_keeps_a_manually_chosen_provisional_row(self):
        w = self.w; cues = self.provisional(); cues[0].timed = True; self.load(cues)
        w.link_selection.setChecked(True); w.set_position(1.0)  # Phrase 1 (confirmed) is playing.
        w.table.selectRow(3); APP.processEvents()
        for t in (1.5, 2.0, 3.5):
            w.set_position(t); w.tick()
            self.assertEqual(w.selected_index(), 3)
            self.assertEqual(w.mark_target(), 3)
        before = self.snapshots(); w.mark_next()
        self.assertEqual(w.project.cues[3].start, 3.5)
        self.assertEqual(self.snapshots()[0], before[0])

    def test_opening_another_project_never_targets_a_hidden_row(self):
        w = self.w; self.load(self.timed())
        w.table.selectRow(2); APP.processEvents()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'otro.lyric.json'); save(Project(duration=40, cues=self.timed()), path)
            w.load_project_path(path); APP.processEvents()
        row = w.selected_index(); w.tick()
        self.assertEqual(w.mark_target(), row)
        self.assertEqual(w.table.item(row, 0).text(), f'▶ {row+1}')
        before = self.snapshots(); w.seek(9.5); w.mark_next()
        changed = [i for i, (a, b) in enumerate(zip(before, self.snapshots())) if a != b]
        self.assertEqual(changed, [row])

    def test_zoom_mark_on_the_same_time_confirms_a_provisional_phrase(self):
        w = self.w; self.load(self.provisional()); w.zoom.setChecked(True)
        w.seek(0); w.mark_next()
        self.assertTrue(w.project.cues[0].timed); self.assertEqual(w.project.cues[0].start, 0)
        self.assertEqual(len(w.history), 1)
        w.seek(4); w.mark_end()  # Same end as the placeholder: also a confirmation.
        self.assertEqual(len(w.history), 1)  # Already confirmed and unchanged: nothing to record.

    # --- audit: undo, deleted rows and key repeat during a sequence -------------------------
    def names(self, index):
        return None if index is None or index < 0 else self.w.project.cues[index].original

    def test_undo_and_redo_of_a_mark_restore_the_sequence(self):
        w = self.w; self.load(self.timed(5))
        w.seek(1); w.mark_next(); w.seek(5); w.mark_next()  # F0 1-5, F1 starts at 5; next is F2.
        w.undo(); w.tick()
        self.assertEqual((self.names(w.mark_target()), self.names(w.selected_index())), ('F1', 'F1'))
        self.assertEqual(w.table.item(1, 0).text(), '▶ 2')
        w.redo(); self.assertEqual(self.names(w.mark_target()), 'F2')
        w.undo(); w.seek(6); w.mark_next()  # Re-mark F1: it closes F0 and starts F1, F2 untouched.
        cues = w.project.cues
        self.assertEqual(((cues[0].start, cues[0].end), cues[1].start, cues[2].start), ((1, 6), 6, 8))

    def test_deleting_rows_mid_sequence_keeps_the_same_phrases(self):
        w = self.w; self.load(self.timed(5))
        w.seek(1); w.mark_next(); w.seek(5); w.mark_next()  # last F1, next F2.
        w.loading = True; w.table.selectRow(0); w.loading = False  # Select F0 without restarting.
        w.delete_cue()
        self.assertEqual((self.names(w.last_marked), self.names(w.mark_target())), ('F1', 'F2'))
        w.loading = True; w.table.selectRow(1); w.loading = False  # Now delete the target, F2.
        w.delete_cue()
        self.assertEqual((self.names(w.last_marked), self.names(w.mark_target())), ('F1', 'F3'))
        w.loading = True; w.table.selectRow(0); w.loading = False  # Delete F1, the open phrase.
        w.delete_cue()
        self.assertEqual(w.last_marked, -1)  # Sequence ended: the target is the row on screen.
        self.assertEqual(w.mark_target(), w.selected_index())

    def test_holding_the_mark_keys_does_not_repeat(self):
        actions = {a.shortcut().toString(): a for a in self.w.findChildren(type(self.w.menuBar().actions()[0]))}
        self.assertFalse(actions['Ctrl+M'].autoRepeat()); self.assertFalse(actions['Ctrl+F'].autoRepeat())

    def test_repeated_final_marks_keep_sequence_closed_until_a_row_is_selected(self):
        w = self.w; self.load(self.timed(2))
        w.seek(.5); w.mark_next(); w.seek(4.5); w.mark_next(); w.seek(7); w.mark_end()
        self.assertIsNone(w.mark_target())
        for end in (7, 7.25, 7.5):
            w.seek(end); w.mark_end()
            self.assertIsNone(w.mark_target())
            before = to_dict(w.project); w.mark_next()
            self.assertEqual(to_dict(w.project), before)
        w.table.selectRow(0)
        self.assertEqual(w.mark_target(), 0)

    def test_delete_visible_next_row_then_undo_redo_keeps_sequence_identity(self):
        w = self.w; self.load(self.timed(4)); uids = [c.uid for c in w.project.cues]
        identity = lambda index: w.project.cues[index].uid
        w.seek(.5); w.mark_next()
        self.assertEqual(w.selected_index(), 1)
        w.delete_cue()
        self.assertEqual((identity(w.last_marked), identity(w.mark_target())), (uids[0], uids[2]))
        w.undo()
        self.assertEqual((identity(w.last_marked), identity(w.mark_target())), (uids[0], uids[1]))
        w.redo()
        self.assertEqual((identity(w.last_marked), identity(w.mark_target())), (uids[0], uids[2]))
        w.seek(4.5); w.mark_next()
        self.assertEqual((w.project.cues[0].end, w.project.cues[1].start), (4.5, 4.5))

    def test_undo_restores_a_provisional_row_pinned_by_hand(self):
        w = self.w; cues = self.provisional(); cues[0].timed = True; self.load(cues)
        w.link_selection.setChecked(True); w.seek(1); w.table.selectRow(3)
        uid = w.selected_cue().uid
        w.set_style('size', w.project.style.size+1)
        w.table.selectRow(0); w.undo(); w.set_position(1.5)
        self.assertEqual((w.selected_cue().uid, w._pinned_uid), (uid, uid))
        w.mark_next()
        self.assertEqual((w.project.cues[3].start, w.project.cues[0].start), (1.5, 0))

    def test_running_preview_clock_marks_only_the_zoomed_selected_phrase(self):
        w = self.w; self.load(self.timed()); w.table.selectRow(1); w.zoom.setChecked(True)
        w.link_selection.setChecked(True); w.seek(4.4); w.play(); QTest.qWait(80)
        w.mark_next(); w.pause()
        self.assertEqual(w.selected_index(), 1)
        self.assertGreater(w.project.cues[1].start, 4.4)
        self.assertEqual((w.project.cues[0].start, w.project.cues[0].end,
                          w.project.cues[1].end, w.project.cues[2].start), (0, 4, 8, 8))

    def test_confirmation_only_zoom_mark_supports_undo_redo(self):
        w = self.w; self.load(self.provisional()); w.zoom.setChecked(True)
        w.seek(0); w.mark_next(); self.assertTrue(w.project.cues[0].timed)
        w.undo(); self.assertFalse(w.project.cues[0].timed)
        w.redo(); self.assertTrue(w.project.cues[0].timed)

    # --- undo in zoom --------------------------------------------------------------------
    def test_each_zoom_mark_is_its_own_undo_step(self):
        w = self.w; self.load(self.timed()); w.table.selectRow(1); w.zoom.setChecked(True)
        w.history.clear()
        w.seek(4.3); w.mark_next(); w.seek(4.6); w.mark_next()  # Within one second.
        self.assertEqual(len(w.history), 2)
        w.undo(); self.assertEqual(w.project.cues[1].start, 4.3)
        w.undo(); self.assertEqual(w.project.cues[1].start, 4)

    def test_finished_sequence_ignores_an_extra_ctrl_m(self):
        w = self.w; self.load(self.timed(2))
        w.seek(.5); w.mark_next(); w.seek(4.5); w.mark_next(); w.seek(7); w.mark_end()
        before = to_dict(w.project); w.mark_next()
        self.assertEqual(to_dict(w.project), before)


if __name__ == '__main__':
    unittest.main()
