import datetime

default_format = "%Y-%m-%dT%H:%M:%S"
default_format_utc = "%Y-%m-%dT%H:%M:%SZ"
default_format_with_offset = "%Y-%m-%dT%H:%M:%S%z"

def on_env(env, config, files, **kwargs):
    def datetime_parse(value, format=None):
        if format is None:
            try:
                return datetime.datetime.strptime(str(value), default_format_utc).astimezone(datetime.UTC)
            except ValueError:
                pass
            try:
                return datetime.datetime.strptime(str(value), default_format_with_offset).astimezone(datetime.UTC)
            except ValueError:
                pass
            try:
                return datetime.datetime.strptime(str(value), default_format).astimezone(datetime.UTC)
            except ValueError:
                raise Exception("The input date does not match the ISO 8601 format with or without offset.")

        return datetime.datetime.strptime(str(value), format).astimezone(datetime.UTC)

    def datetime_format(value, format=None):
        if format is None:
            format = default_format_with_offset
        return value.strftime(format)

    env.filters["datetime_format"] = datetime_format
    env.filters["datetime_parse"] = datetime_parse
