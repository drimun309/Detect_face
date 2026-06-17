"""HTTP Range support for video file streaming (перемотка в браузере)."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import Request
from starlette.responses import FileResponse, StreamingResponse

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


def video_file_response(request: Request, path: Path, media_type: str = "video/mp4") -> FileResponse | StreamingResponse:
    if not path.is_file():
        raise FileNotFoundError(str(path))

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(
            path,
            media_type=media_type,
            headers={"Accept-Ranges": "bytes"},
        )

    match = _RANGE_RE.match(range_header.strip())
    if not match:
        return FileResponse(path, media_type=media_type, headers={"Accept-Ranges": "bytes"})

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else file_size - 1
    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        return StreamingResponse(
            iter(()),
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Accept-Ranges": "bytes",
            },
        )

    length = end - start + 1

    def iter_file():
        with path.open("rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1024 * 512, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        iter_file(),
        status_code=206,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
        },
    )
