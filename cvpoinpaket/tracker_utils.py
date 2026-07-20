import cv2


def create_tracker():
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    if hasattr(cv2, "TrackerMIL_create"):
        return cv2.TrackerMIL_create()
    if hasattr(cv2, "TrackerDaSiamRPN_create"):
        return cv2.TrackerDaSiamRPN_create()
    raise RuntimeError("В этой версии OpenCV нет доступного трекера")
