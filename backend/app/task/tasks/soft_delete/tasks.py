from celery import shared_task

from backend.app.task.service.soft_delete_service import soft_delete_service
from backend.common.log import log


@shared_task
async def delete_soft_deleted_records() -> str:
    """物理删除超过保留期的软删除记录。"""
    counts = await soft_delete_service.cleanup()
    result = f'Purged {sum(counts.values())} soft-deleted records; tables: {counts}'
    log.info(result)
    return result
