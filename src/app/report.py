# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from pathlib import Path
from shutil import copy2 as shutil_copy2

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.app.database import BookmarksDatabase as bmd
from src.config import Config
from src.logs import SmartLogger
from src.utilities import Utilities as uts

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class ApplicationService:
    _log: SmartLogger = SmartLogger()

    @classmethod
    def _save_db_in_data(cls, cfg: Config) -> str | None:
        """
        Проверяет и/или копирует файл `places.sqlite` в папку `data` в текущем каталоге.
        """
        database_file: str = cfg.database_file

        path_source_database: Path | None = cfg.path_source_database
        path_data_folder: Path = Path.cwd() / "data"

        Path.mkdir(path_data_folder, exist_ok=True)

        if path_source_database is None:
            cls._log.warning(
                msg="Указан пустой путь для базы данных закладок.", pretty=True
            )
            if not (path_data_folder / database_file).is_file():
                err = "По указанному пути отсутствует файл базы данных закладок."
                cls._log.error(msg=err, pretty=True)
                return err
            cls._log.info(
                msg="Проверяется старый файл базы данных закладок.", pretty=True
            )
        else:
            try:
                shutil_copy2(path_source_database, path_data_folder / database_file)
            except FileNotFoundError:
                err = "По указанному пути отсутствует файл базы данных закладок."
                cls._log.error(msg=err, pretty=True)
                return err
            except Exception as err:
                err_msg: str = (
                    f"Произошла ошибка при копировании: {path_source_database}. "
                    f"Ошибка: {type(err)} {err}"
                )
                cls._log.error(msg=err_msg, pretty=True)
                return err_msg
        return None

    @classmethod
    async def save_bookmarks_report(
        cls, is_save_file: bool, cfg: Config | None = None
    ) -> tuple[str | None, Path | None, str | None]:
        """
        Копирует файл базы данных закладок Firefox, формирует отчёт и сохраняет его в файл.

        Логика:
        1. Проверяет и/или копирует файл `places.sqlite` в папку `data` в текущем каталоге.
        2. Вызывает метод `BookmarksDatabase.create_bookmarks_report` для формирования отчёта.
        3. Создаёт папку `docs` (если её нет) и записывает отчёт в файл `<report_file>.txt`.
        """
        if cfg is None:
            cfg = Config()

        report_file: str = cfg.report_file
        report_folder: str = cfg.report_folder
        path_report_folder: Path
        report_path: Path

        if err := cls._save_db_in_data(cfg=cfg):
            return None, None, err

        if not (bookmarks_report := await bmd.create_bookmarks_report(cfg=cfg)):
            err = "Указанная директория отсутствует в базе данных закладок."
            cls._log.warning(msg=err, pretty=True)
            return None, None, err

        if is_save_file:
            path_report_folder = Path.cwd() / report_folder
            report_path = path_report_folder / f"{report_file}.txt"

            Path.mkdir(path_report_folder, exist_ok=True)

            try:
                with report_path.open("w", encoding="utf-8") as result_file:
                    result_file.write(bookmarks_report)
            except Exception as err:
                err_msg: str = (
                    f"Не удалось сохранить отчёт в файл: {report_path}. "
                    f"Ошибка: {type(err)} {err}"
                )
                cls._log.error(msg=err_msg, pretty=True)
                return None, None, err_msg

            cls._log.info(
                msg=(
                    "Информация о количестве закладок в категориях "
                    f"сохранена в файл: {report_path.name}"
                ),
                pretty=True,
            )
            return bookmarks_report, report_path, None

        return bookmarks_report, None, None

    @staticmethod
    async def clear_report_files(cfg: Config = Config()) -> dict[str, int | tuple[str]]:
        """
        Асинхронно и безопасно очищает папку от файлов.
        Возвращает статистику по успешным удалениям и ошибкам.
        """
        return await uts.clearing_folder(clear_folder=cfg.report_folder)
