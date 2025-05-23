import sys
import os
import re
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel,
                             QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                             QTextEdit, QProgressBar, QFrame, QScrollArea,
                             QComboBox, QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

# Import the base highlight reel extractor (no title cards)
from src.highlight_reel_extractor import VideoSegment, extract_segments_from_text
from src.highlight_reel_extractor import create_highlight_reel

class StyledButton(QPushButton):
    """Custom styled button with modern appearance"""

    def __init__(self, text, primary=False, icon=None):
        super().__init__(text)
        self.setMinimumHeight(36)
        font = self.font()
        font.setPointSize(10)
        font.setBold(True)  # Make text bold
        self.setFont(font)

        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4a86e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
                QPushButton:pressed {
                    background-color: #2a66c8;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #888888;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    color: #333333;
                    border: 1px solid #aaaaaa;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                    border: 1px solid #888888;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
            """)

        if icon:
            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(18, 18))


class FileSelectionCard(QFrame):
    """Card for file selection with icon and status"""

    def __init__(self, title, icon_path=None, select_text="Select File"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)

        # Header with title
        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_font = title_label.font()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # File status
        status_layout = QHBoxLayout()
        self.status_icon = QLabel("📄")  # Using emoji as placeholder
        status_layout.addWidget(self.status_icon)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #777777;")
        status_layout.addWidget(self.file_label, 1)

        self.select_button = StyledButton(select_text)
        self.select_button.setMinimumWidth(120)  # Make buttons wider
        status_layout.addWidget(self.select_button)

        layout.addLayout(status_layout)

    def set_file(self, file_path):
        if file_path:
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: #333333; font-weight: bold;")
            self.status_icon = QLabel("✅")  # Change to checkmark
        else:
            self.file_label.setText("No file selected")
            self.file_label.setStyleSheet("color: #777777;")


class WorkerThread(QThread):
    """Worker thread for creating highlight reels without freezing the UI."""
    update_progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, video_path, content, output_dir):
        super().__init__()
        self.video_path = video_path
        self.content = content
        self.output_dir = output_dir

    def run(self):
        try:
            # Extract segments from content
            self.update_progress.emit("Analyzing content for video segments...")

            # Use the extract_segments_from_text function
            segments = extract_segments_from_text(self.content)

            if not segments:
                self.update_progress.emit("No valid segments found in the content.")
                self.finished.emit(False, "No valid segments found.")
                return

            self.update_progress.emit(f"Found {len(segments)} segments to extract.")

            # Log segment details
            for i, segment in enumerate(segments):
                self.update_progress.emit(
                    f"Segment {i + 1}: {segment.title} - "
                    f"Start: {segment.start_time // 3600:02d}:{(segment.start_time % 3600) // 60:02d}:{segment.start_time % 60:02d}, "
                    f"Duration: {segment.duration // 60:02d}:{segment.duration % 60:02d}"
                )

            # Create output filename
            video_filename = os.path.splitext(os.path.basename(self.video_path))[0]
            output_filename = f"{video_filename}_highlight_reel.mp4"
            output_path = os.path.join(self.output_dir, output_filename)

            # Create highlight reel (directly using the base function without title cards)
            self.update_progress.emit("Creating highlight reel (this may take a while)...")
            output = create_highlight_reel(self.video_path, segments, output_path)

            self.update_progress.emit(f"Highlight reel created successfully!")
            self.finished.emit(True, output)

        except Exception as e:
            self.update_progress.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class HighlightReelUI(QMainWindow):
    """UI for creating highlight reels from content specifications without title cards."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Highlight Reel Creator (No Title Cards)")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
            }
            QComboBox {
                min-height: 30px;
                padding: 5px;
                border: 1px solid #aaaaaa;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: 0px;
                width: 25px;
            }
        """)
        self.video_path = None
        self.is_processing = False

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Create header
        header = QLabel("Highlight Reel Creator")
        header_font = header.font()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        main_layout.addWidget(header)

        # Description
        description = QLabel("Extract key moments from videos and create highlight reels (without title cards)")
        description.setStyleSheet("color: #666666;")
        main_layout.addWidget(description)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #e0e0e0;")
        main_layout.addWidget(separator)

        # Create file selection area - Make section header more visible
        section_label = QLabel("1. Select your video")
        section_font = section_label.font()
        section_font.setBold(True)
        section_font.setPointSize(12)
        section_label.setFont(section_font)
        main_layout.addWidget(section_label)

        # Video selection card
        self.video_card = FileSelectionCard("Video File", select_text="Select Video")
        self.video_card.select_button.clicked.connect(self._select_video)
        main_layout.addWidget(self.video_card)

        # Format selection - Make section header more visible
        section_label = QLabel("2. Enter segment details")
        section_label.setFont(section_font)
        main_layout.addWidget(section_label)

        format_card = QFrame()
        format_card.setFrameShape(QFrame.Shape.StyledPanel)
        format_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        format_layout = QVBoxLayout(format_card)

        # Format help header
        format_header = QLabel("Format Information")
        format_header_font = format_header.font()
        format_header_font.setBold(True)
        format_header.setFont(format_header_font)
        format_layout.addWidget(format_header)

        # Format selector layout with example button
        format_selector_layout = QHBoxLayout()

        self.format_help_label = QLabel(
            "Enter your highlight reel specification using one of the supported formats:"
        )
        self.format_help_label.setWordWrap(True)
        self.format_help_label.setStyleSheet("color: #666666; padding: 5px;")
        format_layout.addWidget(self.format_help_label)

        # Add format details
        self.format_details = QLabel(
            "• Standard Format with #### headers and STARTING TIMESTAMP: fields\n"
            "• Simple Format with SEGMENT:, TIME:, and DURATION: markers\n"
            "• Custom Format with 'Segment X:' titles and **STARTING TIMESTAMP:** markers"
        )
        self.format_details.setStyleSheet("color: #333333; padding: 5px;")
        format_layout.addWidget(self.format_details)

        self.show_example_button = StyledButton("Show Examples")
        self.show_example_button.setMinimumWidth(120)
        self.show_example_button.clicked.connect(self._show_format_examples)
        format_selector_layout.addWidget(self.show_example_button)
        format_selector_layout.addStretch()
        format_layout.addLayout(format_selector_layout)

        main_layout.addWidget(format_card)

        # Content editor
        content_label = QLabel("Segment Specifications:")
        content_label_font = content_label.font()
        content_label_font.setBold(True)
        content_label.setFont(content_label_font)
        main_layout.addWidget(content_label)

        self.content_editor = QTextEdit()
        self.content_editor.setMinimumHeight(180)
        self.content_editor.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #aaaaaa;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.content_editor.textChanged.connect(self._check_ready)
        main_layout.addWidget(self.content_editor)

        # Set placeholder text for the content editor
        self.content_editor.setPlaceholderText(
            "Enter your highlight reel specification here...\n\n"
            "Example custom format:\n"
            "Segment 1: Opening Hook - AI Hallucinations in Action (01:30)\n"
            "**STARTING TIMESTAMP:** 00:16:30 **CONTENT DESCRIPTION:** Start with the most surprising discovery..."
        )

        # Add output directory section - Make section header more visible
        section_label = QLabel("3. Select output location")
        section_label.setFont(section_font)
        main_layout.addWidget(section_label)

        # Output directory card
        self.output_card = FileSelectionCard("Output Directory", select_text="Select Folder")
        self.output_card.file_label.setText(os.path.join(os.getcwd(), "highlight_reels"))
        self.output_card.select_button.clicked.connect(self._select_output_dir)
        main_layout.addWidget(self.output_card)

        # Process button - Make it more prominent
        self.process_button = StyledButton("Create Highlight Reel", primary=True)
        self.process_button.setMinimumHeight(50)  # Taller button
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._process_highlight_reel)
        main_layout.addWidget(self.process_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f0f0f0;
                text-align: center;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Create log output area with scroll - Make section header more visible
        section_label = QLabel("4. Results")
        section_label.setFont(section_font)
        main_layout.addWidget(section_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #aaaaaa;
                border-radius: 6px;
                padding: 8px;
                font-family: monospace;
            }
        """)
        log_layout.addWidget(self.log_output)

        scroll.setWidget(log_container)
        main_layout.addWidget(scroll)

        # Show initial instructions
        self.log_output.append("Welcome to the Highlight Reel Creator (No Title Cards)!")
        self.log_output.append("This version creates highlight reels without title cards to preserve audio quality.")
        self.log_output.append("Select your video file and enter segment specifications to begin.")

    def _show_format_examples(self):
        """Show examples of the supported formats."""
        example_dialog = QMessageBox(self)
        example_dialog.setWindowTitle("Format Examples")
        example_dialog.setText("Supported Format Examples")

        custom_format = """Video Highlight Reel Outline
Segment 1: Opening Hook - AI Hallucinations in Action (01:30)
**STARTING TIMESTAMP:** 00:16:30 **CONTENT DESCRIPTION:** Start with the most surprising discovery from our week: AI confidently making up contractor reviews that don't exist.

Segment 2: Daily News Update Automation (01:45)
**STARTING TIMESTAMP:** 00:02:30 **CONTENT DESCRIPTION:** Follow Netta's journey debugging the automated news email system.
"""

        standard_format = """#### Introduction (2 minutes)
STARTING TIMESTAMP: 00:01:30
- This is the introduction section
- It contains bullet points for content

#### Main Content (3 minutes)
STARTING TIMESTAMP: 00:15:45
- Here's the main content
- With multiple points to cover
"""

        simple_format = """SEGMENT: Opening Segment
TIME: 00:01:30
DURATION: 2 minutes
This is the opening segment description.

SEGMENT: Main Segment
TIME: 00:15:45
DURATION: 3 minutes
This is the main segment description.
"""

        example_text = f"1. Custom Format (recommended):\n\n{custom_format}\n\n"
        example_text += f"2. Standard Format:\n\n{standard_format}\n\n"
        example_text += f"3. Simple Format:\n\n{simple_format}"

        example_dialog.setDetailedText(example_text)
        example_dialog.exec()

    def _select_video(self):
        """Handle video selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            os.path.expanduser("~/Desktop"),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
        )

        if file_path:
            self.video_path = file_path
            self.video_card.set_file(file_path)
            self._check_ready()
            self.log_output.append(f"Selected video: {os.path.basename(file_path)}")

    def _select_output_dir(self):
        """Handle output directory selection."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            os.path.expanduser("~/Desktop")
        )

        if dir_path:
            self.output_card.file_label.setText(dir_path)
            self.log_output.append(f"Output directory: {dir_path}")

    def _check_ready(self):
        """Check if all conditions are met to enable the process button."""
        has_video = self.video_path is not None
        has_content = len(self.content_editor.toPlainText().strip()) > 0
        self.process_button.setEnabled(bool(has_video and has_content) and not self.is_processing)

    def _process_highlight_reel(self):
        """Process the highlight reel with selected files and content."""
        # Prevent multiple processing attempts
        if self.is_processing:
            return

        self.is_processing = True

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.process_button.setEnabled(False)
            self.log_output.append("\nProcessing highlight reel...")

            # Change cursor to waiting
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            content = self.content_editor.toPlainText()
            output_dir = self.output_card.file_label.text()

            # Use a timer to allow the UI to update before starting processing
            QTimer.singleShot(100, lambda: self._execute_processing(content, output_dir))

        except Exception as e:
            self._reset_ui()
            self.log_output.append(f"\n❌ Error setting up processing: {str(e)}")

    def _execute_processing(self, content, output_dir):
        """Execute the actual highlight reel processing (called by timer)"""
        try:
            # Start worker thread
            self.worker = WorkerThread(self.video_path, content, output_dir)
            self.worker.update_progress.connect(self.update_progress)
            self.worker.finished.connect(self.process_finished)
            self.worker.start()
        except Exception as e:
            self.log_output.append(f"\n❌ Error: {str(e)}")
            self._reset_ui()

    def update_progress(self, message):
        """Update progress message."""
        self.log_output.append(message)

        # Scroll to bottom of log
        scroll_bar = self.log_output.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def process_finished(self, success, result):
        """Handle completion of the worker thread."""
        if success:
            self.log_output.append("\n✅ Highlight reel created successfully!")
            self.log_output.append(f"Output saved to: {result}")

            # Try to open output folder
            try:
                if sys.platform == "darwin":  # macOS
                    os.system(f'open "{os.path.dirname(result)}"')
                elif sys.platform == "win32":  # Windows
                    os.startfile(os.path.dirname(result))
                self.log_output.append("\nOpened output folder!")
            except Exception:
                self.log_output.append(f"\nOutput folder is at: {os.path.dirname(result)}")
        else:
            self.log_output.append("\n❌ Highlight reel creation failed!")
            self.log_output.append(f"Error: {result}")

        # Reset UI using a small delay to ensure everything completes
        QTimer.singleShot(100, self._reset_ui)

    def _reset_ui(self):
        """Reset the UI after processing completes"""
        self.is_processing = False
        self.progress_bar.setVisible(False)
        self._check_ready()
        QApplication.restoreOverrideCursor()

        # Ensure we process any pending events
        QApplication.processEvents()


def main():
    app = QApplication(sys.argv)

    # Apply global stylesheet
    app.setStyle("Fusion")

    window = HighlightReelUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()