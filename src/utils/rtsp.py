"""RTSP URL helpers."""

from urllib.parse import quote

from src.schema.camera_schema import CameraSchema


def build_rtsp_url(camera: CameraSchema) -> str:
    """Build RTSP URL from camera record."""
    if camera.username and camera.password:
        userinfo = f"{quote(camera.username)}:{quote(camera.password)}@"
    elif camera.username:
        userinfo = f"{quote(camera.username)}@"
    else:
        userinfo = ""
    return f"{camera.protocol}://{userinfo}{camera.ip}:{camera.port}{camera.path}"


def infer_substream_path(path: str) -> str | None:
    """Hikvision/Dahua/RVi substream path, or None if unknown."""
    if not path:
        return None
    if "/Channels/101" in path:
        return path.replace("/Channels/101", "/Channels/102")
    if "/Channels/201" in path:
        return path.replace("/Channels/201", "/Channels/202")
    if path.endswith("/1/1"):
        return path[:-1] + "2"
    return None


def build_go2rtc_rtsp_url(
    camera: CameraSchema, go2rtc_rtsp_base: str, suffix: str = ""
) -> str:
    """RTSP input via go2rtc relay (cam{id} or cam{id}_in)."""
    base = go2rtc_rtsp_base.rstrip("/")
    return f"{base}/cam{camera.id}{suffix}"
