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

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#

app_report = app.ReportService()
app_clear = app.ClearReportService()


def start() -> None:
    """
    Запускает формирование и сохранение отчёта по закладкам.

    Notes:
        Функция является точкой входа и запускает асинхронную операцию
        формирования отчёта с сохранением результата в файл.
    """
    async_run(app_report.generate_report(is_save_file=True))


def start_clear() -> None:
    """
    Запускает очистку директории с отчётами от файлов.

    Notes:
        Функция является точкой входа и запускает асинхронную операцию
        очистки директории для хранения отчётов.
    """

    async_run(app_clear.clear_report_directory())


if __name__ == "__main__":
    start()
