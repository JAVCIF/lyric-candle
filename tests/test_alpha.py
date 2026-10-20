"""Run: python -m unittest discover -s tests -v (headless via QT_QPA_PLATFORM)."""
import copy
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('LYRIC_CANDLE_LANG', 'es')  # Tests compare Spanish texts.
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from lyric_candle.model import (Project,Cue,Span,Style,Keyframe,load,save,to_dict,from_dict,
    parse_time,time_text,add_span,split_spans,propose_spans,retime_cue,snap_spans_to_audio,
    animation_progress,animation_clock,animation_to_elapsed,keyframe_points,retime_keyframes)
from lyric_candle.render import Renderer,visibility
from lyric_candle.media import ROOT,ExportWorker,WaveWorker,executable,probe
from lyric_candle.app import MainWindow
from lyric_candle.dialogs import ImportDialog
from lyric_candle.lyrics_import import parse_alternating, parse_columns, uniform_cues
APP=QApplication.instance() or QApplication([])
APP.setApplicationName('LyricCandleTests')

def wait_job(job,seconds=35):
    deadline=time.monotonic()+seconds
    while job.isRunning() and time.monotonic()<deadline:
        APP.processEvents()
        job.wait(10)
    APP.processEvents()
    if job.isRunning():
        job.cancel();job.wait(5000)
        raise AssertionError('Media job timed out')

class ModelTests(unittest.TestCase):
    def test_time_roundtrip_and_reject_invalid(self):
        for n in [0,.001,59.999,60,3671.12]:
            self.assertAlmostEqual(parse_time(time_text(n)),n,places=3)
        self.assertEqual(parse_time('1:02,500'),62.5)
        for v in ['nan','inf','-1','oops']:
            with self.assertRaises(ValueError):parse_time(v)
    def test_syllable_split_preserves_visible_text(self):
        c=Cue(original='El día brillará',end=4)
        split_spans(c,'original','El dí|a bri|lla|rá')
        self.assertEqual(c.original,'El día brillará')
        self.assertEqual(''.join(c.original[s.begin:s.end] for s in c.original_spans),c.original)
        with self.assertRaises(ValueError):split_spans(c,'original','El día | brillará')
    def test_overlap_and_independent_tracks(self):
        c=Cue(original='brillar',translation='shine')
        add_span(c,'original',0,3)
        with self.assertRaises(ValueError):add_span(c,'original',2,5)
        add_span(c,'translation',0,5)
        self.assertEqual(len(c.translation_spans),1)
    def test_estimates_inside_paint_interval(self):
        c=Cue(original='Luz del día',start=8,end=12,paint_start=.4,paint_end=3.4)
        split_spans(c,'original','Luz| del |dí|a')
        for s in c.original_spans:
            self.assertGreaterEqual(s.start,.4)
            self.assertLessEqual(s.finish,3.4)
        self.assertEqual(Project(cues=[c],duration=12).problems(),[])
    def test_retiming_rescales_syllables(self):
        c=Cue(original='sí',start=2,end=6,paint_start=1,paint_end=3,original_spans=[Span(0,2,1,2)])
        c.end=4
        retime_cue(c,4)
        self.assertEqual((c.original_spans[0].start,c.original_spans[0].finish,c.paint_end),(.5,1,1.5))
    def test_unicode_atomic_save_relative_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);media=base/'música con espacios.wav';media.write_bytes(b'not-used')
            c=Cue(original='El corazón 💛',translation='The heart',original_spans=[Span(3,10,.2,.8,color='#ab12ef',lift=20,scale=1.5)])
            p=Project(media=str(media),cues=[c]);path=base/'proyecto.lyric.json'
            save(p,path)
            self.assertEqual(json.loads(path.read_text())['media'],media.name)
            self.assertEqual(to_dict(p),to_dict(load(path)))
            self.assertEqual(list(base.glob('*.tmp')),[])
    def test_draft_can_be_reopened_and_flagged(self):
        p=Project(duration=1,cues=[Cue(end=3,original='draft')])
        restored=from_dict(to_dict(p))
        self.assertTrue(restored.problems())
        self.assertEqual(restored.cues[0].end,3)
    def test_audio_attack_snap_and_silence(self):
        c=Cue(original='Luz',end=1,original_spans=[Span(0,3,.35,.65)])
        peaks=[0]*100
        self.assertEqual(snap_spans_to_audio(c,'original',peaks,1),0)
        peaks[40]=1
        self.assertEqual(snap_spans_to_audio(c,'original',peaks,1),1)
        self.assertAlmostEqual(c.original_spans[0].start,.4)
        self.assertAlmostEqual(c.original_spans[0].finish,.7)

class RenderTests(unittest.TestCase):
    def test_alignment_with_different_lengths_sizes(self):
        r=Renderer();c=Cue(original='Una frase mucho más larga',translation='Short');p=Project(cues=[c])
        for pos in ['left_split','right_split','center']:
            p.style.position=pos
            lines,positions=r.cue_geometry(p,c)
            widths=[g[0] for _,_,g in lines]
            offsets=[0,0] if pos.startswith('left') else widths if pos.startswith('right') else [v/2 for v in widths]
            self.assertAlmostEqual(positions[0][0]+offsets[0],positions[1][0]+offsets[1])
    def test_modes_render_differently_and_keep_anchors(self):
        c=Cue(start=0,end=3,original='Luz del día',translation='Light',original_spans=[Span(0,3,.5,1.5)])
        p=Project(duration=3,cues=[c]);r=Renderer();anchors=r.cue_geometry(p,c)[1];frames=[]
        for mode in ['repaint','fade','advanced']:
            p.style.mode=mode;img=r.frame(p,1)
            self.assertFalse(img.isNull());frames.append(bytes(img.constBits()))
            self.assertEqual(r.cue_geometry(p,c)[1],anchors)
        self.assertEqual(len(set(frames)),3)
    def test_crossfade_and_repaint_visibility(self):
        c=Cue(start=1,end=3);s=Style(mode='fade',crossfade=True,fade_out=.4)
        self.assertAlmostEqual(visibility(c,3.2,s),.5)
        s.crossfade=False;self.assertEqual(visibility(c,3.2,s),0)
        s.mode='repaint';self.assertEqual(visibility(c,2.99,s),1);self.assertEqual(visibility(c,3,s),0)
    def test_overflow_without_wrapping(self):
        c=Cue(original='Largo '*100);p=Project(cues=[c])
        self.assertTrue(Renderer().overflow(p,c));self.assertNotIn('\n',c.original)
    def test_repaint_preserves_outline_pixels(self):
        c=Cue(original='Luz',end=3)
        p=Project(duration=3,cues=[c])
        p.style.layout='one';p.style.mode='repaint';p.style.position='center'
        p.style.fill='#ff0000';p.style.painted='#00ff00';p.style.outline='#0000ff'
        p.style.outline_width=5
        r=Renderer()
        before=bytes(r.frame(p,0).constBits());after=bytes(r.frame(p,2.99).constBits())
        blue=bytes([0,0,255,255])
        self.assertEqual([i for i in range(0,len(before),4) if before[i:i+4]==blue],
                         [i for i in range(0,len(after),4) if after[i:i+4]==blue])

class ImportTests(unittest.TestCase):
    def test_blank_separated_pairs_preserve_symbols_and_spaces(self):
        text='\ufeff  Original ♪☆  \r\nTraducción… 「sí」\r\n\r\n\r\nOtro\r\nOtra\r\n'
        self.assertEqual(parse_alternating(text),[('  Original ♪☆  ','Traducción… 「sí」'),('Otro','Otra')])
    def test_continuous_pairs_without_separators(self):
        self.assertEqual(parse_alternating('Uno\nOne\nDos\nTwo'),[('Uno','One'),('Dos','Two')])
    def test_incomplete_block_is_rejected_without_shifting_pairs(self):
        with self.assertRaisesRegex(ValueError,'Bloque 1.*renglón 1'):
            parse_alternating('Falta traducción\n\nSiguiente\nNext')
        with self.assertRaisesRegex(ValueError,'renglón 3'):
            parse_alternating('Uno\nOne\nHuérfano')
    def test_long_block_between_separators_requires_review(self):
        with self.assertRaisesRegex(ValueError,'Bloque 2'):
            parse_alternating('Uno\nOne\n\nDos\nTwo\nTres\nThree')
    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):parse_alternating('\n \n\t')
    def test_public_demo_matches_prepared_project(self):
        text=(ROOT/'examples'/'Demo.txt').read_text(encoding='utf-8-sig')
        pairs=parse_alternating(text)
        self.assertEqual(len(pairs),3)
        project=load(ROOT/'examples'/'Demo.lyric.json')
        self.assertEqual([(c.original,c.translation) for c in project.cues],pairs)
        self.assertEqual(project.problems(),[])

class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=MainWindow(demo=False,recover=False);cls.w.show();APP.processEvents()
    @classmethod
    def tearDownClass(cls):
        cls.w.dirty=False;cls.w.close();APP.processEvents()
    def setUp(self):
        w=self.w;w.pause()
        w.link_selection.setChecked(False)
        w.project=Project(cues=[Cue(start=0,end=3,original='Vuelve a brillar',translation='Shine again'),
                              Cue(start=3,end=6,original='Otra frase',translation='Another line')])
        w.path=None;w.history.clear();w.future.clear();w.mark_index=0;w.last_marked=-1;w.dirty=False
        w.refresh_all();w.table.selectRow(0);w.seek(0);APP.processEvents()
    def test_all_layouts_modes(self):
        w=self.w
        for layout in ['one','two']:
            w.set_style('layout',layout)
            for idx in range(w.position_combo.count()):
                w.position_combo.setCurrentIndex(idx)
                for mode in ['repaint','fade','advanced']:
                    w.set_style('mode',mode);w.seek(1)
                    self.assertFalse(w.preview.grab().isNull())
        self.assertEqual(w.project.problems(),[])
    def test_marking_progress_and_stop(self):
        w=self.w;w.seek(.5);w.mark_next();w.seek(2.5);w.mark_next()
        self.assertEqual(w.project.cues[0].end,2.5);self.assertEqual(w.project.cues[1].start,2.5)
        w.seek(5);w.mark_end();before=to_dict(w.project);w.mark_next()
        self.assertEqual(before,to_dict(w.project));self.assertEqual(w.project.cues[-1].end,5)
    def test_selection_and_individual_style(self):
        w=self.w;w.track.setCurrentIndex(0);w.refresh_spans();begin=w.span_text.toPlainText().index('bri')
        cursor=w.span_text.textCursor();cursor.setPosition(begin);cursor.setPosition(begin+3,QTextCursor.MoveMode.KeepAnchor)
        w.span_text.setTextCursor(cursor);w.mark_selection();self.assertEqual(w.span_table.rowCount(),1)
        w.span_table.item(0,4).setText('#ff0000');w.span_table.item(0,5).setText('30');w.span_table.item(0,6).setText('1.5')
        s=w.project.cues[0].original_spans[0];self.assertEqual((s.color,s.lift,s.scale),('#ff0000',30,1.5))
    def test_undo_redo_keeps_marks(self):
        w=self.w;w.split_edit.setText('Vuelve a bri|llar');w.apply_split()
        self.assertEqual(len(w.project.cues[0].original_spans),2)
        w.undo();self.assertEqual(len(w.project.cues[0].original_spans),0)
        w.redo();self.assertEqual(len(w.project.cues[0].original_spans),2)
    def test_short_duration_draft_undo(self):
        w=self.w;w.change_duration(1);w.set_style('size',55);w.undo()
        self.assertEqual(w.project.duration,1);self.assertTrue(w.project.problems())
    def test_unicode_selection_offsets(self):
        w=self.w;w.project.cues[0].original='💛 sílaba';w.track.setCurrentIndex(0);w.refresh_all()
        cursor=w.span_text.textCursor();cursor.setPosition(3);cursor.setPosition(5,QTextCursor.MoveMode.KeepAnchor)
        w.span_text.setTextCursor(cursor);w.mark_selection();s=w.project.cues[0].original_spans[0]
        self.assertEqual(w.project.cues[0].original[s.begin:s.end],'sí')
    def test_expanded_editor_returns_to_main_window(self):
        w=self.w
        panel=w.tabs.widget(1)
        QTimer.singleShot(80,lambda:APP.activeModalWidget().accept())
        w.expand_span_editor()
        self.assertIs(w.tabs.widget(1),panel)
        self.assertEqual(w.tabs.count(),5)
    def test_import_keeps_empty_first_translation(self):
        d=ImportDialog(6,self.w)
        d.input_tabs.setCurrentIndex(1)
        d.original.setPlainText('Primera\nSegunda')
        d.translation.setPlainText('\nSecond')
        d.make_cues()
        self.assertEqual([c.translation for c in d.cues],['','Second'])
    def test_alternating_import_preview_and_cues(self):
        d=ImportDialog(8,self.w)
        d.combined.setPlainText('Primera ♪\nFirst\n\nSegunda\nSecond')
        self.assertEqual(d.preview.rowCount(),2)
        self.assertEqual(d.preview.item(0,0).text(),'Primera ♪')
        self.assertEqual(d.preview.item(1,1).text(),'Second')
        d.make_cues()
        self.assertEqual([(c.start,c.end) for c in d.cues],[(0,4),(4,8)])
    def test_alternating_invalid_preview_blocks_import(self):
        from PySide6.QtWidgets import QDialogButtonBox
        d=ImportDialog(8,self.w)
        d.combined.setPlainText('Solo una línea\n\nSegunda\nSecond')
        self.assertEqual(d.preview.rowCount(),0)
        self.assertFalse(d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        self.assertIn('Bloque 1',d.summary.text())

@unittest.skipUnless(executable('ffmpeg') and executable('ffprobe'),'FFmpeg not installed')
class ExportTests(unittest.TestCase):
    def make_project(self):
        c=Cue(start=.05,end=.8,original='Luz',translation='Light',original_spans=[Span(0,3,.1,.5)])
        p=Project(duration=1,media=str(ROOT/'examples'/'Demo.wav'),cues=[c])
        p.style.width,p.style.height,p.style.size,p.style.secondary_size,p.style.margin=320,240,26,20,20
        p.style.fps=24;return p
    def export(self,p,path):
        job=ExportWorker(p,path);result=[];errors=[]
        job.done.connect(result.append);job.failed.connect(errors.append);job.start();wait_job(job)
        self.assertEqual(errors,[]);self.assertEqual(result,[str(path)]);return path
    def test_mp4_frames_duration_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'resultado con espacios.mp4';self.export(self.make_project(),path);m=probe(str(path))
            self.assertEqual({s['codec_type'] for s in m['streams']},{'audio','video'})
            v=next(s for s in m['streams'] if s['codec_type']=='video')
            self.assertEqual((v['width'],v['height'],int(v['nb_frames'])),(320,240,24))
            self.assertAlmostEqual(float(m['format']['duration']),1,delta=.1)
    def test_video_background_with_silent_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'fondo.mp4'
            subprocess.run([executable('ffmpeg'),'-y','-v','error','-f','lavfi','-i','color=c=blue:s=320x240:r=24:d=1',
                           '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(source)],check=True)
            p=self.make_project();p.media=str(source);p.style.background='video';out=self.export(p,tmp/'export.mp4')
            self.assertTrue(any(s['codec_type']=='video' for s in probe(str(out))['streams']))
            raw=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(out),'-frames:v','1','-f','rawvideo',
                                '-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
            self.assertGreater(raw[(120*320+160)*3+2],150)
    def test_failure_preserves_old_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'keep.mp4';path.write_bytes(b'previous version');p=self.make_project();p.media=str(Path(tmp)/'missing.wav')
            errors=[];job=ExportWorker(p,path);job.failed.connect(errors.append);job.start();wait_job(job)
            self.assertTrue(errors);self.assertEqual(path.read_bytes(),b'previous version')
    def test_cancel_preserves_old_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'keep.mp4';path.write_bytes(b'previous version');p=self.make_project();p.duration=30
            job=ExportWorker(p,path);job.start();job.cancel();wait_job(job)
            self.assertEqual(path.read_bytes(),b'previous version');self.assertEqual(list(Path(tmp).glob('lyric-candle-*.mp4')),[])
    def test_waveform_duration(self):
        ready=[];errors=[];job=WaveWorker(str(ROOT/'examples'/'Demo.wav'))
        job.ready.connect(lambda peaks,duration:ready.append((peaks,duration)));job.failed.connect(errors.append);job.start();wait_job(job)
        self.assertEqual(errors,[]);self.assertAlmostEqual(ready[0][1],12,places=2);self.assertTrue(ready[0][0])

if __name__=='__main__':unittest.main()
