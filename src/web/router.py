# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import create_task as a_create_task
from asyncio import get_running_loop as a_get_running_loop
from asyncio import sleep as a_sleep
from contextlib import asynccontextmanager
from copy import copy
from enum import Enum
from json import dumps as json_dumps
from typing import Annotated
from webbrowser import open as web_open

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from fastapi import Depends, FastAPI, Form, Query, Request, status
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from uvicorn import Config as UvicornConfig
from uvicorn import Server as UvicornServer

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from src.app import ApplicationService as app
from src.config import Config, ServerConfig
from src.logs import SmartLogger
from src.utilities import Utilities as uts

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#

cfg = Config()
log: SmartLogger = SmartLogger()
log.setLevel(cfg.log_level)
app_report = app.ReportService()
app_clear = app.ClearReportService()
template_renderer = Jinja2Templates(
    directory=uts.resource_path(relative_path="src/templates")
)
sc: ServerConfig = ServerConfig()
uvicorn_config: UvicornConfig = UvicornConfig(
    f"{__name__}:web",
    host=sc.host,
    port=sc.port,
    reload=sc.is_reload,
    access_log=sc.access_log,
)
uvicorn_server: UvicornServer = UvicornServer(uvicorn_config)


async def open_browser() -> None:
    """
    Открывает веб-интерфейс приложения в браузере.

    Функция ожидает запуска сервера, после чего открывает URL приложения
    в системном браузере.

    Notes:
        Используется только при запуске вне Docker-контейнера.
    """
    sc = ServerConfig()
    await a_sleep(1.5)
    loop = a_get_running_loop()
    loop.run_in_executor(None, web_open, f"http://{sc.host}:{sc.port}")


@asynccontextmanager
async def lifespan(web: FastAPI):
    """
    Управляет жизненным циклом FastAPI-приложения.

    При запуске записывает сообщение в журнал и при необходимости открывает
    веб-интерфейс в браузере. При завершении выполняет небольшую задержку,
    чтобы корректно завершить фоновые операции.

    Args:
        web: Экземпляр FastAPI-приложения.

    Yields:
        Управление приложению на время его работы.

    Returns:
        Ничего не возвращает после завершения жизненного цикла приложения.
    """
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

web.mount(
    path="/static",
    app=StaticFiles(directory=uts.resource_path(relative_path="src/static")),
    name="static",
)


class Browser(str, Enum):
    """
    Поддерживаемые браузеры, из которых извлекаются закладки.
    """

    FLOORP = "Floorp"


class IsYesOrNo(str, Enum):
    """
    Перечисление вариантов ответа «да» или «нет».
    """

    YES = "Да"
    NO = "Нет"


class WebConfig(BaseModel):
    """
    Модель конфигурации веб-интерфейса анализатора закладок.

    Attributes:
        browser: Браузер, используемый для поиска базы закладок.
        bookmarks_folder: Директория или название папки с закладками.
        browser_profile: Пользовательский профиль браузера.
        custom_report_file: Пользовательское имя файла отчёта.
        is_default: Признак сброса конфигурации к значениям по умолчанию.
    """

    browser: Browser = Browser.FLOORP
    bookmarks_folder: str | None = None
    browser_profile: str | None = None
    custom_report_file: str | None = None
    is_default: IsYesOrNo = IsYesOrNo.NO

    @classmethod
    async def web_config_form(
        cls,
        browser: Annotated[
            Browser,
            Form(alias="browser", description="🌎 Браузер", examples=[Browser.FLOORP]),
        ] = Browser.FLOORP,
        bookmarks_folder: Annotated[
            str | None,
            Form(
                alias="bookmarks folder",
                description="🏙️ Директория закладок",
                examples=[""],
            ),
        ] = None,
        browser_profile: Annotated[
            str | None,
            Form(
                alias="custom browser profile",
                description="🪪 Кастомный профиль браузера",
                examples=[""],
            ),
        ] = None,
        custom_report_file: Annotated[
            str | None,
            Form(
                alias="name report file",
                description="📁 Название файла репорта",
                examples=[""],
            ),
        ] = None,
        is_default: Annotated[IsYesOrNo, Form(alias="is default")] = IsYesOrNo.NO,
    ) -> WebConfig:
        """
        Создаёт конфигурацию из данных HTML-формы.

        Args:
            is_default: Нужно ли использовать значения по умолчанию.
            browser: Выбранный браузер.
            bookmarks_folder: Директория с закладками.
            browser_profile: Пользовательский профиль браузера.
            custom_report_file: Имя файла отчёта.

        Returns:
            Экземпляр ``WebConfig`` с параметрами формы.
        """
        return cls(
            browser=browser,
            bookmarks_folder=bookmarks_folder,
            browser_profile=browser_profile,
            custom_report_file=custom_report_file,
            is_default=is_default or IsYesOrNo.NO,
        )


@web.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """
    Перенаправляет пользователя на HTML-форму анализа директории закладок.

    Returns:
        HTTP-редирект на страницу ``/directory-analytics/new``.
    """
    return RedirectResponse(
        url="/directory-analytics/new", status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@web.get(
    "/shutdown",
    description="Посылает запрос на остановку веб-сервера.",
    tags=["⚙️ Конфигурация"],
    summary="Остановить веб-сервер",
)
async def shutdown(request: Request) -> Response:
    """
    Отправляет текущему процессу сигнал остановки веб-сервера.

    Args:
        request: Текущий HTTP-запрос. Используется для выбора формата
            ответа: HTML или JSON.

    Returns:
        HTML-страница или JSON-ответ с подтверждением отправки сигнала.
    """
    uvicorn_server.should_exit = True
    log.info(msg="Запрос на остановку сервера отправлен...", pretty=True)
    if "text/html" in request.headers.get("accept", ""):
        return template_renderer.TemplateResponse(
            request=request,
            name="shutdown.html",
            status_code=status.HTTP_202_ACCEPTED,
        )
    return JSONResponse(
        content={
            "status": "ok",
            "message": "Запрос на остановку сервера отправлен",
        },
        status_code=status.HTTP_202_ACCEPTED,
    )


@web.get("/cleanup", include_in_schema=False)
async def get_cleanup(request: Request) -> Response:
    """
    Отображает HTML-форму очистки папки отчётов.

    Args:
        request: Текущий HTTP-запрос.

    Returns:
        HTML-страница с формой запуска очистки отчётов.
    """
    return template_renderer.TemplateResponse(
        request=request,
        name="cleanup.html",
        status_code=status.HTTP_200_OK,
    )


@web.post(
    "/cleanup",
    description="Очищает папку для отчетов от файлов.",
    tags=["⚙️ Конфигурация"],
    summary="Очистить от файлов директорию для формирования отчётов",
)
async def post_cleanup(request: Request) -> Response:
    """
    Очищает папку отчётов и возвращает результат операции.

    Args:
        request: Текущий HTTP-запрос. Используется для выбора формата
            ответа: HTML или JSON.

    Returns:
        HTML-страница с отчётом об очистке или JSON-ответ со сводкой
        операции.
    """
    path_report_folder = cfg.path_report_folder
    if path_report_folder.exists():
        report = await app_clear.cleanup()
    else:
        report = {"success": 0, "errors": 0, "names of errors": ()}
        log.debug(msg=f"Сводка выполнения очистки:\n{report}", pretty=True)
    if "text/html" in request.headers.get("accept", ""):
        report["pretty json"] = json_dumps(report, indent=2, ensure_ascii=False)
        context = {
            "report": report,
        }
        return template_renderer.TemplateResponse(
            request=request,
            name="cleanup.html",
            context=context,
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={
            "status": "ok",
            "message": "Ручка очистки директории отчетов от файлов доступна через POST /cleanup",
            "report": report,
        },
        status_code=status.HTTP_200_OK,
    )


@web.get("/update-config", include_in_schema=False)
async def get_config(request: Request) -> Response:
    """
     Отображает HTML-форму конфигурации сервиса анализа директории закладок.

    Args:
        request: Текущий HTTP-запрос.

    Returns:
        HTML-страница с формой конфигурации анализа директории закладок.
    """
    name_report_file = cfg.custom_name_report_file or cfg.name_report_file
    context = {
        "bookmarks_folder": cfg.bookmarks_folder,
        "name_report_file": name_report_file,
        "browser_profile": cfg.path_browser_profile,
    }
    return template_renderer.TemplateResponse(
        request=request,
        context=context,
        name="config-form.html",
        status_code=status.HTTP_200_OK,
    )


@web.post(
    "/update-config",
    description="Задает конфигурацию для утилиты анализа закладок браузера.",
    tags=["⚙️ Конфигурация"],
    summary="Задать конфигурацию",
)
async def update_config(
    request: Request,
    web_config: Annotated[WebConfig, Depends(WebConfig.web_config_form)],
) -> Response:
    """
    Сохраняет конфигурацию анализатора закладок.

    Для HTML-запросов возвращает страницу с результатом сохранения.
    Для API-запросов возвращает сохранённые параметры в формате JSON.

    Args:
        request: Текущий HTTP-запрос. Используется для определения формата
            ответа.
        web_config: Параметры конфигурации, полученные из HTML-формы.

    Returns:
        HTML-страница с результатом сохранения или JSON-ответ с конфигурацией.
    """
    if web_config.is_default == IsYesOrNo.YES:
        default_cfg = Config()
        cfg.browser = default_cfg.browser
        cfg.bookmarks_folder = default_cfg.bookmarks_folder
        cfg.custom_name_browser_profile = default_cfg.custom_name_browser_profile
        cfg.custom_name_report_file = default_cfg.custom_name_report_file
        web_config = WebConfig()
        log.info(msg="Установлены настройки по умолчанию", pretty=True)
    else:
        if web_config.browser:
            cfg.browser = web_config.browser.value
            log.info(msg=f'Выбран браузер "{web_config.browser.value}".', pretty=True)
        if web_config.bookmarks_folder:
            cfg.bookmarks_folder = web_config.bookmarks_folder
            log.info(
                msg=f'Выбрана папка закладок "{web_config.bookmarks_folder}".',
                pretty=True,
            )
        if web_config.browser_profile:
            cfg.custom_name_browser_profile = web_config.browser_profile
            log.info(
                msg=f'Установлен профиль браузера "{web_config.browser_profile}".',
                pretty=True,
            )
        if web_config.custom_report_file:
            cfg.custom_name_report_file = web_config.custom_report_file
            log.info(
                msg=f'Для файла отчета установлено название "{web_config.custom_report_file}".',
                pretty=True,
            )
    if "text/html" in request.headers.get("accept", ""):
        return template_renderer.TemplateResponse(
            request=request,
            name="config-response.html",
            status_code=status.HTTP_200_OK,
        )
    return web_config.model_dump()


@web.get("/directory-analytics/new", include_in_schema=False)
async def new_analytics(request: Request) -> Response:
    """
    Отображает HTML-форму анализа директории закладок.

    Args:
        request: Текущий HTTP-запрос.

    Returns:
        HTML-страница с формой параметров поиска.
    """
    context = {"bookmarks_folder": cfg.bookmarks_folder}
    return template_renderer.TemplateResponse(
        request=request,
        context=context,
        name="directory-analytics-form.html",
        status_code=status.HTTP_200_OK,
    )


@web.get(
    "/directory-analytics/report",
    description="Возвращает отчет по анализу закладок браузера.",
    tags=["📑 Анализ директории закладок"],
    summary="Получить отчёт по анализу директории закладок",
)
async def get_report(
    request: Request,
    is_web_save_file: Annotated[
        IsYesOrNo,
        Query(
            alias="saving file",
            description="💾 Сохранить файл",
            examples=[IsYesOrNo.YES],
        ),
    ],
    bookmarks_folder: Annotated[
        str | None,
        Query(
            alias="bookmarks folder",
            description="🏙️ Директория закладок",
            examples=[None],
        ),
    ] = None,
) -> Response:
    """
    Формирует отчёт по закладкам из выбранной директории.

    В зависимости от параметров запроса возвращает HTML-страницу
    с результатами анализа, текстовый отчёт или файл отчёта для скачивания.

    Args:
        request: Текущий HTTP-запрос. Используется для определения формата
            ответа: HTML или текстовый API-ответ.
        is_web_save_file: Нужно ли сохранить отчёт в файл.
        bookmarks_folder: Папка закладок для анализа.
            Если значение не указано, используется директория из конфигурации.

    Returns:
        HTML-страница с результатом анализа, текстовый отчёт или файл
        с отчётом для скачивания.
    """
    is_save_file: bool
    err_status_code: int = status.HTTP_400_BAD_REQUEST
    is_save_file = is_web_save_file == IsYesOrNo.YES
    copy_cfg = copy(cfg)
    data_folder: str = cfg.data_folder
    is_docker: bool = cfg.is_docker

    if bookmarks_folder:
        copy_cfg.bookmarks_folder = bookmarks_folder

    log.info(
        msg=f"Начат анализ закладок браузера в папке: {copy_cfg.bookmarks_folder}.",
        pretty=True,
    )
    bookmarks_report, report_path, err = await app_report.generate_report(
        is_save_file=is_save_file, cfg=copy_cfg
    )
    if err is not None:
        if err == "По указанному пути отсутствует файл базы данных закладок.":
            if is_docker:
                err += f' Положите файл базы закладок браузера в примонтированный том: "{data_folder}".'
            else:
                err += " Укажите корректный профиль браузера."
            err_status_code = status.HTTP_404_NOT_FOUND
        if "text/html" in request.headers.get("accept", ""):
            context = {
                "name_folder": copy_cfg.bookmarks_folder,
                "err": err,
            }
            return template_renderer.TemplateResponse(
                request=request,
                name="directory-analytics-result.html",
                context=context,
                status_code=status.HTTP_200_OK,
            )
        return PlainTextResponse(content=err, status_code=err_status_code)
    if is_save_file:
        return FileResponse(
            path=report_path,
            filename=report_path.name,
            media_type="text/plain",
            status_code=status.HTTP_200_OK,
        )

    if "text/html" in request.headers.get("accept", ""):
        context = {
            "name_folder": copy_cfg.bookmarks_folder,
            "report": bookmarks_report,
        }
        return template_renderer.TemplateResponse(
            request=request,
            name="directory-analytics-result.html",
            context=context,
            status_code=status.HTTP_200_OK,
        )
    return PlainTextResponse(content=bookmarks_report, status_code=status.HTTP_200_OK)


def start_web_server() -> None:
    """
    Запускает FastAPI-приложение с помощью Uvicorn.

    Параметры хоста, порта, режима перезагрузки и журнала доступа
    считываются из конфигурации приложения.
    """
    try:
        uvicorn_server.run()
    except KeyboardInterrupt:
        log.debug(
            "🛑 Сервер остановлен пользователем через `Ctrl+Shift+C`.", pretty=True
        )


if __name__ == "__main__":
    start_web_server()
