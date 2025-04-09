from ..model.image_model import ImageModel
from PyQt5.QtGui import QColor, QImage


class ImageViewModel:
    def __init__(self, model: ImageModel):
        self._model = model
        self._draw_color = QColor(0, 0, 0)
        self._draw_thickness = 5

        # 모드: 브러시 / 선 / 사각형
        self._line_mode = False
        self._rect_mode = False

    def open_image(self, path: str) -> bool:
        return self._model.load_image(path)

    def save_image(self, path: str) -> bool:
        return self._model.save_image(path)

    def invert_image(self):
        self._model.invert_colors()

    # --- 브러시, 선, 사각형 ---
    def draw_brush(self, x, y, prev_x=None, prev_y=None):
        self._model.draw_brush(
            x, y, self._draw_color, self._draw_thickness, prev_x, prev_y
        )

    def draw_line(self, x1, y1, x2, y2):
        self._model.draw_line(x1, y1, x2, y2, self._draw_color, self._draw_thickness)

    def fill_rectangle(self, x1, y1, x2, y2):
        self._model.fill_rect_area(x1, y1, x2, y2, self._draw_color)

    # --- Undo ---
    def undo(self):
        self._model.undo()

    # --- 회전 ---
    def rotate_clockwise(self):
        self._model.rotate_clockwise()

    def rotate_counterclockwise(self):
        self._model.rotate_counterclockwise()

    # --- 하이라이트 ---
    def set_highlight_enabled(self, enabled: bool):
        self._model.set_highlight_enabled(enabled)

    def is_highlight_enabled(self) -> bool:
        return self._model.is_highlight_enabled()

    # --- 모드 설정 ---
    def set_line_mode(self, enabled: bool):
        self._line_mode = enabled

    def is_line_mode(self) -> bool:
        return self._line_mode

    def set_rect_mode(self, enabled: bool):
        self._rect_mode = enabled

    def is_rect_mode(self) -> bool:
        return self._rect_mode

    # --- 색상, 굵기 ---
    def set_draw_color(self, color: QColor):
        self._draw_color = color

    def get_draw_color(self) -> QColor:
        return self._draw_color

    def set_draw_thickness(self, thickness: int):
        self._draw_thickness = thickness

    def get_draw_thickness(self) -> int:
        return self._draw_thickness

    # --- 이미지 접근 ---
    def get_current_image(self) -> QImage:
        return self._model.get_current_image()

    def get_image_size(self):
        img = self._model._baseline_image
        if img.isNull():
            return (0, 0)
        return (img.width(), img.height())
