# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from pathlib import Path
from shutil import copy2 as shutil_copy2

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.app.database import BookmarkDatabaseHandler, DatabaseDeployer
from src.config import Config
from src.logs import SmartLogger
from src.utilities import Utilities as uts

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class ApplicationService:
    class ClearReportService:
        """
        Очищает директорию для хранения отчетов от файлов.
        """
        def __init__(self, cfg: Config | None = None):
            """
            Инициализирует сервис удаления отчётов.

            Args:
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация по умолчанию.
            """
            self._cfg = cfg if cfg is not None else Config()

        async def cleanup(
            self, report_files_directory: str | Path | None = None
        ) -> dict[str, int | tuple[str]]:
            """
            Очищает директорию временных файлов.

            Args:
                report_files_directory: Директория отчетов. Если не передана,
                    используется директория отчетов из конфигурации.

            Returns:
                Словарь со статистикой удаления: количеством успешно
                удалённых файлов и количеством ошибок.
            """
            if report_files_directory is None:
                report_files_directory = self._cfg.report_folder
            return await uts.clearing_folder(clear_folder=report_files_directory)

    class ReportService:
        """
        Формирует отчёты по закладкам.
        """
        def __init__(
            self,
            bdh: BookmarkDatabaseHandler | None = None,
            cfg: Config | None = None,
            dd: DatabaseDeployer | None = None,
            log: SmartLogger | None = None,
        ) -> None:
            """
            Инициализирует сервис формирования отчётов.

            Args:
                bdh: Сервис обработки базы данных закладок.
                    Если не передан, создаётся новый экземпляр.
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация по умолчанию.
                dd: Сервис деплоя базы данных закладок.
                    Если не передан, создаётся новый экземпляр.
                log: Логгер приложения. Если не передан,
                    создаётся новый экземпляр.
            """
            self._bdh = bdh if bdh is not None else BookmarkDatabaseHandler()
            self._cfg = cfg if cfg is not None else Config()
            self._dd = dd if dd is not None else DatabaseDeployer()
            self._log = log if log is not None else SmartLogger()

        async def generate_report(
            self,
            is_save_file: bool,
            bdh: BookmarkDatabaseHandler | None = None,
            cfg: Config | None = None,
            dd: DatabaseDeployer | None = None,
        ) -> tuple[str | None, Path | None, str | None]:
            """
            Формирует отчёт по закладкам и при необходимости сохраняет его в файл.

            Метод проверяет или копирует файл базы данных Firefox,
            формирует отчёт по закладкам и сохраняет результат в файл,
            если это указано в параметре `is_save_file`.

            Args:
                is_save_file: Нужно ли сохранить сформированный отчёт в файл.
                bdh: Сервис работы с базой данных закладок. Если не передан,
                    используется сервис, заданный при инициализации.
                cfg: Конфигурация приложения. Если не передана,
                    используется конфигурация сервиса.
                dd: Сервис деплоя базы данных закладок. Если не передан,
                    используется сервис, заданный при инициализации.

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
            if bdh is None:
                bdh = self._bdh
            if dd is None:
                dd = self._dd

            if err := dd.prepare_db_file(cfg=cfg):
                return None, None, err

            if not (bookmarks_report := await bdh.generate_bookmarks_report(cfg=cfg)):
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
