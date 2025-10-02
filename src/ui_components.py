from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout,
    QTextEdit, QProgressBar, QComboBox, QSlider, QColorDialog
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRegularExpression
)
from PyQt6.QtGui import (
    QColor, QRegularExpressionValidator, QPainter, QLinearGradient, QFont, QPalette
)


class CompactColorPicker(QWidget):
    color_selected = pyqtSignal(str)

    def __init__(self, accent="#6EB6FF"):
        super().__init__()
        self._accent = accent
        self._recent: list[str] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(8, 8, 8, 8)

        recent_row = QHBoxLayout()
        recent_row.setSpacing(6)
        recent_row.addWidget(self._make_section_label("Recent"))
        self.recent_wrap = QHBoxLayout()
        self.recent_wrap.setSpacing(6)
        recent_row.addLayout(self.recent_wrap)
        recent_row.addStretch()
        root.addLayout(recent_row)

        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.preview = QLabel()
        self.preview.setObjectName("colorPreview")
        self.preview.setFixedSize(28, 18)
        self.preview.setStyleSheet("background:#FFFFFF; border-radius:4px;")

        self.hex_edit = QLineEdit()
        self.hex_edit.setObjectName("hexField")
        self.hex_edit.setPlaceholderText("#RRGGBB")
        self.hex_edit.setFixedWidth(110)
        rx = QRegularExpression("^#?[0-9A-Fa-f]{6}$")
        self.hex_edit.setValidator(QRegularExpressionValidator(rx))
        self.hex_edit.returnPressed.connect(self._apply_hex_from_field)

        self.pick_btn = QPushButton("Pick…")
        self.pick_btn.setObjectName("pickButton")
        self.pick_btn.clicked.connect(self._choose_custom_color)

        bar.addWidget(self._make_section_label("Color"))
        bar.addWidget(self.preview)
        bar.addWidget(self.hex_edit)
        bar.addWidget(self.pick_btn)
        bar.addStretch()
        root.addLayout(bar)

        self._select_color("#FFFFFF")

    def _make_section_label(self, text):
        lab = QLabel(text)
        lab.setObjectName("miniSection")
        return lab

    def _choose_custom_color(self):
        from PyQt6.QtWidgets import QColorDialog
        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        cur = self.hex_edit.text() or "#FFFFFF"
        dlg.setCurrentColor(QColor(cur if cur.startswith("#") else f"#{cur}"))
        if dlg.exec():
            self._select_color(dlg.currentColor().name().upper())

    def _apply_hex_from_field(self):
        txt = self.hex_edit.text().strip()
        if not txt:
            return
        if not txt.startswith("#"):
            txt = "#" + txt
        self._select_color(txt.upper())

    def _select_color(self, hexc: str):
        if not hexc.startswith("#"):
            hexc = "#" + hexc
        hexc = hexc.upper()

        self.preview.setStyleSheet(f"background:{hexc}; border-radius:4px;")
        self.hex_edit.setText(hexc)

        if hexc in self._recent:
            self._recent.remove(hexc)
        self._recent.insert(0, hexc)
        self._recent = self._recent[:6]
        self._rebuild_recent()

        self.color_selected.emit(hexc[1:])

    def _rebuild_recent(self):
        while self.recent_wrap.count():
            item = self.recent_wrap.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        for hexc in self._recent:
            b = QPushButton()
            b.setObjectName("swatch")
            b.setFixedSize(32, 22)
            b.setToolTip(hexc)
            b.setStyleSheet(f"background:{hexc};")
            b.clicked.connect(lambda checked=False, c=hexc: self._select_color(c))
            self.recent_wrap.addWidget(b)

class ColorPicker(QWidget):    
    color_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        preset_label = QLabel("Preset Colors:")
        layout.addWidget(preset_label)
                
        self.custom_btn = QPushButton("Choose Custom Color...")
        self.custom_btn.clicked.connect(self.open_color_dialog)
        layout.addWidget(self.custom_btn)
        
    def open_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()[1:]
            self.color_selected.emit(hex_color)


class EffectSelector(QWidget):
    effect_changed = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        effect_layout = QHBoxLayout()
        effect_label = QLabel("Effect:")
        self.effect_combo = QComboBox()
        self.effect_combo.addItems([
            "Single Static", "Single Breathing", "Single Color Cycle",
            "Multi Static", "Multi Breathing", "Rainbow"
        ])
        self.effect_combo.currentTextChanged.connect(self.on_effect_changed)
        
        effect_layout.addWidget(effect_label)
        effect_layout.addWidget(self.effect_combo)
        layout.addLayout(effect_layout)
        
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Speed:")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(3)
        self.speed_slider.setValue(2)
        self.speed_slider.valueChanged.connect(self.on_effect_changed)
        
        self.speed_value = QLabel("2")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_value.setText(str(v))
        )
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        layout.addLayout(speed_layout)
        
    def on_effect_changed(self):
        effect = self.effect_combo.currentText()
        params = {
            'speed': self.speed_slider.value()
        }
        self.effect_changed.emit(effect, params)


class StatusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.clear_message)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.progress_bar)
        
    def show_message(self, message: str, timeout: int = 3000):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #4CAF50;")
        self.message_timer.start(timeout)
        
    def show_error(self, message: str, timeout: int = 5000):
        self.status_label.setText(f"Error: {message}")
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: #F44336;")
        self.message_timer.start(timeout)
        
    def show_warning(self, message: str, timeout: int = 4000):
        self.status_label.setText(f"Warning: {message}")
        self.status_label.setStyleSheet("color: #FF9800;")
        self.message_timer.start(timeout)
        
    def show_progress(self, show: bool = True):
        self.progress_bar.setVisible(show)
        
    def set_progress(self, value: int):
        self.progress_bar.setValue(value)
        
    def clear_message(self):
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("")
        self.message_timer.stop()


class AnimatedButton(QPushButton):
    
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setup_animation()
        
    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        super().leaveEvent(event)


class ColorWheel(QWidget):    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 200)
        self.selected_color = QColor(255, 255, 255)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 10
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, Qt.GlobalColor.red)
        gradient.setColorAt(0.17, Qt.GlobalColor.yellow)
        gradient.setColorAt(0.33, Qt.GlobalColor.green)
        gradient.setColorAt(0.5, Qt.GlobalColor.cyan)
        gradient.setColorAt(0.67, Qt.GlobalColor.blue)
        gradient.setColorAt(0.83, Qt.GlobalColor.magenta)
        gradient.setColorAt(1, Qt.GlobalColor.red)
        
        painter.setBrush(gradient)
        painter.drawEllipse(center.x() - radius, center.y() - radius, 
                          radius * 2, radius * 2)
                          
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            center = self.rect().center()
            dx = event.position().x() - center.x()
            dy = event.position().y() - center.y()
            
            import math
            angle = math.atan2(dy, dx)
            hue = int((angle + math.pi) / (2 * math.pi) * 360)
            
            self.selected_color = QColor.fromHsv(hue, 255, 255)
            self.color_changed.emit(self.selected_color)
            self.update()


class LogViewer(QWidget):
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setObjectName("logViewer")
        
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.clicked.connect(self.clear_logs)
        
        self.export_btn = QPushButton("Export Logs") 
        self.export_btn.clicked.connect(self.export_logs)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        layout.addWidget(QLabel("Application Logs:"))
        layout.addWidget(self.log_text)
        layout.addLayout(button_layout)
        
    def add_log(self, message: str, level: str = "INFO"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        self.log_text.append(formatted_message)
        
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_logs(self):
        self.log_text.clear()
        
    def export_logs(self):
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        
        filename = f"rog_aura_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", filename, "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.log_text.toPlainText())
                self.add_log(f"Logs exported to {file_path}")
            except Exception as e:
                self.add_log(f"Failed to export logs: {str(e)}", "ERROR")