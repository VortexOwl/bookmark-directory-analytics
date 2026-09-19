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


class BookmarksDatabase:
    _log: SmartLogger = SmartLogger()
    _ALLOWED_COLUMNS: set = {"id", "id, title", "guid, title"}

    @classmethod
    async def _connect_database(cls, cfg: Config) -> Connection:
        """
        Открывает и возвращает асинхронное соединение с БД.
        Закрытие соединения — ответственность вызывающего кода.
        """
        bookmarks_folder: str = cfg.bookmarks_folder

        conn = await connect(cfg.path_data_folder)
        cls._log.debug(msg="Подключение к БД прошло успешно.", pretty=True)
        cls._log.info(msg=f'Начата проверка закладок папки "{bookmarks_folder}"', pretty=True)
        return conn

    @classmethod
    async def _fetch_all(
        cls, conn: Connection, columns: str, parent_id: int, bookmark_type: int
    ) -> list[tuple]:
        """
        Выполняет запрос к moz_bookmarks и возвращает все строки результата.
        """
        if columns not in cls._ALLOWED_COLUMNS:
            raise ValueError(f"Недопустимое значение columns: {columns!r}")

        async with conn.execute(
            f"SELECT {columns} FROM moz_bookmarks WHERE parent = ? AND type = ?",
            (parent_id, bookmark_type),
        ) as cursor:
            return await cursor.fetchall()

    @classmethod
    async def bookmarks_check(
        cls, conn: Connection, cfg: Config, id_initial_folder: int
    ) -> str:
        """
        Формирует отчёт по закладкам для указанной папки.
        """
        bookmarks_folder: str = cfg.bookmarks_folder
        category_reports: list[str] = []
        separator: str = f"\n{'-' * 93}\n"

        bookmarks = await cls._fetch_all(
            conn=conn, columns="id", parent_id=id_initial_folder, bookmark_type=1
        )
        categories = await cls._fetch_all(
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
            bookmarks_in_category = await cls._fetch_all(
                conn=conn, columns="guid, title", parent_id=id_category, bookmark_type=1
            )
            catalogs_in_category = await cls._fetch_all(
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

    @classmethod
    async def create_bookmarks_report(cls, cfg: Config | None = None) -> str:
        """
        Создаёт и возвращает отчёт по закладкам из заданной папки.

        Открывает соединение с БД, находит папку закладок по имени из конфигурации
        и вызывает метод `bookmarks_check`.

        В конце гарантированно закрывает соединение.
        """
        if cfg is None:
            cfg = Config()

        bookmarks_folder: str = cfg.bookmarks_folder
        result_check: str = ""
        conn: Connection | None = None

        try:
            conn = await cls._connect_database(cfg=cfg)

            async with conn.execute(
                "SELECT id FROM moz_bookmarks WHERE title = ?",
                (bookmarks_folder,),
            ) as cursor:
                initial_folder = await cursor.fetchone()

            if initial_folder:
                result_check = await cls.bookmarks_check(
                    cfg=cfg, conn=conn, id_initial_folder=initial_folder[0]
                )
            else:
                cls._log.warning(msg=f'Папка "{bookmarks_folder}" не найдена', pretty=True)

        finally:
            if conn is not None:
                await conn.close()
                cls._log.debug(msg="Соединение с БД было закрыто.", pretty=True)

        return result_check
