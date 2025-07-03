import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, QMessageBox,
    QVBoxLayout, QSlider, QColorDialog, QPushButton, QLabel, QDialog
)
from PyQt5.QtGui import QPainter, QBrush, QColor, QIcon, QPen
from PyQt5.QtCore import Qt, QRect

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def save_settings(size, thickness, color, transparency):
    """Save settings to a JSON file."""
    settings = {
        "size": size,
        "thickness": thickness,
        "color": {
            "r": color.red(),
            "g": color.green(),
            "b": color.blue(),
        },
        "transparency": transparency,
    }
    with open("settings.json", "w") as f:
        json.dump(settings, f)

def load_settings():
    """Load settings from a JSON file."""
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
            return (
                settings["size"],
                settings["thickness"],
                QColor(settings["color"]["r"], settings["color"]["g"], settings["color"]["b"]),
                settings["transparency"],
            )
    except (FileNotFoundError, KeyError):
        # Return default settings if the file doesn't exist or is corrupt
        return 3, 2, QColor(255, 255, 255), 255  # Default values

class CrosshairOverlay(QWidget):
    def __init__(self, size=3, thickness=2, color=QColor(255, 255, 255), transparency=255):
        super().__init__()
        self.size = size
        self.thickness = thickness
        self.color = color
        self.transparency = transparency

        # Set the window to be frameless, always on top, and transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Get the screen size and move the window to the center
        self.update_window_geometry()

        # Show the window in full-screen mode
        self.showFullScreen()

    def update_window_geometry(self):
        # Dynamically resize the overlay to match the screen size
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        self.setGeometry(0, 0, screen_size.width(), screen_size.height())

    def paintEvent(self, event):
        painter = QPainter(self)

        # Set the pen for the outline of the circle (black with thicker edges and transparency)
        pen = QPen(QColor(0, 0, 0, self.transparency))  # Black border with transparency
        pen.setWidth(self.thickness)  # Use custom thickness
        painter.setPen(pen)

        # Set the brush for the inside of the circle (with custom color and transparency)
        color_with_transparency = QColor(self.color.red(), self.color.green(), self.color.blue(), self.transparency)
        painter.setBrush(QBrush(color_with_transparency))  # Custom color for the dot

        # Get the center of the screen
        screen_width = self.width()
        screen_height = self.height()
        center_x = screen_width // 2
        center_y = screen_height // 2

        # Draw the crosshair (circle with customized size and border)
        dot_radius = self.size  # Custom size for the dot

        # Draw the circle with thicker edges
        painter.drawEllipse(QRect(center_x - dot_radius, center_y - dot_radius, dot_radius * 2, dot_radius * 2))

    def set_crosshair_properties(self, size, thickness, color, transparency):
        """Update crosshair properties and repaint the window."""
        self.size = size
        self.thickness = thickness
        self.color = color
        self.transparency = transparency
        self.update()  # Trigger repaint

class SettingsWindow(QDialog):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("Crosshair Settings")
        self.setGeometry(300, 300, 300, 200)

        # Layout for settings controls
        layout = QVBoxLayout()

        # Size slider
        layout.addWidget(QLabel("Dot Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(20)
        self.size_slider.setValue(self.overlay.size)
        self.size_slider.valueChanged.connect(self.update_settings)
        layout.addWidget(self.size_slider)

        # Thickness slider
        layout.addWidget(QLabel("Edge Thickness:"))
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setMinimum(1)
        self.thickness_slider.setMaximum(10)
        self.thickness_slider.setValue(self.overlay.thickness)
        self.thickness_slider.valueChanged.connect(self.update_settings)
        layout.addWidget(self.thickness_slider)

        # Transparency slider
        layout.addWidget(QLabel("Transparency:"))
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setMinimum(0)
        self.transparency_slider.setMaximum(255)
        self.transparency_slider.setValue(self.overlay.transparency)
        self.transparency_slider.valueChanged.connect(self.update_settings)
        layout.addWidget(self.transparency_slider)

        # Color button
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.open_color_dialog)
        layout.addWidget(self.color_button)

        # Apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

        # Initialize settings values
        self.color = self.overlay.color

    def update_settings(self):
        """Update the settings in real-time as sliders are changed."""
        size = self.size_slider.value()
        thickness = self.thickness_slider.value()
        transparency = self.transparency_slider.value()

        # Update the overlay with the new settings
        self.overlay.set_crosshair_properties(size, thickness, self.color, transparency)

    def open_color_dialog(self):
        """Open a color picker dialog."""
        color = QColorDialog.getColor(initial=self.color, parent=self)
        if color.isValid():
            self.color = color
            self.update_settings()

    def apply_settings(self):
        """Apply the current settings and keep the dialog open."""
        self.update_settings()
        save_settings(self.overlay.size, self.overlay.thickness, self.overlay.color, self.overlay.transparency)
        # Instead of accepting, just hide to keep the main app running
        self.hide()  # Keep the dialog hidden instead of closing

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, app, overlay):
        super().__init__()
        self.app = app
        self.overlay = overlay
        self.is_overlay_visible = True  # Track the visibility state

        # Create a context menu for the tray icon
        self.menu = QMenu()

        # Add Show/Hide action to the context menu
        self.toggle_action = QAction("Hide Crosshair", self)
        self.toggle_action.triggered.connect(self.toggle_overlay)
        self.menu.addAction(self.toggle_action)

        # Add Settings action to the context menu
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(self.settings_action)

        # Add Exit action to the context menu
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(exit_action)

        # Set the context menu for the tray icon
        self.setContextMenu(self.menu)

        # Set a custom icon for the tray
        icon_path = resource_path("dot.ico")  # Updated icon path
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))  # Ensure "dot.ico" is in the same directory
        else:
            QMessageBox.critical(None, "Error", f"Icon file not found: {icon_path}")
            sys.exit(1)

        # Show the tray icon
        self.show()

        # Connect the activated signal to a handler
        self.activated.connect(self.on_tray_icon_activated)

    def toggle_overlay(self):
        if self.is_overlay_visible:
            self.overlay.hide()  # Hide the overlay
            self.toggle_action.setText("Show Crosshair")  # Update menu text
        else:
            self.overlay.show()  # Show the overlay
            self.toggle_action.setText("Hide Crosshair")  # Update menu text

        self.is_overlay_visible = not self.is_overlay_visible  # Toggle the state

    def open_settings(self):
        """Open the settings dialog."""
        self.settings_window = SettingsWindow(self.overlay)
        self.settings_window.show()  # Show the settings dialog

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_overlay()  # Toggle overlay when the tray icon is clicked

    def exit_app(self):
        # Exit the application when the user clicks "Exit"
        self.overlay.hide()  # Hide the overlay first
        self.app.quit()  # Then quit the application

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Check if the system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available.")  # Debugging output
        sys.exit()

    # Load settings on startup
    size, thickness, color, transparency = load_settings()

    # Create the crosshair overlay window with loaded settings
    overlay = CrosshairOverlay(size, thickness, color, transparency)

    # Show the overlay by default
    overlay.show()  # Ensure the overlay is shown at launch

    # Create the system tray icon with a context menu
    tray_icon = SystemTrayIcon(app, overlay)

    sys.exit(app.exec_())
