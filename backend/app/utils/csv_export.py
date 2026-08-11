import csv
import io
from collections.abc import Sequence


def build_csv(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()
