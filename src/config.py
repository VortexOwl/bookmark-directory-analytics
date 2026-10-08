# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
import sys
from pathlib import Path
from platform import system

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class ServerConfig(BaseSettings):
    """
    Конфигурация uvicorn.

    Attributes:
        host: Хост для запуска сервера.
        port: Порт для запуска сервера.
        is_reload: Включает автоматическую перезагрузку сервера.
        access_log: Включает журналирование запросов.
    """

    model_config = SettingsConfigDict(env_prefix="SERVER_")
    host: str = "127.0.0.1"
    port: int = 8000
    is_reload: bool = not getattr(sys, "frozen", False)
    access_log: bool = not getattr(sys, "frozen", False)

    @model_validator(mode="before")
    @classmethod
    def detect_docker_env(cls, data: dict) -> dict:
        """
        Настраивает параметры сервера при запуске в Docker.

        Args:
            data: Данные конфигурации.

        Returns:
            Обновлённые данные конфигурации.
        """
        if Path("/.dockerenv").exists():
            if "host" not in data:
                data["host"] = "0.0.0.0"
            if "is_reload" not in data:
                data["is_reload"] = False

        return data


class Config(BaseSettings):
    """
    Конфигурация для проведения анализа директории закладок браузера.

    Attributes:
        log_level: Уровень журналирования приложения.
        is_open_webbrowser: Включает открытие веб-браузера.
        _default_profile_pattern: Шаблон для поиска профиля браузера
            по умолчанию.
        bookmarks_folder: Название каталога с закладками.
        browser: Название браузера.
        browser_folder: Название каталога браузера в домашней директории.
        custom_name_browser_profile: Имя пользовательского профиля браузера.
        custom_name_report_file: Пользовательское имя файла отчёта.
        database_file: Имя файла базы данных браузера.
        data_folder: Название каталога для данных приложения.
        report_folder: Название каталога для отчётов.
    """

    model_config = SettingsConfigDict(env_prefix="APP_")
    log_level: int = 20 if getattr(sys, "frozen", False) else 10
    is_open_webbrowser: bool = True
    _default_profile_pattern: str = "*.default*"
    bookmarks_folder: str = "KDE Store"
    browser: str = "Floorp"
    browser_folder: str = ".floorp"
    custom_name_browser_profile: str | None = None
    custom_name_report_file: str | None = None
    database_file: str = "places.sqlite"
    data_folder: str = "data"
    report_folder: str = "report"

    @property
    def patch_data_folder(self) -> Path:
        """
        Возвращает путь к папке с данными.

        Returns:
            Путь к папке с данными.
        """
        return Path(self.data_folder)

    @property
    def path_data_file(self) -> Path:
        """
        Возвращает путь к файлу базы данных.

        Returns:
            Путь к файлу базы данных.
        """
        return self.patch_data_folder / self.database_file

    @property
    def name_report_file(self) -> str:
        """
        Возвращает имя файла отчёта без расширения.

        Returns:
            Пользовательское или сгенерированное имя файла отчёта.
        """
        return (
            f"Bookmarks {self.bookmarks_folder}"
            if self.custom_name_report_file is None
            else self.custom_name_report_file
        )

    @property
    def path_report_folder(self) -> Path:
        """
        Возвращает путь к папке с отчётами.

        Returns:
            Путь к папке с отчётами.
        """
        return Path(self.report_folder)

    @property
    def path_report_file(self) -> Path:
        """
        Возвращает полный путь к текстовому файлу отчёта.

        Returns:
            Путь к файлу отчёта.
        """
        return self.path_report_folder / f"{self.name_report_file}.txt"

    @property
    def is_docker(self) -> bool:
        """
        Проверяет, запущено ли приложение в Docker.

        Returns:
            ``True``, если приложение запущено в Docker, иначе ``False``.
        """
        return Path("/.dockerenv").exists()

    @property
    def path_browser_profile(self) -> Path | None:
        """
        Возвращает путь к профилю браузера.

        Путь определяется в зависимости от операционной системы и настроек
        браузера. Если пользовательский профиль не задан, используется первый
        найденный профиль, соответствующий шаблону профиля по умолчанию.

        Returns:
            Путь к профилю браузера или ``None``, если операционная система
            не поддерживается либо профиль не найден.
        """
        sys_name = system()
        path_user: Path = Path.home()
        path_browser: Path = Path(self.browser)
        path_browser_folder: Path = Path(self.browser_folder)
        path_profiles: Path

        if sys_name == "Windows":
            path_browser = Path("AppData") / "Roaming" / path_browser / "Profiles"
        elif sys_name == "Linux":
            path_browser = path_browser_folder
        else:
            return None

        path_profiles = path_user / path_browser

        if self.custom_name_browser_profile is not None:
            return path_profiles / self.custom_name_browser_profile

        default_profile: Path = next(
            (
                d
                for d in path_profiles.glob(self._default_profile_pattern)
                if d.is_dir()
            ),
            None,
        )
        return default_profile

    @property
    def path_source_database(self) -> Path | None:
        """
        Возвращает путь к исходной базе данных браузера.

        Путь определяется по операционной системе и профилю браузера.

        Returns:
            Путь к базе данных браузера.
        """
        return self.path_browser_profile / self.database_file
