import datetime
import io
from pathlib import Path
from typing import Any, Iterable, Tuple, Union
from zipfile import ZipFile, ZipInfo


class ZipWriter:
    def __init__(self, files: Iterable[Tuple[str, Any]]):
        self.date_time = datetime.datetime.now()
        self.files = {k: v for k, v in files}

    def write(self) -> bytes:
        archive = io.BytesIO()
        with ZipFile(archive, "w") as zip_archive:
            for file_name, content in self.files.items():
                zip_archive.writestr(
                    ZipInfo(file_name, date_time=self.date_time.timetuple()),
                    content.read(),
                )
        return archive.getbuffer().tobytes()

    def to_file(self, filename: Union[str, Path]) -> None:
        data = self.write()
        open(filename, "wb").write(data)
