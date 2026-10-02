# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
import sys
from asyncio import to_thread as asyncio_to_thread
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

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
        cls, clear_folder: str | Path
    ) -> dict[str, int | tuple[str]]:
        """
        Асинхронно и безопасно очищает папку от файлов.

        Args:
            clear_folder: Путь к папке, которую необходимо очистить.

        Returns:
            Статистика выполнения очистки. Содержит количество успешно
            удалённых файлов, количество ошибок и имена ошибок.
        """
        path_clear_folder = Path.cwd() / clear_folder

        if not path_clear_folder.exists() or not path_clear_folder.is_dir():
            name_err = f"Путь не существует или не является папкой: {path_clear_folder}"
            cls._log.warning(msg=name_err, pretty=True)
            return {"success": 0, "errors": 1, "names of errors": (name_err)}

        stats = {"success": 0, "errors": 0}
        names_err = set()

        for file_name in path_clear_folder.iterdir():
            try:
                if file_name.is_file():
                    await asyncio_to_thread(file_name.unlink, missing_ok=True)
                    stats["success"] += 1

            except PermissionError:
                name_err = f"Нет прав на удаление файла: {file_name}"
                cls._log.error(msg=name_err, pretty=True)
                stats["errors"] += 1
                names_err.add(name_err)

            except FileNotFoundError:
                pass

            except Exception as err:
                name_err = f"Не удалось удалить {file_name}. Ошибка: {err}"
                cls._log.exception(msg=name_err, pretty=True)
                stats["errors"] += 1
                names_err.add(name_err)

        stats["names of errors"] = tuple(names_err)
        cls._log.info(
            msg=f"В директории {clear_folder} была проведена очистка от файлов.",
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