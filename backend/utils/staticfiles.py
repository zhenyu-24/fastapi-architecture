import os

from pathlib import Path

from starlette.staticfiles import StaticFiles


class RestrictedStaticFiles(StaticFiles):
    """静态资源服务排除需要通过下载接口访问的目录"""

    def __init__(self, *, directory: Path, excluded_directories: tuple[Path, ...]) -> None:
        super().__init__(directory=directory)
        self.excluded_directories = tuple(path.resolve() for path in excluded_directories)

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        """
        按真实路径排除受保护目录，阻止编码、大小写和符号链接绕过

        :param path: 静态资源相对路径
        :return:
        """
        full_path, stat_result = super().lookup_path(path)
        if full_path and any(Path(full_path).is_relative_to(root) for root in self.excluded_directories):
            return '', None
        return full_path, stat_result
