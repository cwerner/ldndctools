from abc import ABC, abstractmethod
from typing import Any, Dict

from ldndctools.misc.types import BoundingBox


class Page(ABC):
    @abstractmethod
    def write(self):
        pass


# Only used for separating namespace, everything can be saved at state variable as well.
CONFIG_DEFAULTS: Dict[str, Any] = {
    "slider_value": 0,
    "resolution": "LR",
    "regions": ["EU28PLUS"],
    "countries": [],
    "file_name": "sites",
    "bbox": BoundingBox(x1=-180, x2=180, y1=-90, y2=90),
}
