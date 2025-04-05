import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog,
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSlider,
    QRadioButton, QButtonGroup, QCheckBox, QStatusBar, QShortcut
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QKeySequence

# ======================
# 1) Model
# ======================
class ImageModel:
    def __init__(self):
        self._baseline_image = QImage()
        self._highlighted_image = QImage()
        self._highlight_enabled = False

        # Undo 스택
        self._undo_stack = []

    def _push_undo(self):
        if not self._baseline_image.isNull():
            self._undo_stack.append(self._baseline_image.copy())

    def undo(self):
        if self._undo_stack:
            prev_img = self._undo_stack.pop()
            self._baseline_image = prev_img
            if self._highlight_enabled:
                self._rebuild_highlight_image()

    def load_image(self, path: str) -> bool:
        new_img = QImage()
        loaded = new_img.load(path)
        if loaded:
            self._undo_stack.clear()
            self._baseline_image = new_img
            self._rebuild_highlight_image()
        return loaded

    def save_image(self, path: str) -> bool:
        if self._baseline_image.isNull():
            return False
        current_img = self.get_current_image()
        return current_img.save(path)

    def invert_colors(self):
        if not self._baseline_image.isNull():
            self._push_undo()  # 작업 전
            self._baseline_image.invertPixels(QImage.InvertRgb)
            self._rebuild_highlight_image()

    def draw_brush(self, x, y, color: QColor, brush_size: int, prev_x=None, prev_y=None):
        if self._baseline_image.isNull():
            return
        self._push_undo()

        painter = QPainter(self._baseline_image)
        pen = QPen(color, brush_size, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)

        if prev_x is not None and prev_y is not None:
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
        else:
            painter.drawPoint(int(x), int(y))
        painter.end()

        if self._highlight_enabled:
            self._rebuild_highlight_image()

    def draw_line(self, x1, y1, x2, y2, color: QColor, thickness: int):
        if self._baseline_image.isNull():
            return
        self._push_undo()

        painter = QPainter(self._baseline_image)
        pen = QPen(color, thickness, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.end()

        if self._highlight_enabled:
            self._rebuild_highlight_image()

    def set_highlight_enabled(self, enabled: bool):
        self._highlight_enabled = enabled
        if enabled:
            self._rebuild_highlight_image()

    def is_highlight_enabled(self) -> bool:
        return self._highlight_enabled

    def _rebuild_highlight_image(self):
        if self._baseline_image.isNull():
            self._highlighted_image = QImage()
            return

        copy_img = self._baseline_image.copy()
        w, h = copy_img.width(), copy_img.height()
        for y in range(h):
            for x in range(w):
                c = copy_img.pixelColor(x, y)
                # #010101 → #FF0000
                if c.red() == 1 and c.green() == 1 and c.blue() == 1:
                    copy_img.setPixelColor(x, y, QColor(255, 0, 0))
        self._highlighted_image = copy_img

    def get_current_image(self) -> QImage:
        if self._highlight_enabled:
            return self._highlighted_image
        else:
            return self._baseline_image


# ======================
# 2) ViewModel
# ======================
class ImageViewModel:
    def __init__(self, model: ImageModel):
        self._model = model
        self._draw_color = QColor(0, 0, 0)
        self._draw_thickness = 5
        self._line_mode = False

    def open_image(self, path: str) -> bool:
        return self._model.load_image(path)

    def save_image(self, path: str) -> bool:
        return self._model.save_image(path)

    def invert_image(self):
        self._model.invert_colors()

    def draw_brush(self, x, y, prev_x=None, prev_y=None):
        self._model.draw_brush(x, y, self._draw_color, self._draw_thickness,
                               prev_x, prev_y)

    def draw_line(self, x1, y1, x2, y2):
        self._model.draw_line(x1, y1, x2, y2, self._draw_color, self._draw_thickness)

    # Undo
    def undo(self):
        self._model.undo()

    def set_highlight_enabled(self, enabled: bool):
        self._model.set_highlight_enabled(enabled)

    def is_highlight_enabled(self) -> bool:
        return self._model.is_highlight_enabled()

    def set_line_mode(self, enabled: bool):
        self._line_mode = enabled

    def is_line_mode(self) -> bool:
        return self._line_mode

    def set_draw_color(self, color: QColor):
        self._draw_color = color

    def get_draw_color(self) -> QColor:
        return self._draw_color

    def set_draw_thickness(self, thickness: int):
        self._draw_thickness = thickness

    def get_draw_thickness(self) -> int:
        return self._draw_thickness

    def get_current_image(self) -> QImage:
        return self._model.get_current_image()


# ======================
# 3) ImageCanvas
# ======================
class ImageCanvas(QWidget):
    def __init__(self, view_model: ImageViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        self._drawing_brush = False
        self._prev_x = None
        self._prev_y = None

        self._line_start = None
        self._mouse_pos = None

        self._scale_factor = 1.0
        self._translate_x = 0
        self._translate_y = 0

        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.save()

        # 평행 이동 + 배율
        painter.translate(self._translate_x, self._translate_y)
        painter.scale(self._scale_factor, self._scale_factor)

        # 현재 이미지
        current_img = self.view_model.get_current_image()
        if not current_img.isNull():
            painter.drawImage(0, 0, current_img)
        else:
            painter.fillRect(self.rect(), Qt.gray)

        # --- 핵심 변경점 ---
        # 선긋기 모드이지만 아직 첫 클릭을 안 했다면 -> 브러시 미리보기처럼 표시
        # 선긋기 모드 + 첫 클릭이 된 상태라면 -> 선 프리뷰 표시

        if self.view_model.is_line_mode():
            if self._line_start is None:
                # 아직 첫 클릭 전 => 브러시 미리보기 (파란 사각형)
                if self._mouse_pos:
                    self._draw_brush_preview(painter)
            else:
                # 첫 클릭 후 => 선 프리뷰 (파란 선)
                if self._mouse_pos:
                    self._draw_line_preview(painter)
        else:
            # line_mode가 아니면, 항상 브러시 미리보기
            if self._mouse_pos:
                self._draw_brush_preview(painter)

        painter.restore()
        painter.end()

    def _draw_brush_preview(self, painter: QPainter):
        """파란 사각형으로 브러시 미리보기"""
        brush_size = self.view_model.get_draw_thickness()
        half = brush_size / 2.0
        cx = (self._mouse_pos.x() - self._translate_x) / self._scale_factor
        cy = (self._mouse_pos.y() - self._translate_y) / self._scale_factor

        pen = QPen(Qt.blue, 1, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(cx - half), int(cy - half),
                         int(brush_size), int(brush_size))

    def _draw_line_preview(self, painter: QPainter):
        """파란색 선 프리뷰 (선긋기 모드, 첫 클릭 후 두 번째 클릭 전)"""
        pen = QPen(Qt.blue, self.view_model.get_draw_thickness(),
                   Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        sx, sy = self._line_start
        ex = (self._mouse_pos.x() - self._translate_x) / self._scale_factor
        ey = (self._mouse_pos.y() - self._translate_y) / self._scale_factor
        painter.drawLine(int(sx), int(sy), int(ex), int(ey))

    # ---------------------
    # 마우스 이벤트
    # ---------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x_unscaled = (event.x() - self._translate_x) / self._scale_factor
            y_unscaled = (event.y() - self._translate_y) / self._scale_factor

            if self.view_model.is_line_mode():
                if self._line_start is None:
                    # 첫 번째 클릭
                    self._line_start = (x_unscaled, y_unscaled)
                else:
                    # 두 번째 클릭 -> 선 그리기 확정
                    self.view_model.draw_line(self._line_start[0], self._line_start[1],
                                              x_unscaled, y_unscaled)
                    self._line_start = None
                self.update()
            else:
                self._drawing_brush = True
                self._prev_x = x_unscaled
                self._prev_y = y_unscaled
                self.view_model.draw_brush(x_unscaled, y_unscaled)
                self.update()

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.pos()

        x_unscaled = (event.x() - self._translate_x) / self._scale_factor
        y_unscaled = (event.y() - self._translate_y) / self._scale_factor

        # 메인 윈도우 상태바 표시
        if self.parent() and hasattr(self.parent(), "statusBar"):
            if self.parent().statusBar():
                self.parent().statusBar().showMessage(
                    f"X={int(x_unscaled)}, Y={int(y_unscaled)}"
                )

        if self.view_model.is_line_mode():
            # 선 모드
            self.update()  # 프리뷰 갱신
        else:
            if self._drawing_brush:
                self.view_model.draw_brush(x_unscaled, y_unscaled, self._prev_x, self._prev_y)
                self._prev_x = x_unscaled
                self._prev_y = y_unscaled
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.view_model.is_line_mode():
                self._drawing_brush = False
                self._prev_x = None
                self._prev_y = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        mod = event.modifiers()

        if mod & Qt.ControlModifier:
            scale_factor = 1.1 if (delta > 0) else 0.9
            mx = event.x()
            my = event.y()
            old_ax = (mx - self._translate_x) / self._scale_factor
            old_ay = (my - self._translate_y) / self._scale_factor

            new_factor = self._scale_factor * scale_factor
            if new_factor < 0.05:
                new_factor = 0.05
            elif new_factor > 50.0:
                new_factor = 50.0

            self._scale_factor = new_factor
            self._translate_x = mx - self._scale_factor * old_ax
            self._translate_y = my - self._scale_factor * old_ay

        else:
            if mod & Qt.ShiftModifier:
                # 좌우 이동
                if delta > 0:
                    self._translate_x += 50
                else:
                    self._translate_x -= 50
            else:
                # 상하 이동
                if delta > 0:
                    self._translate_y += 50
                else:
                    self._translate_y -= 50

        self.update()

    def set_translate_x(self, value: int):
        self._translate_x = value
        self.update()

    def set_translate_y(self, value: int):
        self._translate_y = value
        self.update()


# ======================
# 4) MainWindow
# ======================
class MainWindow(QMainWindow):
    def __init__(self, view_model: ImageViewModel):
        super().__init__()
        self.view_model = view_model
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("선긋기 첫 클릭 전 브러시 미리보기, 후 선 프리뷰")
        self.resize(1200, 800)

        self.setStatusBar(QStatusBar(self))

        self.canvas = ImageCanvas(self.view_model, parent=self)

        # Ctrl+Z -> Undo
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.on_undo)

        # 색상 라디오버튼
        self.radio_black = QRadioButton("안 (#000000)")
        self.radio_black.setChecked(True)
        self.radio_gray = QRadioButton("바깥 (#010101)")
        self.radio_white = QRadioButton("경계선 (#FFFFFF)")

        color_group = QButtonGroup(self)
        color_group.addButton(self.radio_black)
        color_group.addButton(self.radio_gray)
        color_group.addButton(self.radio_white)

        self.radio_black.toggled.connect(self.on_color_changed)
        self.radio_gray.toggled.connect(self.on_color_changed)
        self.radio_white.toggled.connect(self.on_color_changed)

        # 두께 슬라이더
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 40)
        self.size_slider.setValue(self.view_model.get_draw_thickness())
        self.size_slider.valueChanged.connect(self.on_thickness_changed)
        self.thickness_label = QLabel(f"두께: {self.view_model.get_draw_thickness()}")

        # 선긋기 모드
        self.line_mode_checkbox = QCheckBox("선 긋기 모드")
        self.line_mode_checkbox.setChecked(False)
        self.line_mode_checkbox.stateChanged.connect(self.on_line_mode_changed)

        # 평행 이동 슬라이더 (가로/세로)
        self.translate_x_slider = QSlider(Qt.Horizontal)
        self.translate_x_slider.setRange(-1000, 1000)
        self.translate_x_slider.setValue(0)
        self.translate_x_slider.valueChanged.connect(self.canvas.set_translate_x)

        self.translate_y_slider = QSlider(Qt.Vertical)
        self.translate_y_slider.setRange(-1000, 1000)
        self.translate_y_slider.setValue(0)
        self.translate_y_slider.valueChanged.connect(self.canvas.set_translate_y)
        self.translate_y_slider.setInvertedAppearance(True)

        # 오른쪽 레이아웃
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("색상:"))
        right_layout.addWidget(self.radio_black)
        right_layout.addWidget(self.radio_gray)
        right_layout.addWidget(self.radio_white)

        right_layout.addWidget(self.thickness_label)
        right_layout.addWidget(self.size_slider)
        right_layout.addWidget(self.line_mode_checkbox)
        right_layout.addStretch()

        # 가운데 (캔버스 + 세로 슬라이더)
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

        edit_menu = menubar.addMenu("Edit")

        invert_action = QAction("Invert Colors", self)
        invert_action.triggered.connect(self.on_invert)
        edit_menu.addAction(invert_action)

        highlight_action = QAction("Highlight #010101 → RED", self, checkable=True)
        highlight_action.setChecked(False)
        highlight_action.triggered.connect(self.toggle_highlight)
        edit_menu.addAction(highlight_action)

    def on_undo(self):
        self.view_model.undo()
        self.canvas.update()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.pgm);;All Files (*.*)"
        )
        if path:
            if self.view_model.open_image(path):
                img = self.view_model.get_current_image()
                if not img.isNull():
                    self.canvas.setFixedSize(img.width(), img.height())
                self.canvas.update()

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "",
            "PNG (*.png);;JPG (*.jpg);;All Files (*.*)"
        )
        if path:
            if not self.view_model.save_image(path):
                print("이미지 저장 실패")

    def on_invert(self):
        self.view_model.invert_image()
        self.canvas.update()

    def toggle_highlight(self, checked):
        self.view_model.set_highlight_enabled(checked)
        self.canvas.update()

    def on_color_changed(self):
        if self.radio_black.isChecked():
            self.view_model.set_draw_color(QColor(0, 0, 0))
        elif self.radio_gray.isChecked():
            self.view_model.set_draw_color(QColor(1, 1, 1))
        elif self.radio_white.isChecked():
            self.view_model.set_draw_color(QColor(255, 255, 255))

    def on_thickness_changed(self, value):
        self.view_model.set_draw_thickness(value)
        self.thickness_label.setText(f"두께: {value}")
        self.canvas.update()

    def on_line_mode_changed(self, state):
        enabled = (state == Qt.Checked)
        self.view_model.set_line_mode(enabled)
        if not enabled:
            self.canvas._line_start = None
        self.canvas.update()


def main():
    app = QApplication(sys.argv)
    model = ImageModel()
    view_model = ImageViewModel(model)
    window = MainWindow(view_model)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
