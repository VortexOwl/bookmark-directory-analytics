# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import create_task as a_create_task
from asyncio import get_running_loop as a_get_running_loop
from asyncio import sleep as a_sleep
from contextlib import asynccontextmanager
from copy import copy
from enum import Enum
from os import getpid as os_getpid
from os import kill as os_kill
from signal import SIGINT as signal_SIGINT
from typing import Annotated
from webbrowser import open as web_open

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from fastapi import Depends, FastAPI, Form, Query, status
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from pydantic import BaseModel
from uvicorn import run as uvicorn_run

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.app import ApplicationService as app
from src.config import Config, ServerConfig
from src.logs import SmartLogger

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#

cfg = Config()
log: SmartLogger = SmartLogger()
log.setLevel(cfg.log_level)


async def open_browser() -> None:
    sc = ServerConfig()
    await a_sleep(1.5)
    loop = a_get_running_loop()
    loop.run_in_executor(None, web_open, f"http://{sc.host}:{sc.port}")


@asynccontextmanager
async def lifespan(web: FastAPI) -> None:
    is_open_webbrowser = cfg.is_open_webbrowser
    is_docker = cfg.is_docker

    log.info(msg="🚀 Сервер запускается...", pretty=True)
    if is_open_webbrowser and not is_docker:
        a_create_task(open_browser())
    yield

    log.info(msg="🛑 Сервер останавливается...", pretty=True)
    await a_sleep(1.5)


web = FastAPI(
    title="📚 Bookmarks API",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
        "filter": True,
        "displayRequestDuration": True,
    },
    lifespan=lifespan,
)


class Browser(str, Enum):
    FLOORP = "Floorp"


class IsYesOrNo(str, Enum):
    YES = "✔️ Да"
    NO = "❌ Нет"


class WebConfig(BaseModel):
    """
    Pydantic модель для обработки сетевых данных, связанных с конфигурацией проекта.
    """

    browser: Browser = Browser.FLOORP
    bookmarks_folder: str | None = None
    browser_profile: str | None = None
    custom_report_file: str | None = None
    is_default: IsYesOrNo | bool = IsYesOrNo.NO

    @classmethod
    async def web_config_form(
        cls,
        is_default: Annotated[
            IsYesOrNo,
            Form(alias="📜 Установить значения по умолчанию", examples=[IsYesOrNo.NO]),
        ],
        browser: Annotated[
            Browser, Form(alias="🌎 Браузер", examples=[Browser.FLOORP])
        ],
        bookmarks_folder: Annotated[
            str, Form(alias="🏙️ Директория закладок", examples=[""])
        ] = None,
        browser_profile: Annotated[
            str, Form(alias="🪪 Кастомный профиль браузера", examples=[""])
        ] = None,
        custom_report_file: Annotated[
            str, Form(alias="📁 Название файла репорта", examples=[""])
        ] = None,
    ):
        return cls(
            browser=browser,
            bookmarks_folder=bookmarks_folder,
            browser_profile=browser_profile,
            custom_report_file=custom_report_file,
            is_default=is_default,
        )


@web.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@web.get(
    "/shutdown",
    description="Посылает запрос на остановку веб-сервера.",
    tags=["⚙️ Конфигурация"],
    summary="Остановить веб-сервер",
)
async def shutdown():
    os_kill(os_getpid(), signal_SIGINT)
    log.info(msg="Запрос на остановку сервера отправлен...", pretty=True)
    return PlainTextResponse(
        content="Запрос на остановку сервера отправлен.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@web.post(
    "/clear-report-folder",
    description="Очищает папку для отчетов от файлов.",
    tags=["⚙️ Конфигурация"],
    summary="Очистить от файлов директорию для формирования отчётов",
)
async def clear_report_folder() -> dict:
    """
    Очищает папку от файлов.
    Возвращает сводку по успешным удалениям и ошибкам.
    """
    report = await app.clear_report_files(cfg=cfg)
    return JSONResponse(content=report, status_code=status.HTTP_200_OK)


@web.put(
    "/config",
    description="Задает конфигурацию для утилиты анализа закладок браузера.",
    tags=["⚙️ Конфигурация"],
    summary="Задать конфигурацию",
)
async def put_config(
    web_config: Annotated[WebConfig, Depends(WebConfig.web_config_form)],
) -> dict[str, object]:
    """
    Задает конфигурацию для утилиты анализа закладок браузера.
    """
    global cfg
    if web_config.is_default == IsYesOrNo.YES:
        cfg = copy(Config())
        web_config = WebConfig()
        web_config.is_default = True
    else:
        web_config.is_default = False
        if web_config.browser:
            cfg.browser = web_config.browser.value
        if web_config.bookmarks_folder:
            cfg.bookmarks_folder = web_config.bookmarks_folder
        cfg.browser_profile = web_config.browser_profile
        if web_config.custom_report_file:
            cfg.custom_report_file = web_config.custom_report_file
    return web_config.model_dump()


@web.get(
    "/bookmarks-report",
    description="Возвращает отчет по анализу закладок браузера.",
    tags=["📊 Анализ закладок"],
    summary="Получить отчёт по анализу директории закладок",
)
async def get_report(
    is_web_save_file: Annotated[
        IsYesOrNo,
        Query(
            alias="💾 Сохранить файл",
            examples=[IsYesOrNo.YES],
        ),
    ],
    bookmarks_folder: Annotated[
        str,
        Query(
            alias="🏙️ Директория закладок",
            examples=[None],
        ),
    ] = None,
) -> Response:
    """
    Возвращает отчет по анализу закладок браузера.
    """
    is_save_file: bool
    err_status_code: int = status.HTTP_400_BAD_REQUEST
    is_save_file = is_web_save_file == IsYesOrNo.YES
    copy_cfg = copy(cfg)
    data_folder: str = cfg.data_folder
    is_docker: bool = cfg.is_docker

    if bookmarks_folder:
        copy_cfg.bookmarks_folder = bookmarks_folder
        copy_cfg.custom_report_file = None

    log.info(
        msg=f"Начат анализ закладок браузера в папке: {copy_cfg.bookmarks_folder}.",
        pretty=True,
    )
    bookmarks_report, report_path, err = await app.save_bookmarks_report(
        is_save_file, copy_cfg
    )
    if err is not None:
        if err == "По указанному пути отсутствует файл базы данных закладок.":
            if is_docker:
                err += f' Положите файл базы закладок браузера в примонтированный том: "{data_folder}".'
            else:
                err += " Укажите корректный профиль браузера."
            err_status_code = status.HTTP_404_NOT_FOUND
        return PlainTextResponse(content=err, status_code=err_status_code)
    if is_save_file:
        return FileResponse(
            path=report_path,
            filename=report_path.name,
            media_type="text/plain",
            status_code=status.HTTP_200_OK,
        )
    return PlainTextResponse(content=bookmarks_report, status_code=status.HTTP_200_OK)


def web_start() -> None:
    """
    Запускает веб-приложение FastAPI с использованием сервера Uvicorn.
    Читает параметры хоста и порта из конфигурации приложения.
    """
    sc = ServerConfig()
    uvicorn_run(f"{__name__}:web", host=sc.host, port=sc.port, reload=sc.is_reload)


if __name__ == "__main__":
    web_start()
