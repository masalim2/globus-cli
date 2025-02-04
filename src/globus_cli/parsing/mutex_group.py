import functools
import typing

import click


class MutexInfo:
    def __init__(self, opt, param=None, present=None):
        self.option_name = opt
        if param:
            self.param_name = param
        else:
            self.param_name = opt.lstrip("-").replace("-", "_")
        self.is_present_callback = present

    def is_present(self, d):
        if self.is_present_callback is not None:
            return self.is_present_callback(d)
        val = d.get(self.param_name)
        # None for options with values, False for boolean flags
        # so we do normal "bool" conversion here
        return bool(val)

    def __str__(self):
        return self.option_name


def mutex_option_group(*options: typing.Union[str, MutexInfo]):
    """
    Given a mapping of param name to option string, decorate a command function to check
    for the exclusivity of those options.

    Options may be given as strings, in which case they are treated as the option name,
    leading hyphens are stripped and hyphens are converted to underscores for the param
    name. e.g.
        mutex_option_group("--foo-bar", "--baz-buzz")

    will assume the param names are "foo_bar" and "baz_buzz" respectively.

    Or, if this deduction would be incorrect, options may be given as MutexInfo objects.
    e.g.
        mutex_option_group("--foo-bar", MutexInfo("--baz-buzz", param="buzz"))

    to deduce param names of "foo_bar" and "buzz" respectively.

    MutexInfo allows you to customize how an option is detected as present in a
    dict of parameters by setting `present=...`.
    """
    opt_infos: typing.List[MutexInfo] = []
    for opt in options:
        if isinstance(opt, str):
            opt_infos.append(MutexInfo(opt))
        else:
            opt_infos.append(opt)

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            found_opts = []
            for opt in opt_infos:
                if opt.is_present(kwargs):
                    found_opts.append(opt)
            if len(found_opts) > 1:
                if len(opt_infos) == 2:
                    option_str = "{} and {}".format(*opt_infos)
                else:
                    option_str = ", ".join(opt_infos[:-1]) + f", and {opt_infos[-1]}"
                raise click.UsageError(f"{option_str} are mutually exclusive")
            return func(*args, **kwargs)

        return wrapped

    return decorator
