from model import ImageModel
from viewmodel import ImageViewModel
from view import MainWindow
import sys
from PyQt5.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    model = ImageModel()
    view_model = ImageViewModel(model)
    window = MainWindow(view_model)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
