# -*- coding: utf-8 -*-
#
# cli.py
# ==================
#
# Christian Werner
# christian.werner@kit.edu

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

from ldndctools import __version__

log = logging.getLogger(__name__)


class VerbosityAction(argparse.Action):
    """ CustomAction for argparse that increases the log level """

    def __init__(self, nargs=0, **kw):
        argparse.Action.__init__(self, nargs=nargs, **kw)

    def __call__(self, parser, namespace, values=None, option_string=None):
        handlers = logging.getLogger().handlers
        for handler in handlers:
            if type(handler) is logging.StreamHandler:
                handler.setLevel(logging.DEBUG)
        setattr(namespace, self.dest, True)


class RangeAction(argparse.Action):
    """ CustomAction for argparse to be able to process value range """

    def __call__(self, parser, namespace, values, option_string=None):
        s = values.split("-")

        def is_valid_year_range(s):
            if len(s) > 2:
                return False
            for e in s:
                try:
                    _ = int(e)
                except ValueError:
                    return False
            if int(s[1]) < int(s[0]):
                return False
            return True

        if is_valid_year_range(s):
            setattr(namespace, self.dest, range(int(s[0]), int(s[-1]) + 1))
        else:
            log.critical("No valid range: %s" % values)
            exit(1)


class MultiArgsAction(argparse.Action):
    """ CustomAction for argparse to be able to process ,-seperated args """

    def __init__(self, **kw):
        argparse.Action.__init__(self, **kw)
        self._nsegs = self.const  # misuse of const to carry len(segs)

    def __call__(self, parser, namespace, values, option_string=None):
        s = values.split(",")
        if len(s) == self._nsegs:
            setattr(namespace, self.dest, tuple(s))
        else:
            log.critical("Syntax error in %s" % option_string)
            exit(1)


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    def _get_help_string(self, action):
        help = action.help
        if "%(default)" not in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    if type(action.default) == list:
                        help += " (default: %d-%d)" % (
                            action.default[0],
                            action.default[-1],
                        )
                    else:
                        help += " (default: %(default)s)"
        return help


def cli():
    """ command line interface """

    DESCR = f"dlsc :: LandscapeDNDC Site Creator ({__version__})"

    GREETING = "\n".join(["-" * 78, DESCR, "-" * 78])

    EPILOG = "Use this tool to build XML LDNDC site files\n"

    parser = argparse.ArgumentParser(
        description=DESCR, epilog=EPILOG, formatter_class=CustomFormatter
    )

    parser.add_argument("outfile", default=None, nargs="?", help="output xml file")

    parser.add_argument(
        "-b",
        "--bbox",
        dest="bbox",
        default=None,
        metavar="[X1,Y1,X2,Y2]",
        help="bounding box for netCDF output",
    )

    parser.add_argument(
        "-c", dest="config", metavar="MYCONF", help="use MYCONF file as config"
    )

    # parser.add_argument(
    #     "--no-extra-split",
    #     action="store_true",
    #     dest="noextrasplit",
    #     default=False,
    #     help="do not subdivide the first soil layer",
    # )

    parser.add_argument(
        "--gui",
        action="store_true",
        dest="gui",
        default=False,
        help="start the web-GUI",
    )

    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        default=None,
        metavar="FILE",
        help="optional location file with lat lon coords",
    )

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        dest="interactive",
        default=False,
        help="select regions or countries",
    )

    parser.add_argument(
        "-r",
        "--res",
        dest="resolution",
        default="HR",
        metavar="LR, MR, HR",
        type=str.upper,
        help="data res (0.083, 0.25, 0.5)",
    )

    parser.add_argument(
        "--region",
        dest="rcode",
        default=None,
        help="for non-interactive exec give country or region code(s) [chain with +]",
    )

    parser.add_argument(
        "-S",
        dest="storeconfig",
        action="store_true",
        default=False,
        help="make passed config (-c) the new default",
    )

    parser.add_argument(
        "-v",
        dest="verbose",
        action=VerbosityAction,
        default=False,
        help="increase output verbosity",
    )

    print(GREETING)

    args = parser.parse_args()

    log.debug("-" * 50)
    log.debug("ldndctools::dlsc called at: %s" % dt.datetime.now())

    if args.storeconfig and (args.config is None):
        log.critical("Option -S requires that you pass a file with -c.")
        exit(1)

    if args.gui:
        try:
            from streamlit import cli as stcli

            file_path = str(Path(__file__).parent / ".." / "dlsc-gui.py")
            sys.argv = ["streamlit", "run", file_path]
            sys.exit(stcli.main())
        except ModuleNotFoundError:
            print("Module 'Streamlit' is not installed. GUI not available")
            sys.exit(1)

    return args
