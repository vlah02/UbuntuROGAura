import usb.core
import usb.util
import array
import logging
from typing import Optional, List, Tuple
from enum import Enum


class Color:
    def __init__(self, red: int, green: int, blue: int):
        self.red = max(0, min(255, red))
        self.green = max(0, min(255, green))
        self.blue = max(0, min(255, blue))
    
    @classmethod
    def from_hex(cls, hex_color: str):
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        
        if len(hex_color) != 6:
            raise ValueError("Hex color must be 6 characters")
            
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return cls(r, g, b)
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.red, self.green, self.blue)


class Speed(Enum):
    SLOW = 1
    MEDIUM = 2
    FAST = 3
    
    @property
    def byte_value(self) -> int:
        return [0xe1, 0xeb, 0xf5][self.value - 1]


class RogAuraUSB:
    ASUS_VENDOR_ID = 0x0b05
    SUPPORTED_PRODUCT_IDS = [0x1854, 0x1869, 0x1866, 0x19b6]
    
    MESSAGE_LENGTH = 17
    
    MESSAGE_SET = array.array('B', [0x5d, 0xb5] + [0] * 15)
    MESSAGE_APPLY = array.array('B', [0x5d, 0xb4] + [0] * 15)
    MESSAGE_BRIGHTNESS = array.array('B', [0x5a, 0xba, 0xc5, 0xc4] + [0] * 13)
    MESSAGE_INITIALIZE = array.array('B', [0x5a, 0x41, 0x53, 0x55, 0x53, 0x20, 0x54, 0x65, 0x63, 0x68, 0x2e, 0x49, 0x6e, 0x63, 0x2e, 0x00, 0x00])
    
    COLORS = {
        'red': Color(255, 0, 0),
        'green': Color(0, 255, 0),
        'blue': Color(0, 0, 255),
        'yellow': Color(255, 255, 0),
        'gold': Color(255, 140, 0),
        'cyan': Color(0, 255, 255),
        'magenta': Color(255, 0, 255),
        'white': Color(255, 255, 255),
        'black': Color(0, 0, 0),
    }
    
    def __init__(self):
        self.device = None
        self.interface = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        try:
            self.device = None
            for product_id in self.SUPPORTED_PRODUCT_IDS:
                self.device = usb.core.find(idVendor=self.ASUS_VENDOR_ID, idProduct=product_id)
                if self.device:
                    self.logger.info(f"Found ROG keyboard: {hex(self.ASUS_VENDOR_ID)}:{hex(product_id)}")
                    break
            
            if not self.device:
                self.logger.error("No supported ROG keyboard found")
                return False
            
            try:
                cfg = self.device.get_active_configuration()
            except usb.core.USBError:
                self.device.set_configuration()
                cfg = self.device.get_active_configuration()
            
            self.interface = cfg[(0, 0)]
            
            self.kernel_driver_was_active = False
            if self.device.is_kernel_driver_active(self.interface.bInterfaceNumber):
                try:
                    self.device.detach_kernel_driver(self.interface.bInterfaceNumber)
                    self.kernel_driver_was_active = True
                    self.logger.info("Temporarily detached kernel driver")
                except usb.core.USBError as e:
                    self.logger.warning(f"Could not detach kernel driver: {e}")
            
            usb.util.claim_interface(self.device, self.interface)
            self.logger.info("Connected to ROG keyboard")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to keyboard: {e}")
            return False
    
    def disconnect(self):
        if self.device and self.interface:
            try:
                usb.util.release_interface(self.device, self.interface)
                if hasattr(self, 'kernel_driver_was_active') and self.kernel_driver_was_active:
                    try:
                        self.device.attach_kernel_driver(self.interface.bInterfaceNumber)
                        self.logger.info("Reattached kernel driver - keyboard should work normally")
                    except Exception as e:
                        self.logger.warning(f"Could not reattach kernel driver: {e}")
                else:
                    self.logger.info("Kernel driver was not originally active, not reattaching")
                usb.util.dispose_resources(self.device)
                self.logger.info("Disconnected from keyboard")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self.device = None
                self.interface = None
    
    def _create_message(self) -> array.array:
        msg = array.array('B', [0] * self.MESSAGE_LENGTH)
        msg[0] = 0x5d
        msg[1] = 0xb3
        return msg
    
    def _send_message(self, message: array.array) -> bool:
        try:
            if not self.device:
                return False
                
            result = self.device.ctrl_transfer(
                bmRequestType=0x21,
                bRequest=0x09,
                wValue=0x035d,
                wIndex=0,
                data_or_wLength=message,
                timeout=1000
            )
            return result == len(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def _send_messages(self, messages: List[array.array], set_and_apply: bool = True) -> bool:
        try:
            for msg in messages:
                if not self._send_message(msg):
                    return False
            
            if set_and_apply:
                if not self._send_message(self.MESSAGE_SET):
                    return False
                if not self._send_message(self.MESSAGE_APPLY):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send messages: {e}")
            return False
    
    def set_brightness(self, brightness: int) -> bool:
        if not 0 <= brightness <= 3:
            return False
            
        msg = array.array('B', self.MESSAGE_BRIGHTNESS)
        msg[4] = brightness
        return self._send_messages([msg], set_and_apply=False)
    
    def initialize_keyboard(self) -> bool:
        msg = array.array('B', self.MESSAGE_INITIALIZE)
        return self._send_messages([msg], set_and_apply=False)
    
    def single_static(self, color: Color) -> bool:
        msg = self._create_message()
        msg[4] = color.red
        msg[5] = color.green
        msg[6] = color.blue
        return self._send_messages([msg])
    
    def single_breathing(self, color1: Color, color2: Color, speed: Speed) -> bool:
        msg = self._create_message()
        msg[3] = 1
        msg[4] = color1.red
        msg[5] = color1.green
        msg[6] = color1.blue
        msg[7] = speed.byte_value
        msg[9] = 1
        msg[10] = color2.red
        msg[11] = color2.green
        msg[12] = color2.blue
        return self._send_messages([msg])
    
    def single_colorcycle(self, speed: Speed) -> bool:
        msg = self._create_message()
        msg[3] = 2
        msg[4] = 0xff
        msg[7] = speed.byte_value
        return self._send_messages([msg])
    
    def multi_static(self, colors: List[Color]) -> bool:
        if len(colors) > 4:
            colors = colors[:4]
        elif len(colors) < 4:
            colors.extend([Color(255, 255, 255)] * (4 - len(colors)))
        
        messages = []
        for i, color in enumerate(colors):
            msg = self._create_message()
            msg[2] = i + 1
            msg[4] = color.red
            msg[5] = color.green
            msg[6] = color.blue
            msg[7] = 0xeb
            messages.append(msg)
        
        return self._send_messages(messages)
    
    def multi_breathing(self, colors: List[Color], speed: Speed) -> bool:
        if len(colors) > 4:
            colors = colors[:4]
        elif len(colors) < 4:
            colors.extend([Color(255, 255, 255)] * (4 - len(colors)))
        
        messages = []
        for i, color in enumerate(colors):
            msg = self._create_message()
            msg[2] = i + 1
            msg[3] = 1
            msg[4] = color.red
            msg[5] = color.green
            msg[6] = color.blue
            msg[7] = speed.byte_value
            messages.append(msg)
        
        return self._send_messages(messages)
    
    def rainbow_cycle(self, speed: Speed) -> bool:
        msg = self._create_message()
        msg[3] = 3
        msg[4] = 0xff
        msg[7] = speed.byte_value
        return self._send_messages([msg])
    
    def rainbow(self) -> bool:
        colors = [
            Color(255, 0, 0),
            Color(255, 255, 0),
            Color(0, 255, 255),
            Color(255, 0, 255),
        ]
        return self.multi_static(colors)
    
    def apply_color(self, color_name: str) -> bool:
        if color_name not in self.COLORS:
            return False
        return self.single_static(self.COLORS[color_name])
    
    def apply_custom_color(self, hex_color: str) -> bool:
        try:
            color = Color.from_hex(hex_color)
            return self.single_static(color)
        except ValueError:
            return False


class RogAuraNative:
    
    def __init__(self):
        self.usb = RogAuraUSB()
        self.logger = logging.getLogger(__name__)
        self.connected = False
    
    def connect(self) -> bool:
        self.connected = self.usb.connect()
        return self.connected
    
    def disconnect(self):
        if self.connected:
            self.usb.disconnect()
            self.connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def set_brightness(self, brightness: int) -> bool:
        if not self.connected:
            return False
        return self.usb.set_brightness(brightness)
    
    def initialize_keyboard(self) -> bool:
        if not self.connected:
            return False
        return self.usb.initialize_keyboard()
    
    def apply_color(self, color_name: str) -> bool:
        if not self.connected:
            return False
        return self.usb.apply_color(color_name)
    
    def apply_custom_color(self, hex_color: str) -> bool:
        if not self.connected:
            return False
        return self.usb.apply_custom_color(hex_color)
    
    def single_breathing(self, color1_hex: str = "ffffff", color2_hex: str = "ff0000", speed: int = 2) -> bool:
        if not self.connected:
            return False
        try:
            color1 = Color.from_hex(color1_hex)
            color2 = Color.from_hex(color2_hex)
            speed_enum = Speed(speed)
            return self.usb.single_breathing(color1, color2, speed_enum)
        except (ValueError, KeyError):
            return False
    
    def single_colorcycle(self, speed: int = 2) -> bool:
        if not self.connected:
            return False
        try:
            speed_enum = Speed(speed)
            return self.usb.single_colorcycle(speed_enum)
        except ValueError:
            return False
    
    def multi_static(self, colors: List[str] = None) -> bool:
        if not self.connected:
            return False
        
        if colors is None:
            colors = ["ff0000", "00ff00", "0000ff", "ffff00"]
        
        try:
            color_objects = [Color.from_hex(c) for c in colors]
            return self.usb.multi_static(color_objects)
        except ValueError:
            return False
    
    def multi_breathing(self, colors: List[str] = None, speed: int = 2) -> bool:
        if not self.connected:
            return False
        
        if colors is None:
            colors = ["ff0000", "00ff00", "0000ff", "ffff00"]
        
        try:
            color_objects = [Color.from_hex(c) for c in colors]
            speed_enum = Speed(speed)
            return self.usb.multi_breathing(color_objects, speed_enum)
        except ValueError:
            return False
    
    def rainbow(self) -> bool:
        if not self.connected:
            return False
        return self.usb.rainbow()
    
    def rainbow_cycle(self, speed: int = 2) -> bool:
        if not self.connected:
            return False
        try:
            speed_enum = Speed(speed)
            return self.usb.rainbow_cycle(speed_enum)
        except ValueError:
            return False
    
    def single_static(self, color_hex: str) -> bool:
        if not self.connected:
            return False
        try:
            color = Color.from_hex(color_hex)
            return self.usb.single_static(color)
        except ValueError:
            return False