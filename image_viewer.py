import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QLabel, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

# -----------------------
# 1) Model
# -----------------------
class ImageModel:
    def __init__(self):
        self._image = QImage()  # 실제 이미지 데이터를 담을 QImage

    def load_image(self, path: str) -> bool:
        """이미지를 파일에서 로드해서 _image에 저장한다.
           성공하면 True, 실패하면 False 반환"""
        loaded = self._image.load(path)
        return loaded

    def save_image(self, path: str) -> bool:
        """_image 내용을 지정된 파일 경로로 저장"""
        if self._image.isNull():
            return False
        return self._image.save(path)

    def invert_colors(self):
        """QImage 색을 반전한다. (픽셀 데이터를 직접 건드릴 수도 있고, invertPixels() 사용 가능)"""
        if not self._image.isNull():
            # InvertRgb: RGB 채널만 반전, alpha는 그대로 둠
            self._image.invertPixels(QImage.InvertRgb)

    def get_image(self) -> QImage:
        """현재 이미지(QImage) 객체를 반환"""
        return self._image

    def set_image(self, image: QImage):
        """외부에서 만든 QImage를 이 모델에 설정"""
        self._image = image


# -----------------------
# 2) ViewModel
# -----------------------
class ImageViewModel:
    def __init__(self, model: ImageModel):
        self._model = model

    def open_image(self, path: str) -> bool:
        """이미지 파일 경로를 받아 Model에 로드 요청"""
        return self._model.load_image(path)

    def save_image(self, path: str) -> bool:
        """Model에 현재 이미지를 저장하도록 요청"""
        return self._model.save_image(path)

    def invert_image(self):
        """Model 내 이미지를 색 반전"""
        self._model.invert_colors()

    def get_current_image(self) -> QImage:
        """View가 현재 이미지를 얻어갈 수 있도록 QImage를 반환"""
        return self._model.get_image()


# -----------------------
# 3) View
# -----------------------
class MainWindow(QMainWindow):
    def __init__(self, view_model: ImageViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PyQt MVVM 이미지 뷰어/에디터 예시")
        self.resize(800, 600)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 이미지 표시용 라벨
        self.image_label = QLabel("이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)

        # 레이아웃에 라벨 배치
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.image_label)

        # 메뉴바 생성
        menubar = self.menuBar()

        # File 메뉴
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file_dialog)
        file_menu.addAction(save_action)

        # Edit 메뉴
        edit_menu = menubar.addMenu("Edit")

        invert_action = QAction("Invert Colors", self)
        invert_action.triggered.connect(self.invert_image)
        edit_menu.addAction(invert_action)

    def open_file_dialog(self):
        """사용자가 Open 메뉴를 선택하면 호출. 파일 열기 다이얼로그를 띄우고, 선택하면 ViewModel 통해 로드."""
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", 
                                              "Images (*.png *.jpg *.jpeg *.bmp *.pgm)")
        if path:
            success = self.view_model.open_image(path)
            if success:
                self.update_image_view()
            else:
                self.image_label.setText("이미지 로드 실패")

    def save_file_dialog(self):
        """사용자가 Save 메뉴를 선택하면 호출. 파일 저장 다이얼로그를 띄움."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", 
                                              "PNG (*.png);;JPG (*.jpg);;All Files (*.*)")
        if path:
            success = self.view_model.save_image(path)
            if not success:
                self.image_label.setText("이미지 저장 실패")

    def invert_image(self):
        """사용자가 Invert Colors를 선택하면 ViewModel로 반전 작업 요청 후 뷰 갱신."""
        self.view_model.invert_image()
        self.update_image_view()

    def update_image_view(self):
        """ViewModel에서 최신 QImage를 가져와 QLabel에 표시(QPixmap 변환)."""
        qimage = self.view_model.get_current_image()
        if not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("이미지 없음")


# -----------------------
# 4) Main - 실행 진입점
# -----------------------
def main():
    app = QApplication(sys.argv)
    
    model = ImageModel()
    view_model = ImageViewModel(model)
    window = MainWindow(view_model)
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

