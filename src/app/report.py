# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from pathlib import Path
from shutil import copy2 as shutil_copy2

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.app.database import BookmarksDatabase
from src.config import Config
from src.logs import SmartLogger
from src.utilities import Utilities as uts

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class ApplicationService:
    class ClearReportService:
        """Очищает директорию для хранения отчетов от файлов."""

        def __init__(self, cfg: Config | None = None):
            """
            Инициализирует сервис удаления отчётов.

            Args:
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация по умолчанию.
            """
            self._cfg = cfg if cfg is not None else Config()

        async def clear_report_directory(self) -> dict[str, int | tuple[str]]:
            """
            Удаляет файлы из каталога отчётов.

            Returns:
                Словарь со статистикой удаления: количеством успешно
                удалённых файлов и количеством ошибок.
            """
            return await uts.clearing_folder(clear_folder=self._cfg.report_folder)

    class ReportService:
        """Формирует отчёты по закладкам."""

        def __init__(
            self,
            bmd: BookmarksDatabase | None = None,
            cfg: Config | None = None,
            log: SmartLogger | None = None,
        ) -> None:
            """
            Инициализирует сервис формирования отчётов.

            Args:
                bmd: Сервис работы с базой данных закладок.
                    Если не передан, создаётся новый экземпляр.
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация по умолчанию.
                log: Логгер приложения. Если не передан,
                    создаётся новый экземпляр.
            """

            self._bmd = bmd if bmd is not None else BookmarksDatabase()
            self._cfg = cfg if cfg is not None else Config()
            self._log = log if log is not None else SmartLogger()

        def _get_db_missing_error(self) -> str:
            """
            Формирует сообщение об отсутствии файла базы данных закладок.

            Returns:
                Сообщение об ошибке отсутствующего файла базы данных.
            """
            err = "По указанному пути отсутствует файл базы данных закладок."
            self._log.error(msg=err, pretty=True)
            return err

        def _prepare_db_file(self, cfg: Config | None = None) -> str | None:
            """
            Проверяет наличие базы данных закладок и копирует её в папку данных.

            Args:
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация сервиса.

            Returns:
                Сообщение об ошибке, если файл базы данных не найден
                или копирование завершилось с ошибкой. В случае успеха
                возвращается `None`.
            """
            if cfg is None:
                cfg = self._cfg

            path_source_database: Path | None = cfg.path_source_database
            patch_data_folder: Path = cfg.patch_data_folder
            path_data_file: Path = cfg.path_data_file

            Path.mkdir(patch_data_folder, exist_ok=True)

            if path_source_database is None:
                self._log.warning(
                    msg="Указан пустой путь для базы данных закладок.", pretty=True
                )
                if not (path_data_file).is_file():
                    return self._get_db_missing_error()
                self._log.info(
                    msg="Проверяется старый файл базы данных закладок.", pretty=True
                )
            else:
                try:
                    shutil_copy2(path_source_database, path_data_file)
                except FileNotFoundError:
                    return self._get_db_missing_error()
                except Exception as err:
                    err_msg: str = (
                        f"Произошла ошибка при копировании: {path_source_database}. "
                        f"Ошибка: {type(err)} {err}"
                    )
                    self._log.error(msg=err_msg, pretty=True)
                    return err_msg
            return None

        async def generate_report(
            self,
            is_save_file: bool,
            bmd: BookmarksDatabase | None = None,
            cfg: Config | None = None,
        ) -> tuple[str | None, Path | None, str | None]:
            """
            Формирует отчёт по закладкам и при необходимости сохраняет его в файл.

            Метод проверяет или копирует файл базы данных Firefox,
            формирует отчёт по закладкам и сохраняет результат в файл,
            если это указано в параметре `is_save_file`.

            Args:
                is_save_file: Нужно ли сохранить сформированный отчёт в файл.
                bmd: Сервис работы с базой данных закладок. Если не передан,
                    используется сервис, заданный при инициализации.
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация сервиса.

            Returns:
                Кортеж из трёх элементов:
                - текст отчёта или `None`;
                - путь к сохранённому файлу или `None`;
                - сообщение об ошибке или `None`.

            Notes:
                При сохранении отчёта создаётся директория,
                указанная в конфигурации приложения.
            """
            if cfg is None:
                cfg = self._cfg
            if bmd is None:
                bmd = self._bmd

            if err := self._prepare_db_file(cfg=cfg):
                return None, None, err

            if not (bookmarks_report := await bmd.generate_bookmarks_report(cfg=cfg)):
                err = "Указанная директория отсутствует в базе данных закладок."
                self._log.warning(msg=err, pretty=True)
                return None, None, err

            if is_save_file:
                cfg.path_report_folder.mkdir(exist_ok=True)

                try:
                    with cfg.path_report_file.open(
                        "w", encoding="utf-8"
                    ) as result_file:
                        result_file.write(bookmarks_report)

                except Exception as err:
                    err_msg: str = (
                        f"Не удалось сохранить отчёт в файл: {cfg.path_report_file}. "
                        f"Ошибка: {type(err)} {err}"
                    )
                    self._log.error(msg=err_msg, pretty=True)
                    return None, None, err_msg

                self._log.info(
                    msg=(
                        "Информация о количестве закладок в категориях "
                        f"сохранена в файл: {cfg.path_report_file.name}"
                    ),
                    pretty=True,
                )
                return bookmarks_report, cfg.path_report_file, None

            return bookmarks_report, None, None
