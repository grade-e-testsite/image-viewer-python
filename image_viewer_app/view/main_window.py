from ..viewmodel import ImageViewModel
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QSlider,
    QAction,
    QFileDialog,
    QShortcut,
    QMessageBox,  # Add import for QMessageBox
)
from .image_canvas import ImageCanvas
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self, view_model: ImageViewModel):
        super().__init__()
        self.view_model = view_model
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Image viewer")
        self.resize(1200, 800)

        # 마우스 좌표 라벨
        self.pointer_label = QLabel("Pointer: (---, ---)")

        # 이미지 크기 라벨
        w, h = self.view_model.get_image_size()
        self.image_size_label = QLabel(f"Image Size: {w} x {h}")

        self.canvas = ImageCanvas(self.view_model, parent=self)
        self.canvas.pointerMoved.connect(self.update_pointer_label)

        # Ctrl+Z -> Undo 단축키
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.on_undo)

        # 색상 라디오버튼
        self.radio_black = QRadioButton("Outside (#000000)")
        self.radio_black.setChecked(True)
        self.radio_gray = QRadioButton("Inside (#010101)")
        self.radio_white = QRadioButton("Boundary (#FFFFFF)")

        color_group = QButtonGroup(self)
        color_group.addButton(self.radio_black)
        color_group.addButton(self.radio_gray)
        color_group.addButton(self.radio_white)

        self.radio_black.toggled.connect(self.on_color_changed)
        self.radio_gray.toggled.connect(self.on_color_changed)
        self.radio_white.toggled.connect(self.on_color_changed)

        # 두께 슬라이더 + 라벨
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 50)
        self.size_slider.setValue(self.view_model.get_draw_thickness())
        self.size_slider.valueChanged.connect(self.on_thickness_changed)
        self.thickness_label = QLabel(
            f"Thickness: {self.view_model.get_draw_thickness()}"
        )

        # 모드 라디오버튼 (브러시 / 선 / 사각형)
        self.radio_brush = QRadioButton("Brush")
        self.radio_line = QRadioButton("Line")
        self.radio_rect = QRadioButton("Rectangle")

        self.radio_brush.setChecked(True)  # 기본 브러시
        mode_group = QButtonGroup()
        mode_group.addButton(self.radio_brush)
        mode_group.addButton(self.radio_line)
        mode_group.addButton(self.radio_rect)

        self.radio_brush.toggled.connect(self.on_mode_changed)
        self.radio_line.toggled.connect(self.on_mode_changed)
        self.radio_rect.toggled.connect(self.on_mode_changed)

        # 평행 이동 슬라이더
        self.translate_x_slider = QSlider(Qt.Horizontal)
        self.translate_x_slider.setRange(-1000, 1000)
        self.translate_x_slider.setValue(0)
        self.translate_x_slider.valueChanged.connect(self.canvas.set_translate_x)

        self.translate_y_slider = QSlider(Qt.Vertical)
        self.translate_y_slider.setRange(-1000, 1000)
        self.translate_y_slider.setValue(0)
        self.translate_y_slider.valueChanged.connect(self.canvas.set_translate_y)
        self.translate_y_slider.setInvertedAppearance(True)

        # 우측 레이아웃
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Color:"))
        right_layout.addWidget(self.radio_black)
        right_layout.addWidget(self.radio_gray)
        right_layout.addWidget(self.radio_white)

        right_layout.addWidget(self.thickness_label)
        right_layout.addWidget(self.size_slider)

        right_layout.addWidget(self.radio_brush)
        right_layout.addWidget(self.radio_line)
        right_layout.addWidget(self.radio_rect)

        right_layout.addWidget(self.pointer_label)
        right_layout.addWidget(self.image_size_label)
        right_layout.addStretch()

        # 중앙 (캔버스 + 세로 슬라이더)
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.canvas, stretch=1)
        center_layout.addWidget(self.translate_y_slider)

        main_layout = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(center_layout)
        main_layout.addWidget(left_widget, stretch=3)
        main_layout.addLayout(right_layout, stretch=1)

        bottom_layout = QVBoxLayout()
        bottom_layout.addLayout(main_layout)
        bottom_layout.addWidget(self.translate_x_slider)

        central_widget = QWidget()
        central_widget.setLayout(bottom_layout)
        self.setCentralWidget(central_widget)

        # 메뉴
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)  # Add Exit action
        exit_action.triggered.connect(self.close)  # Connect to close method
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Edit")

        invert_action = QAction("Invert Colors", self)
        invert_action.triggered.connect(self.on_invert)
        edit_menu.addAction(invert_action)

        highlight_action = QAction("Show occupied area", self, checkable=True)
        highlight_action.setChecked(False)
        highlight_action.triggered.connect(self.toggle_highlight)
        edit_menu.addAction(highlight_action)

        # 회전 메뉴 (시계/반시계)
        rotate_cw_action = QAction("Rotate Clockwise", self)
        rotate_cw_action.triggered.connect(self.on_rotate_clockwise)
        edit_menu.addAction(rotate_cw_action)

        rotate_ccw_action = QAction("Rotate Counterclockwise", self)
        rotate_ccw_action.triggered.connect(self.on_rotate_counterclockwise)
        edit_menu.addAction(rotate_ccw_action)

    # ---------------------------
    #  (A) Undo
    # ---------------------------
    def on_undo(self):
        self.view_model.undo()
        self.update_image_info()
        self.canvas.update()

    # ---------------------------
    #  (B) File
    # ---------------------------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.pgm);;All Files (*.*)",
        )
        if path:
            if self.view_model.open_image(path):
                img = self.view_model.get_current_image()
                if not img.isNull():
                    self.canvas.setFixedSize(img.width(), img.height())
                self.update_image_info()
                self.canvas.update()

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG (*.png);;PGM (*.pgm);;All Files (*.*)"
        )
        if path:
            if not self.view_model.save_image(path):
                print("Failed to save image.")

    # ---------------------------
    #  (C) Edit
    # ---------------------------
    def on_invert(self):
        self.view_model.invert_image()
        self.canvas.update()

    def toggle_highlight(self, checked):
        self.view_model.set_highlight_enabled(checked)
        self.canvas.update()

    def on_rotate_clockwise(self):
        self.view_model.rotate_clockwise()
        img = self.view_model.get_current_image()
        if not img.isNull():
            self.canvas.setFixedSize(img.width(), img.height())
        self.update_image_info()
        self.canvas.update()

    def on_rotate_counterclockwise(self):
        self.view_model.rotate_counterclockwise()
        img = self.view_model.get_current_image()
        if not img.isNull():
            self.canvas.setFixedSize(img.width(), img.height())
        self.update_image_info()
        self.canvas.update()

    # ---------------------------
    #  (D) UI
    # ---------------------------
    def on_color_changed(self):
        if self.radio_black.isChecked():
            self.view_model.set_draw_color(QColor(0, 0, 0))
        elif self.radio_gray.isChecked():
            self.view_model.set_draw_color(QColor(1, 1, 1))
        elif self.radio_white.isChecked():
            self.view_model.set_draw_color(QColor(255, 255, 255))

    def on_thickness_changed(self, value):
        self.view_model.set_draw_thickness(value)
        self.thickness_label.setText(f"Thickness: {value}")
        self.canvas.update()

    def on_mode_changed(self):
        """라디오버튼 3개 중 어떤 것이 체크됐는지 보고 모드 설정"""
        if self.radio_brush.isChecked():
            self.view_model.set_line_mode(False)
            self.view_model.set_rect_mode(False)
        elif self.radio_line.isChecked():
            self.view_model.set_line_mode(True)
            self.view_model.set_rect_mode(False)
        elif self.radio_rect.isChecked():
            self.view_model.set_line_mode(False)
            self.view_model.set_rect_mode(True)
        # 선/사각형 시작점 초기화
        self.canvas._line_start = None
        self.canvas._rect_start = None
        self.canvas.update()

    # ---------------------------
    #  (E) 라벨 업데이트
    # ---------------------------
    def update_pointer_label(self, x, y):
        """마우스 좌표 라벨"""
        self.pointer_label.setText(f"Pointer: ({x}, {y})")

    def update_image_info(self):
        """이미지 크기 라벨 갱신"""
        w, h = self.view_model.get_image_size()
        self.image_size_label.setText(f"Image Size: {w} x {h}")

    def closeEvent(self, event):
        """Override closeEvent to check for unsaved changes before exiting."""
        if not self.view_model.is_file_opened():  # Check if a file is opened
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Exit Confirmation",
            "Do you want to save the file before exiting?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )

        if reply == QMessageBox.Yes:
            self.save_file()
            event.accept()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()
