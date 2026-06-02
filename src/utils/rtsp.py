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


def build_go2rtc_rtsp_url(camera: CameraSchema, go2rtc_rtsp_base: str) -> str:
    """RTSP input via go2rtc relay (cam{id} stream name)."""
    base = go2rtc_rtsp_base.rstrip("/")
    return f"{base}/cam{camera.id}"
