from fastapi import APIRouter

from app.api.routes import graphs, repositories
from app.mcp.activity import get_mcp_activity


router = APIRouter(
    prefix="/bob",
    tags=["bob"],
)


@router.get("/activity")
def get_bob_activity():
    repository_id = (
        next(reversed(repositories))
        if repositories
        else None
    )

    repository = (
        repositories.get(repository_id)
        if repository_id
        else None
    )

    return {
        "status": "connected" if repository_id else "waiting",
        "repository": (
            {
                "id": repository_id,
                "name": repository.name,
            }
            if repository
            else None
        ),
        "events": get_mcp_activity(),
    }