# ----------------------------------------------------------------------------#
# Embedded libraries                                                          #
# ----------------------------------------------------------------------------#
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    LogRecord,
    getLevelNamesMapping,
)
from logging import FileHandler as LibFileHandler
from logging import Formatter as LibFormatter
from logging import Logger as LibLogger
from logging import StreamHandler as LibStreamHandler
from logging import addLevelName as libAddLevelName
from logging import getLogger as libGetLogger
from logging import setLoggerClass as libSetLoggerClass
from os import makedirs
from sys import exit, stdout
from typing import Any

# ----------------------------------------------------------------------------#
# External libraries                                                          #
# ----------------------------------------------------------------------------#
from colorama import Fore as color_Fore

# ----------------------------------------------------------------------------#
# Application code                                                            #
# ----------------------------------------------------------------------------#


class SmartLogger(LibLogger):
    """Logger с дополнительными возможностями форматирования и кастомными уровнями.

    Расширяет стандартный `logging.Logger`, добавляя:
    * флаг `pretty` — вывод сообщения с упрощенным форматированием;
    * флаг `raw` — вывод сообщения без стандартного форматирования;
    * флаг `empty_console` — подавление вывода в консоль;
    * метод `add_custom_level` для регистрации пользовательских уровней логирования.
    """

    def __new__(cls, name: str = "smart_logger", all_level: int = DEBUG) -> "SmartLogger":
        """Возвращает существующий экземпляр SmartLogger с данным именем или создает новый.

        Повторяет поведение `logging.getLogger`: при повторном вызове с тем же
        `name` возвращается тот же самый (уже настроенный) экземпляр вместо
        создания нового и повторной настройки обработчиков.

        Args:
            name: Имя logger.
            all_level: Минимальный уровень логирования (используется только
                при создании нового экземпляра, см. `__init__`).

        Returns:
            Экземпляр SmartLogger.
        """

        existing = LibLogger.manager.loggerDict.get(name)
        return existing if isinstance(existing, SmartLogger) else super().__new__(cls)

    def __init__(self, name: str = "smart_logger", all_level: int = DEBUG):
        """Создает и настраивает экземпляр SmartLogger.

        Если logger с указанным именем уже существовал (например, был создан
        ранее вызовом `SmartLogger(name)` или `logging.getLogger(name)`),
        повторная инициализация и настройка обработчиков не выполняются —
        `__new__` в этом случае уже вернул готовый экземпляр.

        Args:
            name: Имя logger.
            all_level: Минимальный уровень логирования для базовой
                конфигурации (консоль + файлы, см. `_basic_configuration`).
        """

        if self.__dict__.get("_smart_logger_initialized", False):
            return

        super().__init__(name=name)

        self.manager = LibLogger.manager
        self.manager.loggerDict[name] = self
        self.manager._fixupParents(self)

        self._smart_logger_initialized = True

        if not self.handlers:
            self._basic_configuration(all_level=all_level)

    def __str__(self) -> str:
        """Возвращает строковое представление доступных уровней логирования."""

        return f"Logger levels: {getLevelNamesMapping()}"

    def _prepare_extra(
        self,
        pretty: bool,
        raw: bool,
        empty_console: bool,
        extra: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Подготавливает словарь `extra` с параметрами форматирования.

        Если хотя бы один из флагов форматирования установлен в `True`,
        соответствующие значения добавляются в словарь `extra`.

        Args:
            pretty: Если `True`, сообщение выводится в упрощённом формате
                `{levelname}:     {message}`. Имя уровня окрашивается
                в цвет, соответствующий уровню.
            raw: Если `True`, сообщение выводится в формате `{message}`.
            empty_console: Если `True`, сообщение не выводится в консоль.
            extra: Дополнительные данные записи журнала.

        Returns:
            Обновлённый словарь `extra` или `None`, если параметры
            форматирования не заданы.
        """

        if pretty or raw or empty_console:
            if extra is None:
                extra = {}
            extra["pretty"] = pretty
            extra["raw"] = raw
            extra["empty_console"] = empty_console
        return extra

    def _basic_configuration(self, all_level: int = DEBUG) -> None:
        """Выполняет базовую настройку SmartLogger.

        Настраивает:
        * уровень logger;
        * консольный обработчик;
        * файловые обработчики для уровней DEBUG, INFO, WARNING, ERROR, CRITICAL;
        * общий файловый лог для всех уровней, начиная с `all_level`.

        Args:
            logger: Экземпляр SmartLogger для настройки.
            all_level: Минимальный уровень логирования для консоли и общего файла.

        Returns:
            Настроенный экземпляр SmartLogger.
        """

        self.setLevel(level=all_level)
        self.propagate = False

        # Console
        add_handler(logger=self, level=all_level)

        # File
        makedirs(name="logs", exist_ok=True)
        add_handler(logger=self, level=DEBUG, filename="logs/logs_debug.log", exact=True)
        add_handler(logger=self, level=INFO, filename="logs/logs_info.log", exact=True)
        add_handler(
            logger=self, level=WARNING, filename="logs/logs_warning.log", exact=True
        )
        add_handler(logger=self, level=ERROR, filename="logs/logs_error.log", exact=True)
        add_handler(
            logger=self, level=CRITICAL, filename="logs/logs_critical.log", exact=True
        )

        add_handler(logger=self, level=all_level, filename="logs/logs_all_levels.log")
    
    def debug(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `DEBUG` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().debug(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def info(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `INFO` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().info(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def warning(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `WARNING` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().warning(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def error(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `ERROR` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().error(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

    def critical(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        is_continue: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `CRITICAL` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            is_continue: Если True, продолжает работу программы после своего вызова.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().critical(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

        if not is_continue:
            exit()

    def fatal(
        self,
        msg: Any,
        *args: Any,
        pretty: bool = False,
        raw: bool = False,
        empty_console: bool = False,
        is_continue: bool = False,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Записывает сообщение уровня `CRITICAL` с дополнительными параметрами форматирования.

        Args:
            msg: Сообщение для логирования.
            *args: Позиционные аргументы для форматирования сообщения.
            pretty: Если True, сообщение выводится в упрощенном форматировании.
            raw: Если True, сообщение выводится без стандартного форматирования.
            empty_console: Если True, подавляет вывод в консоль.
            is_continue: Если True, продолжает работу программы после своего вызова.
            exc_info: Информация об исключении или флаг для её добавления.
            stack_info: Если True, добавляет информацию о стеке.
            stacklevel: Смещение уровня стека для корректного указания места вызова.
            extra: Дополнительные данные для лог-записи.
            **kwargs: Дополнительные параметры, пробрасываемые в базовый logger.
        """

        extra = self._prepare_extra(
            pretty=pretty, raw=raw, empty_console=empty_console, extra=extra
        )
        super().critical(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
            **kwargs,
        )

        if not is_continue:
            exit()

    def add_custom_level(
        self,
        level_name: str,
        level_num: int,
        is_duplicate_level_num: bool = False,
        filename: str | None = None,
        is_create_file_level: bool = True,
    ) -> None:
        """Регистрирует пользовательский уровень логирования и метод для него.

        Добавляет новый уровень в модуль `logging`, создаёт соответствующий
        метод в классе `SmartLogger` и при необходимости добавляет файловый
        handler, который записывает только сообщения этого уровня.

        Args:
            level_name: Имя уровня (например, "TRACE").
            level_num: Числовое значение уровня.
            is_duplicate_level_num: Если False, проверяет, что число уровня не занято.
            filename: Имя файла для логов этого уровня. Если не указано,
                используется `logs/logs_<method_name>.log`.
            is_create_file_level: Если True, создается файловый handler для уровня.

        Raises:
            ValueError: Если `is_duplicate_level_num` False и уровень уже существует.
            AttributeError: Если метод с таким именем уже существует в `SmartLogger`.
        """

        if not is_duplicate_level_num:
            levels = getLevelNamesMapping()
            if level_num in levels.values():
                raise ValueError(f"Level number {level_num} is already used")

        method_name = level_name.lower()
        libAddLevelName(level_num, level_name)

        def custom_log_method(self, message, *args, **kwargs) -> None:
            if self.isEnabledFor(level_num):
                self._log(level_num, message, args, **kwargs, stacklevel=2)

        if hasattr(SmartLogger, method_name):
            raise AttributeError(f"Method '{method_name}' already exists in Logger")

        setattr(SmartLogger, method_name, custom_log_method)

        if is_create_file_level:
            makedirs(name="logs", exist_ok=True)
            if filename is None:
                filename = f"logs/logs_{method_name}.log"
            elif "/" not in filename:
                filename = f"logs/logs_{filename}.log"
            add_handler(logger=self, level=level_num, filename=filename, exact=True)


class StreamHandler(LibStreamHandler):
    """Обработчик потокового вывода с поддержкой специальных флагов.

    Использует разные форматеры в зависимости от параметров записи:
    * `record.raw == True` — выводится только сообщение (`{message}`);
    * `record.pretty == True` — используется упрощённый цветной формат;
    * `record.empty_console == True` — запись не выводится в консоль.

    """

    def __init__(self, stream=None) -> None:
        """Создаёт обработчик потока с предустановленными форматерами.

        Args:
            stream: Поток вывода (по умолчанию sys.stdout).
        """

        super().__init__(stream)

        self.normal_formatter = LibFormatter(
            fmt=basic_format, style="{", datefmt="%Y-%m-%d %H:%M:%S"
        )

        self.raw_formatter = LibFormatter(fmt="{message}", style="{")

        info_fmt = f"{color_Fore.CYAN}{{levelname}}{color_Fore.RESET}:     {{message}}"
        debug_fmt = (
            f"{color_Fore.GREEN}{{levelname}}{color_Fore.RESET}:     {{message}}"
        )
        warning_fmt = (
            f"{color_Fore.YELLOW}{{levelname}}{color_Fore.RESET}:     {{message}}"
        )
        error_fmt = f"{color_Fore.RED}{{levelname}}{color_Fore.RESET}:     {{message}}"
        critical_fmt = (
            f"{color_Fore.MAGENTA}{{levelname}}{color_Fore.RESET}:     {{message}}"
        )

        self.debug_formatter = LibFormatter(fmt=debug_fmt, style="{")
        self.info_formatter = LibFormatter(fmt=info_fmt, style="{")
        self.warning_formatter = LibFormatter(fmt=warning_fmt, style="{")
        self.error_formatter = LibFormatter(fmt=error_fmt, style="{")
        self.critical_formatter = LibFormatter(fmt=critical_fmt, style="{")

    def emit(self, record: LogRecord) -> None:
        """Выводит лог-запись в поток в зависимости от флагов записи.

        Если у записи установлен `empty_console`, вывод подавляется.
        В противном случае форматер выбирается по значениям флагов
        `raw` и `pretty`.

        Args:
            record: Лог-запись для вывода.
        """

        if getattr(record, "empty_console", False):
            return

        if getattr(record, "raw", False):
            self.formatter = self.raw_formatter
        elif getattr(record, "pretty", False):
            level = record.levelno
            if level == DEBUG:
                self.formatter = self.debug_formatter
            elif level == INFO:
                self.formatter = self.info_formatter
            elif level == WARNING:
                self.formatter = self.warning_formatter
            elif level == ERROR:
                self.formatter = self.error_formatter
            elif level == CRITICAL:
                self.formatter = self.critical_formatter
        else:
            self.formatter = self.normal_formatter

        super().emit(record)


def add_handler(
    logger: SmartLogger, level: int, filename: str | None = None, exact: bool = False
) -> None:
    """Добавляет обработчик к logger.

    Если указан `filename`, создаётся файловый обработчик; в противном
    случае используется потоковый обработчик с выводом в `stdout`.
    При `exact=True` обработчик принимает только записи строго
    заданного уровня.

    Args:
        logger: Экземпляр SmartLogger, к которому добавляется обработчик.
        level: Уровень логирования для обработчика.
        filename: Путь к файлу логов. Если `None`, используется `stdout`.
        exact: Если `True`, обработчик фильтрует записи по точному соответствию
            с уровнем `level`.
    """

    if filename:
        handler = LibFileHandler(filename, encoding="utf-8")
        handler.setFormatter(
            LibFormatter(fmt=basic_format, style="{", datefmt="%Y-%m-%d %H:%M:%S")
        )
    else:
        handler = StreamHandler(stdout)
    handler.setLevel(level)
    if exact:
        handler.addFilter(lambda record: record.levelno == level)
    logger.addHandler(handler)


basic_format: str = (
    "{asctime} | {levelname} | "
    "{filename} -> {funcName}: line {lineno} | "
    "Message: {message}"
)
pretty_format: str = (
    color_Fore.GREEN + "{levelname}" + color_Fore.RESET + ":     {message}"
)
