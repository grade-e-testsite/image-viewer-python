__version__ = "0.1.0"
__author__ = "Jinwoo Sung"

from .model.image_model import ImageModel
from .viewmodel.image_view_model import ImageViewModel
from .view.main_window import MainWindow
from .view.image_canvas import ImageCanvas
from PyQt5.QtWidgets import QApplication
import sys


def run():
    app = QApplication(sys.argv)
    model = ImageModel()
    view_model = ImageViewModel(model)
    window = MainWindow(view_model)
    window.show()
    sys.exit(app.exec_())
