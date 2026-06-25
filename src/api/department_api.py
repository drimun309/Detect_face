"""Department management API."""

from fastapi import APIRouter, HTTPException, status

from src.schema.department_schema import (
    DepartmentCreateSchema,
    DepartmentListSchema,
    DepartmentSchema,
    DepartmentUpdateSchema,
)
from src.services.department_store import DepartmentStore


class DepartmentApi:
    def __init__(self, store: DepartmentStore) -> None:
        self.router = APIRouter()
        self.store = store
        self.setup()

    def setup(self) -> None:
        @self.router.get("/departments", response_model=DepartmentListSchema)
        async def list_departments() -> DepartmentListSchema:
            return DepartmentListSchema(items=self.store.list())

        @self.router.post(
            "/departments",
            response_model=DepartmentSchema,
            status_code=status.HTTP_201_CREATED,
        )
        async def create_department(payload: DepartmentCreateSchema) -> DepartmentSchema:
            try:
                return self.store.create(payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        @self.router.get("/departments/{department_id}", response_model=DepartmentSchema)
        async def get_department(department_id: int) -> DepartmentSchema:
            dept = self.store.get(department_id)
            if not dept:
                raise HTTPException(status_code=404, detail="Department not found")
            return dept

        @self.router.put("/departments/{department_id}", response_model=DepartmentSchema)
        async def update_department(
            department_id: int, payload: DepartmentUpdateSchema
        ) -> DepartmentSchema:
            try:
                dept = self.store.update(department_id, payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if not dept:
                raise HTTPException(status_code=404, detail="Department not found")
            return dept

        @self.router.delete(
            "/departments/{department_id}",
            status_code=status.HTTP_204_NO_CONTENT,
        )
        async def delete_department(department_id: int) -> None:
            if not self.store.delete(department_id):
                raise HTTPException(status_code=404, detail="Department not found")
