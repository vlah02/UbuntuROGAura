import logging
from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from .native_rgb import RogAuraNative


class RogAuraBackendNative(QObject):    
    command_executed = pyqtSignal(str, bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setup_logging()
        self.aura = RogAuraNative()
        self.connected = False
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        if self.connected:
            return True
            
        try:
            self.connected = self.aura.connect()
            if self.connected:
                self.logger.info("Connected to ROG keyboard via USB")
                self.command_executed.emit("USB Connection", True)
            else:
                self.logger.error("Failed to connect to ROG keyboard")
                self.error_occurred.emit("Failed to connect to keyboard. Check USB connection and permissions.")
            return self.connected
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def disconnect(self):
        if self.connected:
            self.aura.disconnect()
            self.connected = False
            self.logger.info("Disconnected from keyboard")
    
    def _execute_with_connection(self, operation_name: str, operation_func) -> bool:
        temp_aura = RogAuraNative()
        
        try:
            if not temp_aura.connect():
                self.logger.error(f"Failed to connect for operation: {operation_name}")
                self.command_executed.emit(operation_name, False)
                return False
            
            success = operation_func(temp_aura)
            if success:
                self.logger.info(f"Successfully executed: {operation_name}")
                self.command_executed.emit(operation_name, True)
            else:
                self.logger.error(f"Failed to execute: {operation_name}")
                self.command_executed.emit(operation_name, False)
            return success
            
        except Exception as e:
            error_msg = f"Error executing {operation_name}: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        finally:
            temp_aura.disconnect()
    
    def set_brightness(self, brightness: int) -> bool:
        if not 0 <= brightness <= 3:
            self.logger.error(f"Invalid brightness value: {brightness}")
            return False
        
        return self._execute_with_connection(
            f"Set brightness to {brightness}",
            lambda aura: aura.set_brightness(brightness)
        )
    
    def apply_color(self, color: str) -> bool:
        valid_colors = [
            'red', 'green', 'blue', 'yellow', 'gold', 
            'cyan', 'magenta', 'white', 'black'
        ]
        
        if color.lower() not in valid_colors:
            self.logger.error(f"Invalid color: {color}")
            return False
        
        return self._execute_with_connection(
            f"Apply color: {color}",
            lambda aura: aura.apply_color(color.lower())
        )
    
    def apply_custom_color(self, hex_color: str) -> bool:
        try:
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            int(hex_color, 16)
            if len(hex_color) != 6:
                raise ValueError("Invalid hex color length")
        except ValueError:
            self.logger.error(f"Invalid hex color: {hex_color}")
            return False
        
        return self._execute_with_connection(
            f"Apply custom color: #{hex_color}",
            lambda aura: aura.apply_custom_color(hex_color)
        )
    
    def apply_single_effect(self, effect_name: str, hex_color: str = "ffffff") -> bool:
        if effect_name == "single_static":
            return self.apply_custom_color(hex_color)
        else:
            self.logger.error(f"Unknown single effect: {effect_name}")
            return False
    
    def apply_speed_effect(self, effect_name: str, speed: int = 2) -> bool:
        if not 1 <= speed <= 3:
            speed = 2
        
        if effect_name == "single_breathing":
            return self._execute_with_connection(
                f"Single breathing (speed {speed})",
                lambda aura: aura.single_breathing(speed=speed)
            )
        elif effect_name == "single_colorcycle":
            return self._execute_with_connection(
                f"Single color cycle (speed {speed})",
                lambda aura: aura.single_colorcycle(speed=speed)
            )
        elif effect_name == "rainbow_cycle":
            return self._execute_with_connection(
                f"Rainbow cycle (speed {speed})",
                lambda aura: aura.rainbow_cycle(speed=speed)
            )
        else:
            self.logger.error(f"Unknown speed effect: {effect_name}")
            return False
    
    def apply_multi_zone_effect(self, effect_name: str, speed: int = None) -> bool:
        if effect_name == "multi_static":
            return self._execute_with_connection(
                "Multi-zone static",
                lambda aura: aura.multi_static()
            )
        elif effect_name == "multi_breathing":
            if not speed or not 1 <= speed <= 3:
                speed = 2
            return self._execute_with_connection(
                f"Multi-zone breathing (speed {speed})",
                lambda aura: aura.multi_breathing(speed=speed)
            )
        else:
            self.logger.error(f"Unknown multi-zone effect: {effect_name}")
            return False
    
    def apply_rainbow(self) -> bool:
        return self._execute_with_connection(
            "Rainbow effect",
            lambda aura: aura.rainbow()
        )
    
    def initialize_keyboard(self) -> bool:
        return self._execute_with_connection(
            "Initialize keyboard",
            lambda aura: aura.initialize_keyboard()
        )
    
    def test_connection(self) -> bool:
        try:
            return self.connect()
        except Exception:
            return False


class NativeCommandThread(QThread):
    command_finished = pyqtSignal(bool, str)
    
    def __init__(self, backend: RogAuraBackendNative, operation_name: str, operation_func):
        super().__init__()
        self.backend = backend
        self.operation_name = operation_name
        self.operation_func = operation_func
        
    def run(self):
        try:
            success = self.operation_func()
            message = f"{'Success' if success else 'Failed'}: {self.operation_name}"
            self.command_finished.emit(success, message)
        except Exception as e:
            self.command_finished.emit(False, f"Error: {str(e)}")