"""Font audition and paused saved-video restoration regressions."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'windows' if os.name == 'nt' else 'offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import copy
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QFont,QFontDatabase,QImage,QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer
from lyric_candle.app import MainWindow
from lyric_candle.model import Project,Cue,load,save,to_dict,from_dict
from lyric_candle.media import executable,StillFrameWorker
APP=QApplication.instance() or QApplication([])


def wait_for(condition,seconds=7):
    deadline=time.monotonic()+seconds
    while not condition() and time.monotonic()<deadline:
        APP.processEvents();QTest.qWait(10)
    APP.processEvents()
    if not condition():raise AssertionError('Timed out waiting for preview')


def is_blue(image):
    return image is not None and not image.isNull() and image.pixelColor(image.width()//2,image.height()//2).blue()>200


class FontAuditionTests(unittest.TestCase):
    def setUp(self):
        self.w=MainWindow(demo=False,recover=False);w=self.w
        w.link_selection.setChecked(False)
        w.project=Project(cues=[Cue(end=3,original='Fuente de prueba',translation='Font preview')])
        families=QFontDatabase.families()
        self.first=next((f for f in families if f=='DejaVu Sans'),families[0])
        self.second=next((f for f in families if f=='DejaVu Serif'),families[-1])
        w.project.style.font=self.first
        w.refresh_all();w.seek(1);w.show();w.tabs.setCurrentIndex(2)
        w.history.clear();w.future.clear();w.dirty=False;APP.processEvents()
    def tearDown(self):
        self.w.font_combo.hidePopup()
        self.w.dirty=False;self.w.close();APP.processEvents()
    def hover_second(self):
        combo=self.w.font_combo
        combo.showPopup();APP.processEvents()
        index=combo.model().index(combo.findText(self.second),0)
        combo.view().scrollTo(index);APP.processEvents()
        pos=combo.view().visualRect(index).center()
        QTest.mouseMove(combo.view().viewport(),QPoint(2,2));APP.processEvents()
        QTest.mouseMove(combo.view().viewport(),pos);APP.processEvents()
        return pos
    def test_mouse_hover_renders_temporarily_without_mutating_project(self):
        before=to_dict(self.w.project)
        self.hover_second()
        self.assertEqual(self.w.preview.font_override,self.second)
        self.assertEqual(self.w.preview.effective_project().style.font,self.second)
        self.assertEqual(to_dict(self.w.project),before)
        self.assertFalse(self.w.dirty);self.assertEqual(len(self.w.history),0)
    def test_escape_restores_font_without_undo_entry(self):
        self.hover_second()
        QTest.keyClick(self.w.font_combo.view(),Qt.Key.Key_Escape);APP.processEvents()
        self.assertEqual(self.w.preview.font_override,'')
        self.assertEqual(self.w.project.style.font,self.first)
        self.assertEqual(self.w.font_combo.currentFont().family(),self.first)
        self.assertEqual(self.w.history,[]);self.assertFalse(self.w.dirty)
    def test_click_commits_once_and_undo_restores(self):
        pos=self.hover_second()
        QTest.mouseClick(self.w.font_combo.view().viewport(),Qt.MouseButton.LeftButton,pos=pos);APP.processEvents()
        self.assertEqual(self.w.project.style.font,self.second)
        self.assertEqual(self.w.preview.font_override,'')
        self.assertEqual(len(self.w.history),1)
        self.w.undo();self.assertEqual(self.w.project.style.font,self.first)
    def test_search_completion_hover_is_temporary_and_cancelable(self):
        combo=self.w.font_combo
        combo.completer().highlighted[str].emit(self.second);APP.processEvents()
        self.assertEqual(self.w.preview.font_override,self.second)
        self.assertEqual(self.w.project.style.font,self.first)
        self.w.font_preview_end();APP.processEvents()
        self.assertEqual(self.w.preview.font_override,'')
        self.assertFalse(self.w.dirty)
    def test_saving_during_audition_preserves_committed_font(self):
        self.hover_second()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'font.lyric.json'
            self.assertTrue(self.w.write_project(path))
            self.assertEqual(load(path).style.font,self.first)
    def test_programmatic_font_refresh_does_not_commit_fallback(self):
        self.w.project.style.font='A-font-that-is-not-installed-123'
        self.w.refresh_panels();APP.processEvents()
        self.w.font_combo.lineEdit().editingFinished.emit();APP.processEvents()
        self.assertEqual(self.w.project.style.font,'A-font-that-is-not-installed-123')
        self.assertEqual(self.w.history,[])
    def test_typed_search_mouse_hover_and_escape(self):
        combo=self.w.font_combo
        edit=combo.lineEdit();edit.setFocus();edit.selectAll()
        prefix=self.second[:3]
        QTest.keyClicks(edit,prefix);APP.processEvents()
        combo.completer().setCompletionPrefix(prefix)
        combo.completer().complete();APP.processEvents()
        popup=combo.completer().popup()
        row=next(i for i in range(popup.model().rowCount()) if popup.model().index(i,0).data()==self.second)
        index=popup.model().index(row,0);popup.scrollTo(index);APP.processEvents()
        QTest.mouseMove(popup.viewport(),QPoint(2,2));APP.processEvents()
        QTest.mouseMove(popup.viewport(),popup.visualRect(index).center());APP.processEvents()
        self.assertEqual(self.w.preview.font_override,self.second)
        self.assertEqual(self.w.project.style.font,self.first)
        QTest.keyClick(popup,Qt.Key.Key_Escape);APP.processEvents()
        self.assertEqual(self.w.preview.font_override,'')
        self.assertEqual(self.w.project.style.font,self.first)


class SavedViewModelTests(unittest.TestCase):
    def test_saved_position_and_legacy_default(self):
        p=Project(duration=3,playhead=1.6)
        self.assertEqual(from_dict(to_dict(p)).playhead,1.6)
        data=to_dict(p);data.pop('playhead')
        self.assertEqual(from_dict(data).playhead,0)
    def test_invalid_position_and_shorter_duration(self):
        p=Project(duration=3,playhead=8)
        self.assertEqual(from_dict(to_dict(p)).playhead,3)
        for value in [-1,float('nan'),'bad']:
            data=to_dict(Project());data['playhead']=value
            with self.assertRaises(ValueError):from_dict(data)


@unittest.skipUnless(executable('ffmpeg'),'FFmpeg not installed')
class PausedVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name);cls.video=cls.root/'red then blue.mp4'
        subprocess.run([executable('ffmpeg'),'-y','-v','error','-f','lavfi','-i','color=red:s=320x240:r=25:d=1',
            '-f','lavfi','-i','color=blue:s=320x240:r=25:d=2','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0',
            '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(cls.video)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.w=MainWindow(demo=False,recover=False);self.w.link_selection.setChecked(False);self.w.show();APP.processEvents()
    def tearDown(self):
        self.w.dirty=False;self.w.close();APP.processEvents()
    def project(self,head=1.6):
        p=Project(duration=3,media=str(self.video),playhead=head,cues=[Cue(end=3,original='Prueba')])
        p.style.background='video';return p
    def open_project(self,head=1.6):
        path=self.root/'saved.lyric.json';save(self.project(head),path)
        self.w.load_project_path(path);return path
    def settle_blue(self):
        wait_for(lambda:is_blue(self.w.preview.video) and self.w._pending_player_seek is None and not self.w._warming_video)
        QTest.qWait(150);APP.processEvents()
    def test_reopen_stays_at_saved_position_and_shows_frame_without_play(self):
        self.open_project();self.settle_blue()
        self.assertAlmostEqual(self.w.position,1.6,delta=.04)
        self.assertFalse(self.w.is_playing());self.assertFalse(self.w.dirty)
        self.assertNotEqual(self.w.player.playbackState(),QMediaPlayer.PlaybackState.PlayingState)
        self.assertFalse(self.w.audio.isMuted())
    def test_save_stores_current_head_and_reopening_restores_it(self):
        path=self.open_project(.2)
        wait_for(lambda:self.w.preview.video is not None and self.w._pending_player_seek is None)
        self.w.seek(1.6);self.settle_blue();self.assertTrue(self.w.write_project(path))
        self.assertAlmostEqual(load(path).playhead,1.6,places=2)
        self.w.seek(.1);self.w.load_project_path(path);self.settle_blue()
        self.assertAlmostEqual(self.w.position,1.6,delta=.04)
    def test_rapid_paused_seeks_do_not_restore_stale_frame(self):
        self.open_project(.2);self.w.seek(.3);self.w.seek(1.8);self.settle_blue()
        self.assertAlmostEqual(self.w.position,1.8,delta=.04)
        self.assertTrue(is_blue(self.w.preview.video))
    def test_decoder_fallback_without_standalone_ffmpeg(self):
        with patch('lyric_candle.app.executable',return_value=None):
            self.open_project();self.settle_blue()
            self.assertAlmostEqual(self.w.position,1.6,delta=.06)
            self.assertFalse(self.w.is_playing());self.assertFalse(self.w.audio.isMuted())
    def test_still_extraction_at_eof_returns_last_frame(self):
        ready=[];errors=[];job=StillFrameWorker(str(self.video),3)
        job.ready.connect(ready.append);job.failed.connect(errors.append);job.start()
        deadline=time.monotonic()+8
        while job.isRunning() and time.monotonic()<deadline:APP.processEvents();job.wait(10)
        if job.isRunning():job.cancel();job.wait(4000);self.fail('Still extraction timed out')
        APP.processEvents();self.assertEqual(errors,[]);self.assertTrue(is_blue(ready[0]))
    def test_outdated_result_from_another_source_or_seek_is_ignored(self):
        self.open_project();self.settle_blue()
        wrong=QImage(8,8,QImage.Format.Format_RGB32);wrong.fill(QColor('red'))
        serial,gen=self.w._still_serial,self.w._source_generation
        self.w.still_frame_ready(wrong,serial-1,gen,1.6)
        self.w.still_frame_ready(wrong,serial,gen-1,1.6)
        self.w.still_frame_ready(wrong,serial,gen,.1)
        self.w.video_frame(object(),gen-1)
        self.assertTrue(is_blue(self.w.preview.video))
    def test_project_without_saved_head_opens_first_frame(self):
        self.open_project(0)
        wait_for(lambda:self.w.preview.video is not None and self.w._pending_player_seek is None)
        pixel=self.w.preview.video.pixelColor(160,120)
        self.assertGreater(pixel.red(),200);self.assertLess(pixel.blue(),50)
        self.assertAlmostEqual(self.w.position,0,delta=.04)


if __name__=='__main__':unittest.main()
