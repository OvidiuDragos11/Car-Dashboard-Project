import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import time
import pygame  # Import pygame to play sounds
from dashboard import DashBoard, TriggerAction
from threading import Thread

# Try importing pigpio. If it fails, handle the error.
try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False

class GPIOHandler(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def run(self):
        while True:
            self.parent.check_gpio()
            time.sleep(0.1)  # Reduce GPIO check frequency

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Electric Car DashBoard")
        self.resize(1280, 720)
        self.setStyleSheet("background-color: black;")

        # Initialize pygame mixer
        pygame.mixer.init()

        # Load the horn sound
        self.horn_sound = pygame.mixer.Sound("mixkit-car-horn-718.wav")

        # Set the central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Set the layout
        self.outer_layout = QVBoxLayout(self.central_widget)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create an inner layout to center the dashboard horizontally
        self.inner_layout = QHBoxLayout()
        self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the dashboard widget and add it to the inner layout
        self.dashboard_widget = DashBoard(self.central_widget)
        self.inner_layout.addWidget(self.dashboard_widget)
        self.dashboard_widget.resize(1280, 720)  # aspect ratio 16:9

        # Add the inner layout to the outer layout
        self.outer_layout.addLayout(self.inner_layout)
        self.trigger_action = TriggerAction()

        self.dashboard_widget.show_dashboard(skip_start_screen=True, skip_loading_screen=True)

        self.dashboard_widget_action()

        if PIGPIO_AVAILABLE:
            self.setup_gpio()

        self.battery_level = 50
        self.start_charging()# Starting battery level
        #self.is_charging = True  # Charging state
        self.setup_battery_timer()

        if PIGPIO_AVAILABLE:
            self.gpio_thread = GPIOHandler(self)
            self.gpio_thread.start()

    def dashboard_widget_action(self):
        self.trigger_action = TriggerAction()
        self.trigger_action.set_speedometer_range(200)

    if PIGPIO_AVAILABLE:
        def setup_gpio(self):
            self.pi = pigpio.pi('192.168.1.6')

            if not self.pi.connected:
                print("Failed to connect to Raspberry Pi")
                exit()

            # Define pin numbers
            self.ACCELERATOR_PIN = 17
            self.BRAKE_PIN = 27
            self.HORN_PIN = 22
            self.LEFT_INDICATOR_PIN = 23
            self.RIGHT_INDICATOR_PIN = 24

            # Setup GPIO pins
            self.pi.set_mode(self.ACCELERATOR_PIN, pigpio.INPUT)
            self.pi.set_pull_up_down(self.ACCELERATOR_PIN, pigpio.PUD_DOWN)

            self.pi.set_mode(self.BRAKE_PIN, pigpio.INPUT)
            self.pi.set_pull_up_down(self.BRAKE_PIN, pigpio.PUD_DOWN)

            self.pi.set_mode(self.HORN_PIN, pigpio.INPUT)
            self.pi.set_pull_up_down(self.HORN_PIN, pigpio.PUD_DOWN)

            self.pi.set_mode(self.LEFT_INDICATOR_PIN, pigpio.INPUT)
            self.pi.set_pull_up_down(self.LEFT_INDICATOR_PIN, pigpio.PUD_DOWN)

            self.pi.set_mode(self.RIGHT_INDICATOR_PIN, pigpio.INPUT)
            self.pi.set_pull_up_down(self.RIGHT_INDICATOR_PIN, pigpio.PUD_DOWN)

            # Initialize debounce variables
            self.last_accelerator_state = self.pi.read(self.ACCELERATOR_PIN)
            self.last_brake_state = self.pi.read(self.BRAKE_PIN)
            self.last_horn_state = self.pi.read(self.HORN_PIN)
            self.last_left_indicator_state = self.pi.read(self.LEFT_INDICATOR_PIN)
            self.last_right_indicator_state = self.pi.read(self.RIGHT_INDICATOR_PIN)

            self.last_accelerator_time = time.time()
            self.last_brake_time = time.time()
            self.last_horn_time = time.time()
            self.last_left_indicator_time = time.time()
            self.last_right_indicator_time = time.time()

            self.debounce_time = 0.2  # 200 ms debounce time

        def check_gpio(self):
            try:
                current_time = time.time()
                # Check Accelerator
                pin_state_accelerator = self.pi.read(self.ACCELERATOR_PIN)
                if pin_state_accelerator != self.last_accelerator_state:
                    if current_time - self.last_accelerator_time > self.debounce_time:
                        if pin_state_accelerator == 1:
                            print("Accelerator pressed")
                            self.trigger_action.apply_accelerator()
                        else:
                            self.trigger_action.release_accelerator()
                        self.last_accelerator_time = current_time
                    self.last_accelerator_state = pin_state_accelerator

                # Check Brake
                pin_state_brake = self.pi.read(self.BRAKE_PIN)
                if pin_state_brake != self.last_brake_state:
                    if current_time - self.last_brake_time > self.debounce_time:
                        if pin_state_brake == 1:
                            print("Brake pressed")
                            self.trigger_action.apply_break()
                        else:
                            self.trigger_action.release_break()
                        self.last_brake_time = current_time
                    self.last_brake_state = pin_state_brake

                # Check Horn
                pin_state_horn = self.pi.read(self.HORN_PIN)
                if pin_state_horn != self.last_horn_state:
                    if current_time - self.last_horn_time > self.debounce_time:
                        if pin_state_horn == 1:
                            print("Horn pressed")
                            self.trigger_action.sound_horn()
                            self.horn_sound.play()

                        elif pin_state_horn == 0:
                            print("Horn released")
                            self.trigger_action.off_horn()
                            self.horn_sound.stop()  # Stop the horn sound

                        self.last_horn_time = current_time
                    self.last_horn_state = pin_state_horn

                # Check Left Indicator
                pin_state_left_indicator = self.pi.read(self.LEFT_INDICATOR_PIN)
                if pin_state_left_indicator != self.last_left_indicator_state:
                    if current_time - self.last_left_indicator_time > self.debounce_time:
                        if pin_state_left_indicator == 1:
                            print("Left indicator pressed")
                            self.trigger_action.left_indicator_on_or_off()
                            if self.trigger_action.left_indicator_state:
                                self.trigger_action.right_indicator_state = False  # Turn off right indicator
                        self.last_left_indicator_time = current_time
                    self.last_left_indicator_state = pin_state_left_indicator

                # Check Right Indicator
                pin_state_right_indicator = self.pi.read(self.RIGHT_INDICATOR_PIN)
                if pin_state_right_indicator != self.last_right_indicator_state:
                    if current_time - self.last_right_indicator_time > self.debounce_time:
                        if pin_state_right_indicator == 1:
                            print("Right indicator pressed")
                            self.trigger_action.right_indicator_on_or_off()
                            if self.trigger_action.right_indicator_state:
                                self.trigger_action.left_indicator_state = False  # Turn off left indicator
                        self.last_right_indicator_time = current_time
                    self.last_right_indicator_state = pin_state_right_indicator

            except Exception as e:
                print(f"Error in check_gpio: {e}")

    def setup_battery_timer(self):
        self.battery_timer = QTimer()
        self.battery_timer.start(4000)  # Update every 4 seconds
        self.battery_timer.timeout.connect(self.update_battery)

    def update_battery(self):
        if self.is_charging and self.battery_level < 100:
            self.battery_level = self.battery_level + 1
            print(f"Battery level: {self.battery_level}% (Charging)")

        elif not self.is_charging and self.battery_level > 0:
            self.battery_level -= 1
            print(f"Battery level: {self.battery_level}%")
        self.trigger_action.update_battery_power(self.battery_level)

    def start_charging(self):
        self.is_charging = True
        self.update_battery_level()
        self.trigger_action.charging_on()

    def stop_charging(self):
        self.is_charging = False
        self.update_battery_level()
        self.trigger_action.charging_off()

    def update_battery_level(self):
        print(f"Battery level remains at: {self.battery_level}% (Charging: {self.is_charging})")
        self.trigger_action.update_battery_power(self.battery_level)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Example usage
    window.start_charging()  # Start charging
    #window.stop_charging()  # Stop charging

    sys.exit(app.exec())

