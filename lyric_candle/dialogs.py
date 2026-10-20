from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .lyrics_import import parse_alternating, parse_columns, uniform_cues


class ImportDialog(QDialog):
    def __init__(self, duration, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Importar letra · original y traducción'))
        self.resize(900, 740)
        self.duration = duration
        self.cues = []
        layout = QVBoxLayout(self)
        label = QLabel(tr('Carga tu letra y revisa las parejas antes de importar. '
                       'Los tiempos se repartirán de forma provisional; después márcalos escuchando el audio.'))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.input_tabs = QTabWidget()
        layout.addWidget(self.input_tabs, 2)
        combined_page = QWidget()
        combined_layout = QVBoxLayout(combined_page)
        button = QPushButton(tr('Abrir TXT con original y traducción juntos…'))
        self.combined = QPlainTextEdit()
        self.combined.setPlaceholderText(tr('Original de la primera frase\nTraducción de la primera frase\n\n'
                                         'Original de la segunda frase\nTraducción de la segunda frase'))
        button.clicked.connect(lambda checked=False: self.open_text(self.combined))
        combined_layout.addWidget(button)
        combined_layout.addWidget(self.combined, 1)
        hint = QLabel(tr('Formato: original → traducción → línea vacía. También acepta parejas continuas sin líneas vacías. '
                      'No modifica símbolos, puntuación ni espacios del texto.'))
        hint.setWordWrap(True)
        combined_layout.addWidget(hint)
        self.input_tabs.addTab(combined_page, tr('TXT alternado'))
        columns_page = QWidget()
        row = QHBoxLayout(columns_page)
        self.original = QPlainTextEdit()
        self.translation = QPlainTextEdit()
        self.original.setPlaceholderText(tr('Original: una frase por renglón'))
        self.translation.setPlaceholderText(tr('Traducción: una frase por renglón (opcional)'))
        for editor, caption in ((self.original, tr('Abrir TXT original')), (self.translation, tr('Abrir TXT traducción'))):
            column = QVBoxLayout()
            column.addWidget(editor)
            button = QPushButton(caption)
            button.clicked.connect(lambda checked=False, e=editor: self.open_text(e))
            column.addWidget(button)
            row.addLayout(column)
        self.input_tabs.addTab(columns_page, tr('Dos columnas'))
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.preview = QTableWidget(0, 2)
        self.preview.setHorizontalHeaderLabels([tr('Original'), tr('Traducción')])
        self.preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview.setAlternatingRowColors(True)
        self.preview.setMinimumHeight(155)
        layout.addWidget(self.preview, 1)
        self.replace = QCheckBox(tr('Reemplazar todas las frases actuales'))
        self.replace.setChecked(True)
        layout.addWidget(self.replace)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('Importar parejas'))
        self.buttons.accepted.connect(self.make_cues)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for editor in (self.combined, self.original, self.translation):
            editor.textChanged.connect(self.update_preview)
        self.input_tabs.currentChanged.connect(self.update_preview)
        self.update_preview()

    def open_text(self, editor):
        path, _ = QFileDialog.getOpenFileName(self, tr('Abrir letra UTF-8'), '', tr('Texto (*.txt);;Todos los archivos (*)'))
        if path:
            try:
                editor.setPlainText(Path(path).read_text(encoding='utf-8-sig'))
            except (OSError, UnicodeDecodeError) as exc:
                QMessageBox.warning(self, tr('No se pudo leer'), str(exc))

    def pairs(self):
        if self.input_tabs.currentIndex() == 0:
            return parse_alternating(self.combined.toPlainText())
        return parse_columns(self.original.toPlainText(), self.translation.toPlainText())

    def update_preview(self):
        try:
            pairs = self.pairs()
            uniform_cues(pairs, self.duration)  # Validate before enabling import.
        except ValueError as exc:
            self.summary.setText(str(exc))
            self.summary.setStyleSheet('color:#ffcb88;')
            self.preview.setRowCount(0)
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        self.summary.setText(tr('{0} pareja(s) listas · tiempos provisionales, sin sincronizar con la canción.').format(len(pairs)))
        self.summary.setStyleSheet('color:#9ed6fa;')
        self.preview.setRowCount(len(pairs))
        for row, pair in enumerate(pairs):
            for col, value in enumerate(pair):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.preview.setItem(row, col, item)
        self.preview.resizeRowsToContents()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def make_cues(self):
        try:
            self.cues = uniform_cues(self.pairs(), self.duration)
        except ValueError as exc:
            QMessageBox.warning(self, tr('Revisa la letra'), str(exc))
            return
        self.accept()
