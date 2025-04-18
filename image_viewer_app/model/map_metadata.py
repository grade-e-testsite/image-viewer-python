import yaml


class MapMetadata:
    def __init__(self):
        self.origin = None  # [x, y, theta]
        self.resolution = None
        self.image_height = None  # 추후 필요

    def load_from_yaml(self, path: str):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        self.origin = data.get("origin", [0.0, 0.0, 0.0])
        self.resolution = data.get("resolution", 1.0)

    def set_image_height(self, height: int):
        self.image_height = height

    def get_origin_pixel_position(self):
        if self.origin is None or self.resolution is None or self.image_height is None:
            return None
        ox_m, oy_m, _ = self.origin
        px = -ox_m / self.resolution
        py = self.image_height - (-oy_m / self.resolution)
        return int(px), int(py)
