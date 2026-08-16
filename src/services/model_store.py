"""Model catalog and many-to-many camera assignments."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.schema.camera_sql_schema import CameraSqlSchema
from src.schema.model_schema import (
    CameraModelAssignmentSchema,
    ModelCreateSchema,
    ModelSchema,
    ModelUpdateSchema,
)
from src.schema.model_sql_schema import CameraModelSqlSchema, DetectionModelSqlSchema


BUILTIN_MODELS = (
    {
        "code": "yolox_face",
        "name": "YOLOX Face",
        "task": "face",
        "backend": "onnx",
        "path": "assets/yoloxs_face.onnx",
    },
    {
        "code": "mobilefacenet",
        "name": "MobileFaceNet",
        "task": "face",
        "backend": "onnx",
        "path": "assets/w600k_mbf.onnx",
    },
    {
        "code": "yolov8s",
        "name": "YOLOv8s (COCO person)",
        "task": "person",
        "backend": "ultralytics",
        "path": "assets/yolov8s.pt",
    },
    {
        "code": "crowdhuman_yolov5m",
        "name": "YOLOv5 CrowdHuman",
        "task": "person",
        "backend": "crowdhuman",
        "path": "assets/crowdhuman_yolov5m.pt",
    },
    {
        "code": "yolo26n",
        "name": "YOLO26n",
        "task": "person",
        "backend": "onnx",
        "path": "assets/yolo26n.onnx",
    },
    {
        "code": "package_label_stage2",
        "name": "Packages + labels",
        "task": "package",
        "backend": "ultralytics",
        "path": "assets/package_label_stage2.pt",
    },
    {
        "code": "rod_pose",
        "name": "Rod pose",
        "task": "pose",
        "backend": "ultralytics",
        "path": "assets/best_pala_roi.pt",
    },
)


def _json_load(value: str | None) -> dict:
    try:
        data = json.loads(value or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


class ModelStore:
    """CRUD for models and atomic replacement of a camera's model list."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._seed_builtin_models()

    def _rollback(self) -> None:
        try:
            self.pg.session.rollback()
        except Exception:
            pass

    @staticmethod
    def _to_schema(row: DetectionModelSqlSchema) -> ModelSchema:
        return ModelSchema(
            id=int(row.id),
            name=row.name,
            code=row.code,
            task=row.task,
            backend=row.backend,
            path=row.path,
            enabled=bool(row.enabled),
            builtin=bool(row.builtin),
            config=_json_load(row.config),
            exists=Path(row.path).exists(),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _seed_builtin_models(self) -> None:
        with self._lock:
            try:
                existing = {
                    row.code
                    for row in self.pg.session.exec(select(DetectionModelSqlSchema)).all()
                }
                now = datetime.now()
                for item in BUILTIN_MODELS:
                    if item["code"] not in existing:
                        self.pg.session.add(
                            DetectionModelSqlSchema(
                                **item,
                                enabled=True,
                                builtin=True,
                                config="{}",
                                created_at=now,
                                updated_at=now,
                            )
                        )
                self.pg.session.commit()
            except SQLAlchemyError:
                self._rollback()
                raise

    def list(self) -> list[ModelSchema]:
        with self._lock:
            rows = self.pg.session.exec(
                select(DetectionModelSqlSchema).order_by(
                    DetectionModelSqlSchema.task, DetectionModelSqlSchema.name
                )
            ).all()
        return [self._to_schema(row) for row in rows]

    def get(self, model_id: int) -> ModelSchema | None:
        with self._lock:
            row = self.pg.session.get(DetectionModelSqlSchema, model_id)
        return self._to_schema(row) if row else None

    def create(self, payload: ModelCreateSchema) -> ModelSchema:
        now = datetime.now()
        row = DetectionModelSqlSchema(
            **payload.model_dump(exclude={"config"}),
            config=json.dumps(payload.config, ensure_ascii=False),
            builtin=False,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            try:
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except IntegrityError as exc:
                self._rollback()
                raise ValueError("Модель с таким code уже существует") from exc
        return self._to_schema(row)

    def update(self, model_id: int, payload: ModelUpdateSchema) -> ModelSchema | None:
        updates = payload.model_dump(exclude_unset=True)
        with self._lock:
            row = self.pg.session.get(DetectionModelSqlSchema, model_id)
            if not row:
                return None
            if "config" in updates:
                updates["config"] = json.dumps(updates["config"] or {}, ensure_ascii=False)
            for key, value in updates.items():
                setattr(row, key, value)
            row.updated_at = datetime.now()
            try:
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except IntegrityError as exc:
                self._rollback()
                raise ValueError("Модель с таким code уже существует") from exc
        return self._to_schema(row)

    def delete(self, model_id: int) -> bool:
        with self._lock:
            row = self.pg.session.get(DetectionModelSqlSchema, model_id)
            if not row:
                return False
            if row.builtin:
                raise ValueError("Встроенную модель нельзя удалить; её можно отключить")
            assignments = self.pg.session.exec(
                select(CameraModelSqlSchema).where(CameraModelSqlSchema.model_id == model_id)
            ).all()
            for assignment in assignments:
                self.pg.session.delete(assignment)
            self.pg.session.delete(row)
            self.pg.session.commit()
        return True

    def list_camera_models(self, camera_id: int) -> list[CameraModelAssignmentSchema] | None:
        with self._lock:
            if not self.pg.session.get(CameraSqlSchema, camera_id):
                return None
            rows = self.pg.session.exec(
                select(CameraModelSqlSchema).where(
                    CameraModelSqlSchema.camera_id == camera_id
                ).order_by(CameraModelSqlSchema.id)
            ).all()
            models = {
                int(model.id): model
                for model in self.pg.session.exec(select(DetectionModelSqlSchema)).all()
            }
        return [
            CameraModelAssignmentSchema(
                id=int(row.id),
                camera_id=row.camera_id,
                model_id=row.model_id,
                enabled=bool(row.enabled),
                config=_json_load(row.config),
                model=self._to_schema(models[row.model_id]),
            )
            for row in rows
            if row.model_id in models
        ]

    def replace_camera_models(
        self, camera_id: int, model_ids: list[int]
    ) -> list[CameraModelAssignmentSchema] | None:
        with self._lock:
            if not self.pg.session.get(CameraSqlSchema, camera_id):
                return None
            selected = set(model_ids)
            if selected:
                found = {
                    int(row.id)
                    for row in self.pg.session.exec(
                        select(DetectionModelSqlSchema).where(
                            DetectionModelSqlSchema.id.in_(selected)
                        )
                    ).all()
                }
                missing = selected - found
                if missing:
                    raise ValueError(f"Модели не найдены: {sorted(missing)}")

            current = self.pg.session.exec(
                select(CameraModelSqlSchema).where(
                    CameraModelSqlSchema.camera_id == camera_id
                )
            ).all()
            current_ids = {row.model_id for row in current}
            for row in current:
                if row.model_id not in selected:
                    self.pg.session.delete(row)
            for model_id in selected - current_ids:
                self.pg.session.add(
                    CameraModelSqlSchema(camera_id=camera_id, model_id=model_id)
                )
            self.pg.session.commit()
        return self.list_camera_models(camera_id)
