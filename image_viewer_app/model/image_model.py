from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QTransform
from PyQt5.QtCore import Qt


class ImageModel:
    def __init__(self):
        self._baseline_image = QImage()
        self._highlighted_image = QImage()
        self._highlight_enabled = False

        # Undo 스택
        self._undo_stack = []

    def _push_undo(self):
        """현재 baseline 이미지를 undo 스택에 복사해서 저장 (작업 전 호출)"""
        if not self._baseline_image.isNull():
            self._undo_stack.append(self._baseline_image.copy())

    def undo(self):
        """스택에서 마지막 이미지를 가져와 baseline으로 되돌림"""
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
            self._push_undo()
            self._baseline_image.invertPixels(QImage.InvertRgb)
            self._rebuild_highlight_image()

    def draw_brush(
        self, x, y, color: QColor, brush_size: int, prev_x=None, prev_y=None
    ):
        """브러시로 자유 드로잉 (사각형 캡)"""
        if self._baseline_image.isNull():
            return
        self._push_undo()

        painter = QPainter(self._baseline_image)
        pen = QPen(color, brush_size, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)

        if (prev_x is not None) and (prev_y is not None):
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
        else:
            painter.drawPoint(int(x), int(y))
        painter.end()

        if self._highlight_enabled:
            self._rebuild_highlight_image()

    def draw_line(self, x1, y1, x2, y2, color: QColor, thickness: int):
        """시작점→끝점 직선"""
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

    def fill_rect_area(self, x1, y1, x2, y2, color: QColor):
        """사각형 영역 내부를 지정 색으로 채우기"""
        if self._baseline_image.isNull():
            return
        self._push_undo()

        painter = QPainter(self._baseline_image)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        left = min(int(x1), int(x2))
        right = max(int(x1), int(x2))
        top = min(int(y1), int(y2))
        bottom = max(int(y1), int(y2))

        painter.drawRect(left, top, right - left, bottom - top)
        painter.end()

        if self._highlight_enabled:
            self._rebuild_highlight_image()

    # -----------------------
    #    이미지 회전
    # -----------------------
    def rotate_clockwise(self):
        """시계 방향 90도 회전"""
        if not self._baseline_image.isNull():
            self._push_undo()
            transform = QTransform()
            transform.rotate(90)  # 90도
            rotated = self._baseline_image.transformed(transform)
            self._baseline_image = rotated
            if self._highlight_enabled:
                self._rebuild_highlight_image()

    def rotate_counterclockwise(self):
        """반시계 방향 90도 회전"""
        if not self._baseline_image.isNull():
            self._push_undo()
            transform = QTransform()
            transform.rotate(-90)
            rotated = self._baseline_image.transformed(transform)
            self._baseline_image = rotated
            if self._highlight_enabled:
                self._rebuild_highlight_image()

    def set_highlight_enabled(self, enabled: bool):
        self._highlight_enabled = enabled
        if enabled:
            self._rebuild_highlight_image()

    def is_highlight_enabled(self) -> bool:
        return self._highlight_enabled

    def _rebuild_highlight_image(self):
        """(1,1,1,255) 픽셀 => (255,0,0,255)로"""
        if self._baseline_image.isNull():
            self._highlighted_image = QImage()
            return

        copy_img = self._baseline_image.copy()
        w, h = copy_img.width(), copy_img.height()

        for y in range(h):
            for x in range(w):
                c = copy_img.pixelColor(x, y)
                # alpha=255도 체크
                if (
                    c.red() == 1
                    and c.green() == 1
                    and c.blue() == 1
                    and c.alpha() == 255
                ):
                    copy_img.setPixelColor(x, y, QColor(255, 0, 0, 255))

        self._highlighted_image = copy_img

    def get_current_image(self) -> QImage:
        if self._highlight_enabled:
            return self._highlighted_image
        else:
            return self._baseline_image
