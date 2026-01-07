from fastapi import HTTPException, status


def _settings_repo_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings persistence is disabled; use settings_service instead.",
    )


async def create_settings(*args, **kwargs):
    _settings_repo_disabled()


async def get_settings(*args, **kwargs):
    _settings_repo_disabled()


async def get_settingss(*args, **kwargs):
    _settings_repo_disabled()


async def update_settings(*args, **kwargs):
    _settings_repo_disabled()


async def delete_settings(*args, **kwargs):
    _settings_repo_disabled()
