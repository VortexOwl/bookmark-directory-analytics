# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
import sys
from asyncio import gather as asyncio_gather
from asyncio import to_thread as asyncio_to_thread
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from logs import SmartLogger

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


@dataclass
class Utilities:
    _log = SmartLogger()

    @staticmethod
    def read_file_line_by_line(file_path: Path, encoding="utf-8") -> Iterator[str]:
        """
        Читает файл построчно, передавая данные в буфер по одной строке.

        Полезен при обработке файлов большого объёма.

        Args:
            file_path: Путь к файлу для чтения.
            encoding: Кодировка файла.

        Yields:
            Очередную строку файла без пробельных символов по краям.
        """
        with file_path.open("r", encoding=encoding) as file:
            for line in file:
                yield line.strip()

    @classmethod
    async def clearing_folder(
        cls,
        clear_folder: str,
        *,
        remove_files: bool = True,
        remove_subfolders: bool = True,
    ) -> dict[str, int | tuple[str, ...]]:
        """
        Асинхронно и безопасно очищает папку от файлов и/или подпапок,
        не удаляя саму директорию. Возвращает статистику по удалениям и ошибкам.

        :param clear_folder: путь к очищаемой папке (относительно cwd).
        :param remove_files: удалять файлы (и симлинки) в папке.
        :param remove_subfolders: удалять вложенные подпапки (рекурсивно).
        """
        if not remove_files and not remove_subfolders:
            name_err = (
                "Не указано, что удалять: remove_files и remove_subfolders выключены"
            )
            cls._log.warning(msg=name_err, pretty=True)
            return {"success": 0, "errors": 1, "names of errors": (name_err,)}

        path_clear_folder = Path.cwd() / clear_folder

        if not path_clear_folder.exists() or not path_clear_folder.is_dir():
            name_err = f"Путь не существует или не является папкой: {path_clear_folder}"
            cls._log.warning(msg=name_err, pretty=True)
            return {"success": 0, "errors": 1, "names of errors": (name_err,)}

        stats = {"success": 0, "errors": 0}
        names_err: set[str] = set()

        def _remove_entry(entry: Path) -> None:
            # Выполняется в отдельном потоке — не блокирует event loop
            if entry.is_dir() and not entry.is_symlink():
                rmtree(entry)
            else:
                entry.unlink(missing_ok=True)

        def _should_remove(entry: Path) -> bool:
            is_dir_entry = entry.is_dir() and not entry.is_symlink()
            return remove_subfolders if is_dir_entry else remove_files

        entries = [e for e in path_clear_folder.iterdir() if _should_remove(e)]

        async def _process(entry: Path) -> None:
            try:
                await asyncio_to_thread(_remove_entry, entry)
                stats["success"] += 1
            except PermissionError:
                name_err = f"Нет прав на удаление: {entry}"
                cls._log.error(msg=name_err, pretty=True)
                stats["errors"] += 1
                names_err.add(name_err)
            except FileNotFoundError:
                pass
            except Exception as err:
                name_err = f"Не удалось удалить {entry}. Ошибка: {err}"
                cls._log.exception(msg=name_err, pretty=True)
                stats["errors"] += 1
                names_err.add(name_err)

        await asyncio_gather(*(_process(entry) for entry in entries))

        stats["names of errors"] = tuple(names_err)
        cls._log.debug(
            msg=(
                f"В директории {clear_folder} удалены: "
                f"{'файлы' if remove_files else ''}"
                f"{' и ' if remove_files and remove_subfolders else ''}"
                f"{'подпапки' if remove_subfolders else ''}."
            ),
            pretty=True,
        )
        cls._log.debug(msg=f"Сводка выполнения очистки:\n{stats}", pretty=True)
        return stats

    @staticmethod
    def resource_path(relative_path: str | Path) -> Path:
        """
        Возвращает абсолютный путь к ресурсу приложения.

        Args:
            relative_path: Относительный путь к ресурсу от корневой
                директории проекта или каталога собранного приложения.

        Returns:
            Абсолютный путь к ресурсу.
        """
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parents[2]

        return base_path / relative_path