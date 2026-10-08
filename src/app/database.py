# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from shutil import copy2 as shutil_copy2

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from aiosqlite import Connection, connect

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.config import Config
from src.logs import SmartLogger

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class DatabaseDeployer:
    """
    Копирует файл базы данных закладок в директорию проекта.
    """

    def __init__(
        self,
        cfg: Config | None = None,
        log: SmartLogger | None = None,
    ) -> None:
        """
        Инициализирует сервис деплоя базы данных закладок.

        Args:
            cfg: Конфигурация приложения. Если не передана,
                используется конфигурация по умолчанию.
            log: Логгер приложения. Если не передан,
                создаётся новый экземпляр.
        """
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

    def prepare_db_file(self, cfg: Config | None = None) -> str | None:
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

        patch_data_folder.mkdir(exist_ok=True)

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


class BookmarkDatabaseHandler:
    """
    Предоставляет доступ к базе данных закладок.
    """

    def __init__(
        self, log: SmartLogger | None = None, cfg: Config | None = None
    ) -> None:
        """
        Инициализирует объект для работы с базой данных закладок.

        Args:
            log: Экземпляр логгера. Если не указан, создаётся новый.
            cfg: Конфигурация приложения. Если не указана, создаётся новая.
        """
        self._cfg = cfg if cfg is not None else Config()
        self._log = log if log is not None else SmartLogger()
        self._ALLOWED_COLUMNS: set = {"id", "id, title", "guid, title"}

    async def _connect_to_database(self, cfg: Config) -> Connection:
        """
        Открывает асинхронное соединение с базой данных.

        Args:
            cfg: Конфигурация с путём к файлу базы данных.

        Returns:
            Асинхронное соединение с базой данных.

        Notes:
            Закрытие соединения является ответственностью вызывающего кода.
        """
        bookmarks_folder: str = cfg.bookmarks_folder

        conn = await connect(cfg.path_data_file)
        self._log.debug(msg="Подключение к БД прошло успешно.", pretty=True)
        self._log.info(
            msg=f'Начата проверка закладок папки "{bookmarks_folder}"', pretty=True
        )
        return conn

    async def _fetch_bookmark_entries(
        self, conn: Connection, columns: str, parent_id: int, bookmark_type: int
    ) -> list[tuple]:
        """
        Выполняет запрос к таблице `moz_bookmarks`.

        Args:
            conn: Открытое соединение с базой данных.
            columns: Список столбцов для получения.
            parent_id: Идентификатор родительской папки.
            bookmark_type: Тип записи: закладка или папка.

        Returns:
            Все строки результата запроса.

        Raises:
            ValueError: Если передан столбец, отсутствующий в списке
                разрешённых значений.
        """
        if columns not in self._ALLOWED_COLUMNS:
            raise ValueError(f"Недопустимое значение columns: {columns!r}")

        async with conn.execute(
            f"SELECT {columns} FROM moz_bookmarks WHERE parent = ? AND type = ?",
            (parent_id, bookmark_type),
        ) as cursor:
            return await cursor.fetchall()

    async def _build_bookmarks_report(
        self, conn: Connection, cfg: Config, id_initial_folder: int
    ) -> str:
        """
        Формирует отчёт по закладкам для указанной папки.

        Args:
            conn: Открытое соединение с базой данных.
            cfg: Конфигурация приложения.
            id_initial_folder: Идентификатор исходной папки закладок.

        Returns:
            Текстовый отчёт о закладках и вложенных папках.
        """
        bookmarks_folder: str = cfg.bookmarks_folder
        category_reports: list[str] = []
        separator: str = f"\n{'-' * 93}\n"

        bookmarks = await self._fetch_bookmark_entries(
            conn=conn, columns="id", parent_id=id_initial_folder, bookmark_type=1
        )
        categories = await self._fetch_bookmark_entries(
            conn=conn, columns="id, title", parent_id=id_initial_folder, bookmark_type=2
        )

        if categories:
            category_reports.append(
                "\n".join(
                    [
                        f"Initial catalog: {bookmarks_folder}",
                        f"bookmarks: {len(bookmarks)}",
                        f"catalogs: {len(categories)}",
                    ]
                )
            )
        else:
            category_reports.append(
                "\n".join(
                    [
                        f"Initial catalog: {bookmarks_folder}",
                        f"bookmarks: {len(bookmarks)}",
                    ]
                )
            )

        for id_category, title_category in categories:
            bookmarks_in_category = await self._fetch_bookmark_entries(
                conn=conn, columns="guid, title", parent_id=id_category, bookmark_type=1
            )
            catalogs_in_category = await self._fetch_bookmark_entries(
                conn=conn, columns="guid, title", parent_id=id_category, bookmark_type=2
            )

            if catalogs_in_category:
                category_reports.append(
                    "\n".join(
                        [
                            title_category,
                            f"bookmarks: {len(bookmarks_in_category)}",
                            f"catalogs: {len(catalogs_in_category)}",
                        ]
                    )
                )
            else:
                category_reports.append(
                    "\n".join(
                        [
                            title_category,
                            f"bookmarks: {len(bookmarks_in_category)}",
                        ]
                    )
                )

        return separator.join(category_reports)

    async def generate_bookmarks_report(self, cfg: Config | None = None) -> str:
        """
        Создаёт отчёт по закладкам из заданной папки.

        Открывает соединение с базой данных, находит папку закладок
        по имени из конфигурации и вызывает метод `_build_bookmarks_report`.

        Args:
            cfg: Конфигурация приложения. Если не указана, создаётся новая.

        Returns:
            Текстовый отчёт по закладкам. Если исходная папка не найдена,
            возвращается пустая строка.

        Notes:
            Соединение с базой данных гарантированно закрывается
            после завершения операции.
        """
        if cfg is None:
            cfg = Config()

        bookmarks_folder: str = cfg.bookmarks_folder
        result_check: str = ""
        conn: Connection | None = None

        try:
            conn = await self._connect_to_database(cfg=cfg)

            async with conn.execute(
                "SELECT id FROM moz_bookmarks WHERE title = ?",
                (bookmarks_folder,),
            ) as cursor:
                initial_folder = await cursor.fetchone()

            if initial_folder:
                result_check = await self._build_bookmarks_report(
                    cfg=cfg, conn=conn, id_initial_folder=initial_folder[0]
                )
            else:
                self._log.warning(
                    msg=f'Папка "{bookmarks_folder}" не найдена', pretty=True
                )

        finally:
            if conn is not None:
                await conn.close()
                self._log.debug(msg="Соединение с БД было закрыто.", pretty=True)

        return result_check
