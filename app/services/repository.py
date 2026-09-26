import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import UploadFile

from app.config import settings


GITHUB_REPO_PATTERN = re.compile(
    r"^(?:https?://)?github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)"
    r"/(?P<repo>[A-Za-z0-9_.-]+)"
    r"/?$",
    re.IGNORECASE,
)


class RepositoryService:
    def __init__(self):
        self.base_dir = Path(tempfile.gettempdir()) / "ripple"
        self.base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def save_upload(
        self,
        upload: UploadFile,
    ) -> Path:
        if not upload.filename:
            raise ValueError(
                "Repository archive has no filename."
            )

        if not upload.filename.lower().endswith(".zip"):
            raise ValueError(
                "Ripple accepts .zip repository archives."
            )

        repository_id = str(uuid4())

        repository_dir = self.base_dir / repository_id
        archive_path = repository_dir / "repository.zip"
        extracted_dir = repository_dir / "source"

        repository_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            max_bytes = (
                settings.MAX_UPLOAD_MB
                * 1024
                * 1024
            )

            total = 0

            with archive_path.open("wb") as output:
                while True:
                    chunk = await upload.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    total += len(chunk)

                    if total > max_bytes:
                        raise ValueError(
                            f"Repository exceeds "
                            f"{settings.MAX_UPLOAD_MB}MB limit."
                        )

                    output.write(chunk)

            extracted_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._safe_extract(
                archive_path,
                extracted_dir,
            )

            return self._find_project_root(
                extracted_dir
            )

        except Exception:
            shutil.rmtree(
                repository_dir,
                ignore_errors=True,
            )
            raise

    async def save_github_repository(
        self,
        repository_url: str,
        branch: str | None = None,
    ) -> Path:
        parsed = self.parse_github_url(
            repository_url
        )

        if not parsed:
            raise ValueError(
                "Enter a valid GitHub repository URL, "
                "for example https://github.com/owner/repository."
            )

        owner = parsed["owner"]
        repo = parsed["repo"]

        repository_id = str(uuid4())

        repository_dir = self.base_dir / repository_id
        archive_path = repository_dir / "repository.zip"
        extracted_dir = repository_dir / "source"

        repository_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            download_url = self._github_download_url(
                owner=owner,
                repo=repo,
                branch=branch,
            )

            await self._download_archive(
                download_url,
                archive_path,
            )

            extracted_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._safe_extract(
                archive_path,
                extracted_dir,
            )

            return self._find_project_root(
                extracted_dir
            )

        except httpx.HTTPStatusError as exc:
            shutil.rmtree(
                repository_dir,
                ignore_errors=True,
            )

            if exc.response.status_code == 404:
                raise ValueError(
                    "GitHub repository or branch was not found."
                )

            raise ValueError(
                "GitHub could not provide this repository."
            )

        except httpx.HTTPError:
            shutil.rmtree(
                repository_dir,
                ignore_errors=True,
            )

            raise ValueError(
                "Unable to connect to GitHub."
            )

        except Exception:
            shutil.rmtree(
                repository_dir,
                ignore_errors=True,
            )
            raise

    @staticmethod
    def parse_github_url(
        repository_url: str,
    ) -> dict[str, str] | None:
        if not repository_url:
            return None

        cleaned = repository_url.strip()

        match = GITHUB_REPO_PATTERN.match(
            cleaned
        )

        if not match:
            return None

        return {
            "owner": match.group("owner"),
            "repo": match.group("repo").removesuffix(
                ".git"
            ),
        }

    @staticmethod
    def _github_download_url(
        owner: str,
        repo: str,
        branch: str | None,
    ) -> str:
        base_url = f"https://github.com/{owner}/{repo}"

        if branch:
            encoded_branch = quote(
                branch.strip(),
                safe="",
            )

            return (
                f"{base_url}/archive/refs/heads/"
                f"{encoded_branch}.zip"
            )

        return f"{base_url}/archive/HEAD.zip"

    async def _download_archive(
        self,
        url: str,
        destination: Path,
    ) -> None:
        max_bytes = (
            settings.MAX_UPLOAD_MB
            * 1024
            * 1024
        )

        total = 0

        timeout = httpx.Timeout(
            60.0,
            connect=15.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        ) as client:

            async with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": (
                        "Ripple-Developer-Intelligence"
                    ),
                    "Accept": "application/zip",
                },
            ) as response:

                response.raise_for_status()

                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes(
                        1024 * 1024
                    ):
                        total += len(chunk)

                        if total > max_bytes:
                            raise ValueError(
                                f"Repository exceeds "
                                f"{settings.MAX_UPLOAD_MB}MB limit."
                            )

                        output.write(chunk)

    def _safe_extract(
        self,
        archive_path: Path,
        destination: Path,
    ) -> None:
        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            members = archive.infolist()

            if len(members) > settings.MAX_FILES:
                raise ValueError(
                    "Repository contains too many files."
                )

            destination_resolved = (
                destination.resolve()
            )

            for member in members:
                member_path = (
                    destination / member.filename
                ).resolve()

                try:
                    member_path.relative_to(
                        destination_resolved
                    )
                except ValueError:
                    raise ValueError(
                        "Unsafe archive path detected."
                    )

            archive.extractall(
                destination
            )

    def _find_project_root(
        self,
        extracted: Path,
    ) -> Path:
        children = [
            item
            for item in extracted.iterdir()
            if item.name != "repository.zip"
        ]

        if (
            len(children) == 1
            and children[0].is_dir()
        ):
            return children[0]

        return extracted