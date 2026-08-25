from datetime import datetime

default_format = "%Y-%m-%dT%H:%M:%S"
default_format_utc = "%Y-%m-%dT%H:%M:%SZ"
default_format_with_offset = "%Y-%m-%dT%H:%M:%S%z"

def on_env(env, config, files, **kwargs):
    def datetime_parse(value, format=None):
        if format is None:
            try:
                return datetime.strptime(str(value), default_format_utc)
            except ValueError:
                pass
            try:
                return datetime.strptime(str(value), default_format_with_offset)
            except ValueError:
                pass
            try:
                return datetime.strptime(str(value), default_format)
            except ValueError:
                raise Exception("The input date does not match the ISO 8601 format with or without offset.")

        return datetime.strptime(str(value), format)

    def datetime_format(value, format=None):
        if format is None:
            format = default_format_with_offset
        return value.strftime(format)

    env.filters["datetime_format"] = datetime_format
    env.filters["datetime_parse"] = datetime_parse
