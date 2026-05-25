"""Web API for face enrollment (photo + video → PostgreSQL)."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.schema.enroll_schema import EnrollResultSchema, EnrolledListSchema, EnrolledPersonSchema
from src.services.enrollment_service import (
    EnrollmentOptions,
    delete_person,
    list_enrolled_summary,
    run_enrollment_upload,
)
from src.services.face_embedding_store import get_face_embedding_store
from src.services.settings_store import SettingsStore
from src.streaming.stream_manager import get_stream_manager
from src.schema.configs import Configs


class EnrollApi:
    def __init__(self, cfg: Configs, settings_store: SettingsStore) -> None:
        self.cfg = cfg
        self.settings_store = settings_store
        self.router = APIRouter()
        self.setup()

    def setup(self) -> None:
        @self.router.get("/faces/enrolled", response_model=EnrolledListSchema)
        async def list_enrolled() -> EnrolledListSchema:
            manager = get_stream_manager()
            items = list_enrolled_summary(manager.db)
            total = sum(p["count"] for p in items)
            return EnrolledListSchema(
                items=[EnrolledPersonSchema(**p) for p in items],
                total_embeddings=total,
            )

        @self.router.delete("/faces/person/{name}", status_code=204)
        async def delete_enrolled_person(name: str) -> None:
            manager = get_stream_manager()
            deleted = delete_person(manager.db, name)
            if deleted == 0:
                raise HTTPException(status_code=404, detail="Person not found")
            store = get_face_embedding_store()
            if store:
                store.reload()

        @self.router.post("/faces/enroll", response_model=EnrollResultSchema)
        async def enroll_person(
            name: str = Form(...),
            replace: bool = Form(False),
            every: int = Form(15),
            max_embeddings: int = Form(30),
            photos: list[UploadFile] = File(default=[]),
            videos: list[UploadFile] = File(default=[]),
        ) -> EnrollResultSchema:
            """Загрузка фото/видео и сохранение эмбеддингов в PostgreSQL."""
            det = self.settings_store.get()
            manager = get_stream_manager()

            photo_files: list[tuple[str, bytes]] = []
            for f in photos:
                if f.filename:
                    photo_files.append((f.filename, await f.read()))

            video_files: list[tuple[str, bytes]] = []
            for f in videos:
                if f.filename:
                    video_files.append((f.filename, await f.read()))

            options = EnrollmentOptions(
                name=name,
                every=max(1, every),
                max_embeddings=max(1, min(max_embeddings, 100)),
                replace=replace,
                conf=det.fr_det_conf,
                nms=det.fr_det_nms,
                min_score=det.min_det_score,
            )

            try:
                result = run_enrollment_upload(
                    options,
                    photo_files=photo_files,
                    video_files=video_files,
                    engine=manager.engine,
                    db=manager.db,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

            store = get_face_embedding_store()
            if store:
                store.reload()

            return EnrollResultSchema(
                saved=result.saved,
                photos_ok=result.photos_ok,
                photos_skip=result.photos_skip,
                frames_ok=result.frames_ok,
                frames_skip=result.frames_skip,
                logs=result.logs,
            )
