# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
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
    """

    host: str = "127.0.0.1"
    port: int = 8000
    is_reload: bool = True

    model_config = SettingsConfigDict(env_prefix="API_")

    @model_validator(mode="before")
    @classmethod
    def detect_docker_env(cls, data: dict) -> dict:
        if Path("/.dockerenv").exists():
            if "host" not in data:
                data["host"] = "0.0.0.0"
            if "is_reload" not in data:
                data["is_reload"] = False

        return data


class Config(BaseSettings):
    """
    Конфигурация для проведения анализа директории закладок браузера.
    """

    model_config = SettingsConfigDict(env_prefix="APP_")

    log_level: int = 10
    is_open_webbrowser: bool = True
    _default_profile_pattern: str = "*.default-default"
    bookmarks_folder: str = "KDE Store"
    browser: str = "Floorp"
    browser_folder: str = ".floorp"
    browser_profile: str | None = None
    custom_report_file: str | None = None
    database_file: str = "places.sqlite"
    data_folder: str = "data"
    report_folder: str = "docs"

    @property
    def patch_data_folder(self) -> Path:
        return Path(self.data_folder)

    @property
    def path_data_file(self) -> Path:
        return self.patch_data_folder / self.database_file

    @property
    def report_file(self) -> str:
        return (
            f"Bookmarks {self.bookmarks_folder}"
            if self.custom_report_file is None
            else self.custom_report_file
        )

    @property
    def path_report_folder(self) -> Path:
        return Path(self.report_folder)

    @property
    def path_report_file(self) -> Path:
        return self.path_report_folder / f"{self.report_file}.txt"

    @property
    def is_docker(self) -> bool:
        return Path("/.dockerenv").exists()

    @property
    def path_source_database(self) -> Path | None:
        sys_name = system()
        path_user: Path = Path.home()
        path_browser: Path = Path(self.browser)
        path_browser_folder: Path = Path(self.browser_folder)
        path_profiles: Path
        path_profile_bookmarks: Path

        if sys_name == "Windows":
            path_browser = Path("AppData") / "Roaming" / path_browser / "Profiles"
        elif sys_name == "Linux":
            path_browser = path_browser_folder
        else:
            return None

        path_profiles = path_user / path_browser

        if self.browser_profile is not None:
            path_profile_bookmarks = path_profiles / self.browser_profile
        else:
            default_profile: Path = next(
                (
                    d
                    for d in path_profiles.glob(self._default_profile_pattern)
                    if d.is_dir()
                ),
                None,
            )
            if default_profile is None:
                return None
            path_profile_bookmarks = default_profile

        return path_profile_bookmarks / self.database_file
