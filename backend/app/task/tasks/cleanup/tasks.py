from celery import shared_task

from backend.plugin.files.service.cleanup_service import cleanup_service


@shared_task
async def delete_orphan_files() -> str:
    """回收超过保护期且无引用的临时文件、失效记录和过期分片。"""
    result = await cleanup_service.cleanup()
    return (
        f'Deleted {result.deleted_records} orphaned file records; '
        f'expired sessions: {result.expired_sessions}; failed files: {result.failed_files}; '
        f'untracked files (retained): {result.untracked_files}'
    )


@shared_task
async def delete_untracked_storage() -> str:
    """每年清理超过上传保护期的无记录文件，及不限制目录年龄的空目录。"""
    result = await cleanup_service.cleanup_storage()
    return (
        f'Deleted {result.deleted_files} untracked files; '
        f'empty directories: {result.deleted_directories}; failed entries: {result.failed_files}; '
        f'retained known files: {result.retained_known_files}; '
        f'retained recent files: {result.retained_recent_files}'
    )
