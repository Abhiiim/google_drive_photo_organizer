"""Logging utilities providing structured logging configuration."""

from __future__ import annotations

import logging
from importlib import import_module
import inspect
from logging.config import dictConfig
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import yaml

from core.config import get_settings


DEFAULT_LOGGING_CONFIG = Path(__file__).resolve().parent / "logging_config.yaml"
_LOGGING_INITIALIZED = False


def setup_logging(force: bool = False) -> None:
    """Configure structlog + standard logging with optional YAML overrides."""

    global _LOGGING_INITIALIZED

    if _LOGGING_INITIALIZED and not force:
        return

    settings = get_settings()
    logs_dir = settings.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    logging_config = _load_logging_config(settings)

    if logging_config is not None:
        try:
            dictConfig(logging_config)
        except Exception as exc:  # pragma: no cover - fallback safety
            logging.getLogger(__name__).warning(
                "logging.config_apply_failed",
                error=str(exc),
            )
            _configure_default_logging(settings)
    else:
        _configure_default_logging(settings)

    _configure_structlog(settings)
    _configure_access_logger(settings)

    _LOGGING_INITIALIZED = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger, configuring logging if needed."""

    if not _LOGGING_INITIALIZED:
        setup_logging()
    return structlog.get_logger(name)


def bind_contextvars(**kwargs: Any) -> None:
    """Bind key/value pairs to the current logging context."""

    if not _LOGGING_INITIALIZED:
        setup_logging()
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """Clear context variables from the current logging context."""

    structlog.contextvars.clear_contextvars()


def _load_logging_config(settings) -> Optional[Dict[str, Any]]:
    """Attempt to load logging configuration from YAML."""

    config_path = settings.logging_config_path or DEFAULT_LOGGING_CONFIG

    if not config_path.exists():
        return None

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    except Exception as exc:
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.warning("logging.config_load_failed", error=str(exc))
        return None

    if not isinstance(config, dict):
        return None

    _apply_runtime_overrides(config, settings)
    return config


def _apply_runtime_overrides(config: Dict[str, Any], settings) -> None:
    """Ensure file handlers use runtime paths and levels from settings."""

    logs_dir = settings.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_level = settings.log_level.upper()

    handlers = config.setdefault("handlers", {})

    def _update_file_handler(handler_key: str, filename: str) -> None:
        handler = handlers.get(handler_key)
        if handler is None:
            return
        handler["filename"] = str(logs_dir / filename)
        handler.setdefault("when", "midnight")
        handler["backupCount"] = settings.log_backup_count
        handler.setdefault("encoding", "utf-8")

    _update_file_handler("app_file", settings.app_log_filename)
    _update_file_handler("error_file", settings.error_log_filename)
    _update_file_handler("access_file", settings.access_log_filename)

    console_handler = handlers.get("console")
    if console_handler is not None:
        console_handler.setdefault("stream", "ext://sys.stdout")
        console_handler["level"] = log_level

    root_config = config.setdefault("root", {})
    root_config["level"] = log_level
    root_config.setdefault("handlers", ["console", "app_file", "error_file"])

    access_logger_config = config.setdefault("loggers", {}).setdefault("access", {})
    access_logger_config.setdefault("handlers", ["access_file"])
    access_logger_config["level"] = log_level
    access_logger_config["propagate"] = False

    formatters = config.get("formatters", {})
    _materialize_structlog_processors(formatters)


def _configure_default_logging(settings) -> None:
    """Configure logging via Python objects when YAML config is unavailable."""

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logs_dir = settings.logs_dir

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    app_file_handler = TimedRotatingFileHandler(
        filename=logs_dir / settings.app_log_filename,
        when="midnight",
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(formatter)

    error_file_handler = TimedRotatingFileHandler(
        filename=logs_dir / settings.error_log_filename,
        when="midnight",
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)


def _configure_structlog(settings) -> None:
    """Configure structlog processors to emit JSON logs."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _configure_access_logger(settings) -> None:
    """Ensure the access logger writes to a dedicated rotating file."""

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logs_dir = settings.logs_dir
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    access_logger = logging.getLogger("access")
    access_logger.handlers.clear()

    access_file_handler = TimedRotatingFileHandler(
        filename=logs_dir / settings.access_log_filename,
        when="midnight",
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    access_file_handler.setLevel(log_level)
    access_file_handler.setFormatter(formatter)

    access_logger.addHandler(access_file_handler)
    access_logger.setLevel(log_level)
    access_logger.propagate = False


def _materialize_structlog_processors(formatters: Dict[str, Any]) -> None:
    """Convert dotted path processor definitions into callables."""

    for formatter in formatters.values():
        target = formatter.get("()")
        if target != "structlog.stdlib.ProcessorFormatter":
            continue
        processors = formatter.get("processors", [])
        materialized = []
        for processor in processors:
            materialized.append(_import_processor(processor))
        formatter["processors"] = materialized


def _import_processor(definition: Any) -> Any:
    """Import processor definitions from strings or dict definitions."""

    if isinstance(definition, str):
        return _import_from_string(definition)

    if isinstance(definition, dict):
        name = definition.get("name")
        kwargs = definition.get("kwargs", {})
        processor = _import_from_string(name) if name else None
        if processor is None:
            return None
        if inspect.isclass(processor):
            return processor(**kwargs) if kwargs else processor()
        if callable(processor) and kwargs:
            return processor(**kwargs)
        return processor

    return definition


def _import_from_string(path: Optional[str]) -> Any:
    """Import a dotted-path attribute, supporting nested attributes."""

    if not path:
        return None

    parts = path.split(".")
    for index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:index])
        try:
            module = import_module(module_name)
        except ImportError:
            continue

        attr_parts = parts[index:]
        obj: Any = module
        for attr in attr_parts:
            obj = getattr(obj, attr)
        return obj

    raise ImportError(f"Invalid import path: {path}")

