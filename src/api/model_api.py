"""REST API for models and camera-to-model assignments."""

from fastapi import APIRouter, HTTPException, status

from src.schema.model_schema import (
    CameraModelAssignmentListSchema,
    CameraModelsUpdateSchema,
    ModelCreateSchema,
    ModelListSchema,
    ModelSchema,
    ModelUpdateSchema,
)
from src.services.model_store import ModelStore


class ModelApi:
    def __init__(self, store: ModelStore, camera_store=None) -> None:
        self.store = store
        self.camera_store = camera_store
        self.router = APIRouter()
        self.setup()

    def setup(self) -> None:
        @self.router.get("/models", response_model=ModelListSchema)
        async def list_models() -> ModelListSchema:
            return ModelListSchema(items=self.store.list())

        @self.router.post(
            "/models", response_model=ModelSchema, status_code=status.HTTP_201_CREATED
        )
        async def create_model(payload: ModelCreateSchema) -> ModelSchema:
            try:
                return self.store.create(payload)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

        @self.router.get("/models/{model_id}", response_model=ModelSchema)
        async def get_model(model_id: int) -> ModelSchema:
            model = self.store.get(model_id)
            if not model:
                raise HTTPException(status_code=404, detail="Model not found")
            return model

        @self.router.put("/models/{model_id}", response_model=ModelSchema)
        async def update_model(model_id: int, payload: ModelUpdateSchema) -> ModelSchema:
            try:
                model = self.store.update(model_id, payload)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if not model:
                raise HTTPException(status_code=404, detail="Model not found")
            return model

        @self.router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_model(model_id: int) -> None:
            try:
                deleted = self.store.delete(model_id)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if not deleted:
                raise HTTPException(status_code=404, detail="Model not found")

        @self.router.get(
            "/cameras/{camera_id}/models",
            response_model=CameraModelAssignmentListSchema,
        )
        async def list_camera_models(camera_id: int) -> CameraModelAssignmentListSchema:
            items = self.store.list_camera_models(camera_id)
            if items is None:
                raise HTTPException(status_code=404, detail="Camera not found")
            return CameraModelAssignmentListSchema(items=items)

        @self.router.put(
            "/cameras/{camera_id}/models",
            response_model=CameraModelAssignmentListSchema,
        )
        async def replace_camera_models(
            camera_id: int, payload: CameraModelsUpdateSchema
        ) -> CameraModelAssignmentListSchema:
            try:
                items = self.store.replace_camera_models(camera_id, payload.model_ids)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if items is None:
                raise HTTPException(status_code=404, detail="Camera not found")
            if self.camera_store is not None:
                camera = self.camera_store.get(camera_id)
                if camera:
                    try:
                        from src.streaming.stream_manager import get_stream_manager

                        manager = get_stream_manager()
                        if manager.is_running(camera_id):
                            manager.restart_stream(camera)
                    except RuntimeError:
                        pass
            return CameraModelAssignmentListSchema(items=items)
