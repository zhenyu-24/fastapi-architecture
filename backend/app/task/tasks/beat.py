from typing import Any

from celery.schedules import schedule

from backend.app.task.utils.tzcrontab import TzAwareCrontab


def get_local_beat_schedule() -> dict[str, dict[str, Any]]:
    """获取本地 Celery beat 任务配置"""
    # 参考：https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
    return {
        '测试同步任务': {
            'task': 'task_demo',
            'schedule': schedule(30),
        },
        '测试异步任务': {
            'task': 'task_demo_async',
            'schedule': TzAwareCrontab('1'),
        },
        '测试传参任务': {
            'task': 'task_demo_params',
            'schedule': TzAwareCrontab('1'),
            'args': ['你好，'],
            'kwargs': {'world': '世界'},
        },
        '清理操作日志': {
            'task': 'backend.app.task.tasks.db_log.tasks.delete_db_opera_log',
            'schedule': TzAwareCrontab('0', '0', day_of_week='6'),
        },
        '清理登录日志': {
            'task': 'backend.app.task.tasks.db_log.tasks.delete_db_login_log',
            'schedule': TzAwareCrontab('0', '0', day_of_month='15'),
        },
        '清理孤立文件': {
            'task': 'backend.app.task.tasks.cleanup.tasks.delete_orphan_files',
            'schedule': TzAwareCrontab('0', '3', day_of_week='0'),
        },
        '年度清理存储冗余文件': {
            'task': 'backend.app.task.tasks.cleanup.tasks.delete_untracked_storage',
            'schedule': TzAwareCrontab('0', '4', day_of_month='1', month_of_year='1'),
        },
        '清理软删除数据': {
            'task': 'backend.app.task.tasks.soft_delete.tasks.delete_soft_deleted_records',
            'schedule': TzAwareCrontab('30', '3'),
        },
    }
