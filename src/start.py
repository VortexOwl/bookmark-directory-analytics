# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from asyncio import run as async_run

# ----------------------------------------------------------------------------#
# Project modules                                                             #
# ----------------------------------------------------------------------------#
from utilities.basic_utilities_project import add_workdir_in_PATH

add_workdir_in_PATH()
from src.app import ApplicationService as app
from src.web.router import start_web_server

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#

app_report = app.ReportService()
app_clear = app.ClearReportService()


def start_web() -> None:
    """
    Запускает приложение.

    Notes:
        Функция инициализирует и запускает веб-сервер приложения.
    """
    start_web_server()


def start_default() -> None:
    """
    Запускает анализ директории закладок с использованием настроек по умолчанию
    и формирует отчёт по результатам анализа.

    Notes:
        Функция является точкой входа и запускает асинхронную операцию,
        которая анализирует директорию закладок, формирует отчёт и сохраняет
        его в текстовый файл.
    """
    async_run(app_report.generate_report(is_save_file=True))


def start_clear() -> None:
    """
    Запускает очистку директории с отчётами от файлов.

    Notes:
        Функция является точкой входа и запускает асинхронную операцию
        очистки директории для хранения отчётов.
    """

    async_run(app_clear.cleanup())


if __name__ == "__main__":
    start_web()
