import datetime
import io
from typing import Iterable, Tuple, Union, Any
from pathlib import Path
from zipfile import ZipFile, ZipInfo


class ZipWriter:
    def __init__(self, files: Iterable[Tuple[str, Any]]):
        self.date_time = datetime.datetime.now().timetuple()
        self.files = {k: v for k, v in files}

    def write(self) -> bytes:
        archive = io.BytesIO()
        with ZipFile(archive, "w") as zip_archive:
            for file_name, content in self.files.items():
                zip_archive.writestr(
                    ZipInfo(file_name, date_time=self.date_time), content.read()
                )
        return archive.getbuffer().tobytes()

    def to_file(self, filename: Union[str, Path]) -> None:
        data = self.write()
        open(filename, "wb").write(data)
