"""Regression coverage for linked navigation and piecewise animation timing."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from lyric_candle.app import MainWindow
from lyric_candle.model import (Project,Cue,Span,Keyframe,load,save,to_dict,from_dict,
    animation_progress,animation_clock,animation_to_elapsed,retime_cue,retime_keyframes)
from lyric_candle.render import Renderer,visibility
from lyric_candle.media import ExportWorker,executable
APP=QApplication.instance() or QApplication([])


def held_cue():
    return Cue(end=4,original='Luz del día',translation='Daylight',
               keyframes=[Keyframe(1,.4),Keyframe(3,.4)])


class CurveModelTests(unittest.TestCase):
    def test_hold_and_catch_up(self):
        c=held_cue()
        for t in (1,1.5,2,2.9,3):
            self.assertAlmostEqual(animation_progress(c,t),.4)
        self.assertAlmostEqual(animation_progress(c,3.5),.7)
        self.assertAlmostEqual(animation_clock(c,2.5),1.6)
        self.assertEqual(animation_progress(c,4),1)
        self.assertEqual(animation_progress(c,-1),0)
    def test_disabled_curve_restores_legacy_clock(self):
        c=held_cue();c.use_keyframes=False
        self.assertAlmostEqual(animation_progress(c,2),.5)
        self.assertEqual(animation_clock(c,2),2)
        c.keyframes=[];c.use_keyframes=True
        self.assertEqual(animation_clock(c,3),3)
    def test_inverse_uses_first_reached_time_on_hold(self):
        c=held_cue()
        self.assertAlmostEqual(animation_to_elapsed(c,1.6),1)
        self.assertAlmostEqual(animation_to_elapsed(c,2.8),3.5)
        self.assertEqual(animation_to_elapsed(c,-.1),-.1)
    def test_save_reload_and_old_project_compatibility(self):
        p=Project(cues=[held_cue()]);p.cues[0].keyframe_scope='paint'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'curva.lyric.json';save(p,path);restored=load(path)
            self.assertEqual(to_dict(p),to_dict(restored))
        data=to_dict(p)
        self.assertEqual(data['schema'],2)
        for key in ('keyframes','keyframe_scope','use_keyframes'):data['cues'][0].pop(key)
        data['schema']=1
        old=from_dict(data)
        self.assertEqual(old.cues[0].keyframes,[])
        self.assertAlmostEqual(animation_progress(old.cues[0],2),.5)
    def test_duration_and_paint_window_rescale_points(self):
        c=held_cue();c.end=8;retime_cue(c,4)
        self.assertEqual([p.time for p in c.keyframes],[2,6])
        c.paint_start,c.paint_end=1,7
        retime_keyframes(c,0,8)
        self.assertEqual([p.time for p in c.keyframes],[2.5,5.5])
        self.assertEqual(Project(cues=[c]).problems(),[])
    def test_invalid_curves_are_rejected(self):
        for points in ([Keyframe(1,.6),Keyframe(2,.4)], [Keyframe(1,.4),Keyframe(1,.6)],
                       [Keyframe(0,.4)], [Keyframe(4,.5)], [Keyframe(2,float('nan'))]):
            p=Project(cues=[Cue(end=4,keyframes=points)])
            self.assertTrue(any('keyframes' in issue for issue in p.problems()))
            with self.assertRaises(ValueError):from_dict(to_dict(p))


class CurveRenderTests(unittest.TestCase):
    def assert_frames_equal(self,p,a,b):
        r=Renderer();first=r.frame(p,a);second=r.frame(p,b)
        self.assertEqual(bytes(first.constBits()),bytes(second.constBits()))
    def test_repaint_holds_exactly(self):
        p=Project(cues=[held_cue()]);p.style.mode='repaint'
        self.assert_frames_equal(p,1.5,2.5)
    def test_emphasis_motion_and_color_can_hold(self):
        c=held_cue();c.original_spans=[Span(0,3,1,2.6)]
        p=Project(cues=[c]);p.style.fade=False
        self.assert_frames_equal(p,1.5,2.5)
    def test_scope_changes_only_selected_animations_and_fade_stays_real(self):
        c=held_cue();c.original_spans=[Span(0,3,1,2.6)]
        p=Project(cues=[c]);p.style.fade=False;r=Renderer()
        c.keyframe_scope='all';all_image=r.frame(p,2.4)
        c.keyframe_scope='paint';paint_image=r.frame(p,2.4)
        c.keyframe_scope='emphasis';emphasis_image=r.frame(p,2.4)
        self.assertNotEqual(bytes(all_image.constBits()),bytes(paint_image.constBits()))
        self.assertNotEqual(bytes(all_image.constBits()),bytes(emphasis_image.constBits()))
        p.style.mode='fade';p.style.fade_in=1
        self.assertAlmostEqual(visibility(c,.5,p.style),.5)


class LinkedEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=MainWindow(demo=False,recover=False)
        cls.prior=cls.w.link_selection.isChecked()
        cls.w.show();APP.processEvents()
    @classmethod
    def tearDownClass(cls):
        cls.w.link_selection.setChecked(cls.prior)
        cls.w.dirty=False;cls.w.close();APP.processEvents()
    def setUp(self):
        w=self.w;w.pause();w.link_selection.setChecked(False);w.loop.setChecked(False)
        w.project=Project(duration=6,cues=[Cue(start=0,end=3,original='Primera',translation='First'),
                                        Cue(start=3,end=6,original='Segunda',translation='Second')])
        w.history.clear();w.future.clear();w.mark_index=0;w.last_marked=-1;w.dirty=False
        w.refresh_all();w.table.selectRow(0);w.seek(0);APP.processEvents()
    def test_navigation_off_then_bidirectional_on(self):
        w=self.w;w.seek(1.25);w.table.selectRow(1)
        self.assertEqual(w.position,1.25)
        w.seek(.5);self.assertEqual(w.selected_index(),1)
        w.link_selection.setChecked(True)
        self.assertEqual(w.selected_index(),0)
        w.table.selectRow(1);self.assertEqual(w.position,3)
        w.seek(.75);self.assertEqual(w.selected_index(),0);self.assertEqual(w.position,.75)
    def test_playback_follow_does_not_seek_or_reset_mark_sequence(self):
        w=self.w;w.link_selection.setChecked(True);w.mark_index=1;w.last_marked=0
        w.set_position(4.25)
        self.assertEqual(w.selected_index(),1);self.assertEqual(w.position,4.25)
        self.assertEqual((w.mark_index,w.last_marked),(1,0))
    def test_waveform_and_slider_navigation_keep_precise_time(self):
        w=self.w;w.link_selection.setChecked(True)
        w.waveform.seek.emit(4.125)
        self.assertEqual(w.selected_index(),1);self.assertEqual(w.position,4.125)
        w.seek_slider.setValue(1350)
        self.assertEqual(w.selected_index(),0);self.assertEqual(w.position,1.35)
    def test_click_current_row_restarts_it(self):
        w=self.w;w.link_selection.setChecked(True);w.seek(1.5)
        w.table.cellClicked.emit(0,3)
        self.assertEqual(w.position,0)
    def test_mark_next_does_not_seek_when_auto_selecting_next_row(self):
        w=self.w;w.link_selection.setChecked(True);w.seek(.5);w.mark_next()
        self.assertEqual(w.position,.5);self.assertEqual(w.mark_index,1)
        w.set_position(2);w.mark_next()
        self.assertEqual(w.position,2);self.assertEqual(w.project.cues[1].start,2)
    def test_add_hold_edit_and_undo(self):
        w=self.w;w.seek(1);w.keyframe_at_head()
        self.assertAlmostEqual(w.project.cues[0].keyframes[0].progress,1/3,places=5)
        w.seek(2);w.keyframe_at_head(hold=True)
        self.assertAlmostEqual(animation_progress(w.project.cues[0],1.5),1/3,places=5)
        w.keyframe_table.item(1,1).setText('25')
        self.assertAlmostEqual(w.project.cues[0].keyframes[0].progress,.25)
        w.undo();self.assertAlmostEqual(w.project.cues[0].keyframes[0].progress,1/3,places=5)
        w.redo();self.assertAlmostEqual(w.project.cues[0].keyframes[0].progress,.25)
    def test_points_follow_duration_and_paint_window_changes(self):
        w=self.w;w.keyframe_add(1,.4);w.keyframe_add(2,.4)
        w.cue_time('end',6)
        self.assertEqual([p.time for p in w.project.cues[0].keyframes],[2,4])
        w.cue_time('paint_start',1)
        self.assertAlmostEqual(w.project.cues[0].keyframes[0].time,1+5/3)
        self.assertFalse(any('keyframes' in e for e in w.project.problems()))
    def test_graph_double_click_adds_and_drag_moves_point(self):
        w=self.w;w.tabs.setCurrentIndex(4);APP.processEvents()
        curve=w.keyframe_curve
        pos=curve.point_xy(1,.3).toPoint();QTest.mouseDClick(curve,Qt.MouseButton.LeftButton,pos=pos);APP.processEvents()
        self.assertEqual(len(w.project.cues[0].keyframes),1)
        point=w.project.cues[0].keyframes[0];start=curve.point_xy(point.time,point.progress).toPoint()
        finish=curve.point_xy(1.7,.5).toPoint()
        QTest.mousePress(curve,Qt.MouseButton.LeftButton,pos=start)
        QTest.mouseMove(curve,finish);QTest.mouseRelease(curve,Qt.MouseButton.LeftButton,pos=finish);APP.processEvents()
        self.assertAlmostEqual(w.project.cues[0].keyframes[0].time,1.7,delta=.025)
        self.assertAlmostEqual(w.project.cues[0].keyframes[0].progress,.5,delta=.025)
    def test_manual_seek_can_leave_loop_and_gaps_do_not_jump(self):
        w=self.w;w.link_selection.setChecked(True);w.loop.setChecked(True);w.play();w.seek(4)
        self.assertEqual(w.selected_index(),1);self.assertEqual(w.position,4)
        w.pause();w.loop.setChecked(False);w.project.cues[1].start=4.5;w.seek(3.5)
        self.assertEqual(w.position,3.5);self.assertEqual(w.selected_index(),1)
    def test_automatic_follow_does_not_discard_unapplied_text(self):
        w=self.w;w.link_selection.setChecked(True)
        w.original_edit.setPlainText('Texto aún sin aplicar')
        w.set_position(4)
        self.assertEqual(w.selected_index(),0)
        self.assertEqual(w.original_edit.toPlainText(),'Texto aún sin aplicar')
        w.apply_text();w.set_position(4)
        self.assertEqual(w.selected_index(),1)


@unittest.skipUnless(executable('ffmpeg') and executable('ffprobe'),'FFmpeg not installed')
class CurveExportTests(unittest.TestCase):
    def test_exported_frames_hold_and_catch_up(self):
        c=held_cue();p=Project(duration=4,cues=[c]);p.style.mode='repaint'
        p.style.width,p.style.height,p.style.size,p.style.secondary_size,p.style.margin=320,240,26,20,20;p.style.fps=24
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'hold.mp4';errors=[];done=[];job=ExportWorker(p,target)
            job.failed.connect(errors.append);job.done.connect(done.append);job.start()
            limit=time.monotonic()+35
            while job.isRunning() and time.monotonic()<limit:APP.processEvents();job.wait(10)
            if job.isRunning():job.cancel();job.wait(5000);self.fail('Export timed out')
            APP.processEvents();self.assertEqual(errors,[]);self.assertTrue(done)
            decoded=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(target),'-vf',
                r'select=eq(n\,12)+eq(n\,36)+eq(n\,60)','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
                capture_output=True,check=True)
            self.assertEqual(decoded.returncode,0,decoded.stderr.decode('utf-8','replace'))
            data=decoded.stdout
            size=320*240*3;self.assertEqual(len(data),size*3)
            before,held_a,held_b=[data[i*size:(i+1)*size] for i in range(3)]
            self.assertLess(sum(abs(a-b) for a,b in zip(held_a,held_b))/size,1.5)
            self.assertGreater(sum(a!=b for a,b in zip(before,held_a)),300)


if __name__=='__main__':unittest.main()
