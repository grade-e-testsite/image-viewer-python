from ..viewmodel import ImageViewModel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QWidget


class ImageCanvas(QWidget):
    def __init__(self, view_model: ImageViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model

        self._drawing_brush = False
        self._prev_x = None
        self._prev_y = None

        self._line_start = None  # 선 모드
        self._rect_start = None  # 사각형 모드
        self._mouse_pos = None

        self._scale_factor = 1.0
        self._translate_x = 0
        self._translate_y = 0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure the widget can receive key events

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.save()

        # 평행 이동 + 배율
        painter.translate(self._translate_x, self._translate_y)
        painter.scale(self._scale_factor, self._scale_factor)

        current_img = self.view_model.get_current_image()
        if not current_img.isNull():
            painter.drawImage(0, 0, current_img)
        else:
            painter.fillRect(self.rect(), Qt.gray)

        # --- 모드별 프리뷰 ---
        if self.view_model.is_line_mode():
            if self._line_start is None:
                # 첫 클릭 전: 브러시 미리보기처럼 표시?
                if self._mouse_pos:
                    self._draw_brush_preview(painter)
            else:
                # 첫 클릭 후 -> 선 프리뷰
                if self._mouse_pos:
                    self._draw_line_preview(painter)

        elif self.view_model.is_rect_mode():
            if self._rect_start is None:
                # 첫 클릭 전 -> 브러시 미리보기
                if self._mouse_pos:
                    self._draw_brush_preview(painter)
            else:
                # 첫 클릭 후 -> 사각형 테두리 표시
                if self._mouse_pos:
                    self._draw_rectangle_preview(painter)

        else:
            # 브러시 모드
            if self._mouse_pos:
                self._draw_brush_preview(painter)

        painter.restore()
        painter.end()

    def _draw_brush_preview(self, painter: QPainter):
        brush_size = self.view_model.get_draw_thickness()
        half = brush_size / 2.0
        if not self._mouse_pos:
            return
        cx = (self._mouse_pos.x() - self._translate_x) / self._scale_factor
        cy = (self._mouse_pos.y() - self._translate_y) / self._scale_factor

        pen = QPen(Qt.blue, 1, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # 사각형 브러시 미리보기
        painter.drawRect(
            int(cx - half), int(cy - half), int(brush_size), int(brush_size)
        )

    def _draw_line_preview(self, painter: QPainter):
        pen = QPen(
            Qt.blue,
            self.view_model.get_draw_thickness(),
            Qt.SolidLine,
            Qt.SquareCap,
            Qt.MiterJoin,
        )
        painter.setPen(pen)
        sx, sy = self._line_start
        ex = (self._mouse_pos.x() - self._translate_x) / self._scale_factor
        ey = (self._mouse_pos.y() - self._translate_y) / self._scale_factor
        painter.drawLine(int(sx), int(sy), int(ex), int(ey))

    def _draw_rectangle_preview(self, painter: QPainter):
        pen = QPen(Qt.blue, 1, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        sx, sy = self._rect_start
        ex = (self._mouse_pos.x() - self._translate_x) / self._scale_factor
        ey = (self._mouse_pos.y() - self._translate_y) / self._scale_factor

        left = min(sx, ex)
        right = max(sx, ex)
        top = min(sy, ey)
        bottom = max(sy, ey)

        painter.drawRect(int(left), int(top), int(right - left), int(bottom - top))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x_unscaled = (event.x() - self._translate_x) / self._scale_factor
            y_unscaled = (event.y() - self._translate_y) / self._scale_factor

            # --- 선 모드 ---
            if self.view_model.is_line_mode():
                if self._line_start is None:
                    self._line_start = (x_unscaled, y_unscaled)
                else:
                    self.view_model.draw_line(
                        self._line_start[0], self._line_start[1], x_unscaled, y_unscaled
                    )
                    self._line_start = None
                self.update()
                return

            # --- 사각형 모드 ---
            if self.view_model.is_rect_mode():
                if self._rect_start is None:
                    self._rect_start = (x_unscaled, y_unscaled)
                else:
                    self.view_model.fill_rectangle(
                        self._rect_start[0], self._rect_start[1], x_unscaled, y_unscaled
                    )
                    self._rect_start = None
                self.update()
                return

            # --- 브러시 모드 ---
            self._drawing_brush = True
            self._prev_x = x_unscaled
            self._prev_y = y_unscaled
            self.view_model.draw_brush(x_unscaled, y_unscaled)
            self.update()

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.pos()

        x_unscaled = (event.x() - self._translate_x) / self._scale_factor
        y_unscaled = (event.y() - self._translate_y) / self._scale_factor

        # 부모(MainWindow) 쪽에 마우스 좌표 알림
        main_win = self.window()
        if hasattr(main_win, "update_pointer_label"):
            main_win.update_pointer_label(int(x_unscaled), int(y_unscaled))
        # 브러시 드래그
        if (not self.view_model.is_line_mode()) and (
            not self.view_model.is_rect_mode()
        ):
            if self._drawing_brush:
                self.view_model.draw_brush(
                    x_unscaled, y_unscaled, self._prev_x, self._prev_y
                )
                self._prev_x = x_unscaled
                self._prev_y = y_unscaled

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 브러시 모드 드래그 종료
            if (not self.view_model.is_line_mode()) and (
                not self.view_model.is_rect_mode()
            ):
                self._drawing_brush = False
                self._prev_x = None
                self._prev_y = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        mod = event.modifiers()

        if mod & Qt.ControlModifier:
            # 마우스 중심 확대/축소
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # Cancel line or rectangle drawing
            if self._line_start is not None:
                self._line_start = None
            if self._rect_start is not None:
                self._rect_start = None
            self.update()
