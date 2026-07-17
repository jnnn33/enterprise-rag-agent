from app.repositories.workspace import WorkspaceRepository


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def list_work_items(self):
        return self._repository.list_work_items()
