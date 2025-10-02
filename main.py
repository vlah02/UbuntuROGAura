#!/usr/bin/env python3

import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider, QComboBox,
    QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QFrame, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon

from src.native_backend import RogAuraBackendNative
from src.ui_components import StatusBar, CompactColorPicker


class ROGAuraGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('ROGAura', 'GUI')
        self.backend = RogAuraBackendNative()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("ROG Aura Core Control")
        self.setGeometry(100, 100, 1000, 900)
        self.setMinimumSize(800, 600)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        try:
            self.setWindowIcon(QIcon('assets/rog_icon.png'))
        except:
            pass
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        
        self.create_title_section(main_layout)

        self.create_brightness_section(main_layout)
        
        self.create_tabbed_effects_section(main_layout)
        
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)
        
        self.apply_theme()
        
    def create_title_section(self, parent_layout):
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_layout = QVBoxLayout(title_frame)
        
        title_label = QLabel("ROG Aura Core Control")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle_label = QLabel("Control your ASUS ROG laptop keyboard lighting")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        parent_layout.addWidget(title_frame)
        
    def create_brightness_section(self, parent_layout):
        brightness_group = QGroupBox("Brightness Control")
        brightness_group.setObjectName("groupBox")
        brightness_layout = QVBoxLayout(brightness_group)
        
        slider_layout = QHBoxLayout()
        brightness_label = QLabel("Brightness:")
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(3)
        self.brightness_slider.setValue(2)
        self.brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness_slider.setTickInterval(1)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        
        self.brightness_value = QLabel("2")
        self.brightness_value.setObjectName("valueLabel")
        
        slider_layout.addWidget(brightness_label)
        slider_layout.addWidget(self.brightness_slider)
        slider_layout.addWidget(self.brightness_value)
        
        brightness_layout.addLayout(slider_layout)
        parent_layout.addWidget(brightness_group)
        

        
    def create_tabbed_effects_section(self, parent_layout):
        effects_group = QGroupBox("Lighting Effects")
        effects_group.setObjectName("groupBox")
        effects_layout = QVBoxLayout(effects_group)
        
        self.tabs = QTabWidget()
        
        single_tab = QWidget()
        self.create_single_zone_tab(single_tab)
        self.tabs.addTab(single_tab, "Single Zone")
        
        multi_tab = QWidget()
        self.create_multi_zone_tab(multi_tab)
        self.tabs.addTab(multi_tab, "Multi Zone")
        
        effects_layout.addWidget(self.tabs)
        
        control_layout = QHBoxLayout()
        
        speed_label = QLabel("Speed:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1 (Slow)", "2 (Medium)", "3 (Fast)"])
        self.speed_combo.setCurrentIndex(1)
        
        self.init_btn = QPushButton("Initialize Keyboard")
        self.init_btn.setObjectName("initButton")
        self.init_btn.clicked.connect(self.initialize_keyboard)
        
        control_layout.addWidget(speed_label)
        control_layout.addWidget(self.speed_combo)
        control_layout.addStretch()
        control_layout.addWidget(self.init_btn)
        
        effects_layout.addLayout(control_layout)
        parent_layout.addWidget(effects_group)
        
    def create_single_zone_tab(self, tab_widget):
        layout = QVBoxLayout(tab_widget)

        single_group = QGroupBox("Single Zone")
        single_group.setObjectName("groupBox")
        single_layout = QVBoxLayout(single_group)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.compact_picker = CompactColorPicker()
        self.compact_picker.color_selected.connect(self._on_color_selected)
        row.addWidget(self.compact_picker, 2)  
        actions = QVBoxLayout()
        actions.setSpacing(10)

        act_label = QLabel("Actions")
        act_label.setObjectName("miniSection")
        actions.addWidget(act_label)

        self.single_static_btn = QPushButton("Static Color")
        self.single_breathing_btn = QPushButton("Breathing")

        self.single_static_btn.setMinimumHeight(36)
        self.single_breathing_btn.setMinimumHeight(36)

        actions.addWidget(self.single_static_btn)
        actions.addWidget(self.single_breathing_btn)
        actions.addStretch()

        row.addLayout(actions, 1)

        single_layout.addLayout(row)

        layout.addWidget(single_group)
        layout.addStretch()

        self.single_static_btn.clicked.connect(
            lambda: self.apply_single_effect_with_selected_color("single_static")
        )
        self.single_breathing_btn.clicked.connect(self.apply_single_breathing_with_selected_color)

    def _on_color_selected(self, hex_without_hash: str):
        self.current_selected_color = hex_without_hash.lower()
        self.current_selected_color_name = f"#{hex_without_hash.upper()}"

        success = self.backend.apply_custom_color(hex_without_hash)
        if success:
            self.status_bar.show_message(f"Selected color: #{hex_without_hash.upper()}")
        else:
            self.status_bar.show_error(f"Failed to apply color: #{hex_without_hash.upper()}")

    def create_multi_zone_tab(self, tab_widget):
        layout = QVBoxLayout(tab_widget)
        
        multi_effects_group = QGroupBox("Multi Zone Effects")
        multi_effects_group.setObjectName("groupBox")
        multi_effects_layout = QVBoxLayout(multi_effects_group)
        
        effects_layout = QGridLayout()
        
        self.multi_breathing_btn = QPushButton("Multi Breathing")
        self.color_cycle_btn = QPushButton("Color Cycle")
        self.rainbow_btn = QPushButton("Rainbow")
        self.rainbow_cycle_btn = QPushButton("Rainbow Cycle")
        
        effects_layout.addWidget(self.multi_breathing_btn, 0, 0)
        effects_layout.addWidget(self.color_cycle_btn, 0, 1)
        effects_layout.addWidget(self.rainbow_btn, 1, 0)
        effects_layout.addWidget(self.rainbow_cycle_btn, 1, 1)
        
        multi_effects_layout.addLayout(effects_layout)
        layout.addWidget(multi_effects_group)
        
        layout.addStretch()
        
        self.multi_breathing_btn.clicked.connect(lambda: self.apply_multi_effect("multi_breathing"))
        self.color_cycle_btn.clicked.connect(lambda: self.apply_effect_with_speed("single_colorcycle"))
        self.rainbow_btn.clicked.connect(lambda: self.backend.apply_rainbow())
        self.rainbow_cycle_btn.clicked.connect(lambda: self.apply_effect_with_speed("rainbow_cycle"))
        
    def create_color_buttons(self, layout):
        colors = [
            ("Red", "#FF0000", "red"),
            ("Green", "#00FF00", "green"),
            ("Blue", "#0000FF", "blue"),
            ("Yellow", "#FFFF00", "yellow"),
            ("Gold", "#FFD700", "gold"),
            ("Cyan", "#00FFFF", "cyan"),
            ("Magenta", "#FF00FF", "magenta"),
            ("White", "#FFFFFF", "white"),
            ("Black", "#000000", "black")
        ]
        
        self.color_buttons = {}
        self.current_selected_color = "ffffff"
        self.current_selected_color_name = "White"
        
        row, col = 0, 0
        for name, hex_color, cmd in colors:
            btn = QPushButton(name)
            btn.setObjectName("colorButton")
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QPushButton#colorButton {{
                    background-color: {hex_color};
                    color: {"white" if name == "Black" else "black" if name in ["Yellow", "Gold", "White"] else "white"};
                    border: 2px solid #666;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton#colorButton:hover {{
                    border-color: #888;
                    background-color: {hex_color}DD;
                }}
                QPushButton#colorButton:pressed {{
                    background-color: {hex_color}CC;
                }}
            """)
            btn.clicked.connect(lambda checked, command=cmd, color_name=name, hex_val=hex_color[1:]: self.select_color(command, color_name, hex_val))
            
            layout.addWidget(btn, row, col)
            self.color_buttons[name] = btn
            
            col += 1
            if col > 4:
                col = 0
                row += 1
                
    def on_brightness_changed(self, value):
        self.brightness_value.setText(str(value))
        self.backend.set_brightness(value)
        self.status_bar.show_message(f"Brightness set to {value}")
        
    def select_color(self, command, color_name, hex_color):
        self.current_selected_color = hex_color
        self.current_selected_color_name = color_name
        self.selected_color_display.setText(color_name)
        
        success = self.backend.apply_color(command)
        if success:
            self.status_bar.show_message(f"Selected color: {color_name}")
        else:
            self.status_bar.show_error(f"Failed to apply color: {command}")
            
    def apply_single_effect_with_selected_color(self, effect_name):
        success = self.backend.apply_single_effect(effect_name, self.current_selected_color)
        if success:
            self.status_bar.show_message(f"Applied {effect_name} with {self.current_selected_color_name}")
        else:
            self.status_bar.show_error(f"Failed to apply {effect_name}")
            
    def apply_single_breathing_with_selected_color(self):
        speed = self.speed_combo.currentIndex() + 1
        success = self.backend.apply_speed_effect_with_colors("single_breathing", self.current_selected_color, "000000", speed)
        if success:
            self.status_bar.show_message(f"Applied breathing with {self.current_selected_color_name} (speed {speed})")
        else:
            self.status_bar.show_error("Failed to apply breathing effect")
            
    def apply_effect_with_speed(self, effect_name):
        speed = self.speed_combo.currentIndex() + 1
        success = self.backend.apply_speed_effect(effect_name, speed)
        if success:
            self.status_bar.show_message(f"Applied {effect_name} (speed {speed})")
        else:
            self.status_bar.show_error(f"Failed to apply {effect_name}")
            
    def apply_multi_effect(self, effect_name):
        speed = self.speed_combo.currentIndex() + 1 if "breathing" in effect_name else None
        success = self.backend.apply_multi_zone_effect(effect_name, speed)
        if success:
            self.status_bar.show_message(f"Applied {effect_name}")
        else:
            self.status_bar.show_error(f"Failed to apply {effect_name}")
        
    def open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()[1:]
            custom_name = f"Custom #{hex_color.upper()}"
            
            self.current_selected_color = hex_color
            self.current_selected_color_name = custom_name
            self.selected_color_display.setText(custom_name)
            
            self.color_picker_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {'black' if color.lightness() > 128 else 'white'};
                    border: 2px solid #666;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
            """)
            self.color_picker_btn.setText(f"Custom: {hex_color.upper()}")
            
            success = self.backend.apply_custom_color(hex_color)
            if success:
                self.status_bar.show_message(f"Selected custom color: #{hex_color}")
            else:
                self.status_bar.show_error("Failed to apply custom color")
                
    def initialize_keyboard(self):
        success = self.backend.initialize_keyboard()
        if success:
            self.status_bar.show_message("Keyboard initialized successfully")
        else:
            self.status_bar.show_error("Failed to initialize keyboard")
            
    def toggle_theme(self):
        current_theme = self.settings.value('theme', 'light')
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.settings.setValue('theme', new_theme)
        self.apply_theme()
        
    def apply_theme(self):
        self.load_dark_theme()
            
    def load_dark_theme(self):
        with open('styles/dark_theme.qss', 'r') as f:
            self.setStyleSheet(f.read())
            
    def load_light_theme(self):
        with open('styles/light_theme.qss', 'r') as f:
            self.setStyleSheet(f.read())
            
    def load_settings(self):
        brightness = self.settings.value('brightness', 2, type=int)
        self.brightness_slider.setValue(brightness)
        
    def save_settings(self):
        self.settings.setValue('brightness', self.brightness_slider.value())
        
    def closeEvent(self, event):
        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ROG Aura Core GUI")
    app.setOrganizationName("ROGAura")
    
    app.setStyle('Fusion')
    
    window = ROGAuraGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()