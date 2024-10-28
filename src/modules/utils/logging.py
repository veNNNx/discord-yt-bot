from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggerSettings(BaseSettings):
    LOGFILE_PATHNAME: str = "discord_bot.log"
    LOG_FORMAT: str = (
        "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d %(levelname)s %(message)s"
    )

    model_config = SettingsConfigDict(env_prefix="LOGGER_CONFIG_", case_sensitive=True)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LoggerSettings().LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "logfile": {
            "formatter": "default",
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": LoggerSettings().LOGFILE_PATHNAME,
            "when": "midnight",
        },
        "console": {
            "formatter": "default",
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "discord": {
            "level": "ERROR",
            "handlers": ["console", "logfile"],
            "propagate": False,
        },
    },
    "root": {"level": "NOTSET", "handlers": ["logfile", "console"]},
}
