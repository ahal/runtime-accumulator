# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from configman import Namespace, ConfigurationManager
from configman.environment import environment
from configman.command_line import command_line
from mozlog.structured.commandline import (
    log_formatters,
    fmt_options,
    setup_logging,
)

manager = None
config = None


def get_logging_namespace():
    logging = Namespace()
    for name, (cls, help_str) in log_formatters.iteritems():
        logging.add_option(
            name='{}'.format(name),
            doc=help_str,
            default=None)

    for optname, (cls, help_str, formatters, action) in \
            fmt_options.iteritems():
        for fmt in formatters:
            if fmt in log_formatters:
                logging.add_option(
                    name='{}-{}'.format(fmt, optname),
                    doc=help_str,
                    default=None)
    return logging


def get_logger():
    log = {'log_{}'.format(k.replace('-', '_')): v for k, v in dict(
        config.log).iteritems()}
    return setup_logging('test-runtimes', log)


def define_config(**spaces):
    ns = Namespace()
    for k, v in spaces.iteritems():
        setattr(ns, k, v)

    ns.db = Namespace()
    ns.db.add_option(
        name='database',
        default='runtimes',
        doc="Database to connect to",
    )
    ns.db.add_option(
        name='host',
        default='localhost',
        doc="Database host",
    )
    ns.db.add_option(
        name='port',
        default=27017,
        doc="Database port",
    )

    global log_formatters
    log_formatters = {k: v for k, v in log_formatters.iteritems()
                      if k in ('raw', 'mach')}
    ns.log = get_logging_namespace()

    global manager
    global config
    sources = [
        os.path.expanduser('~/.runtimes.ini'),
        environment,
        command_line
    ]
    manager = ConfigurationManager(ns, values_source_list=sources)
    config = manager.get_config()

    # misc things
    config.dot_escape = '&dot;'


def get_config(**spaces):
    if config is None:
        define_config(**spaces)
    return config

# a mapping from suite name to dict containing manifest path and parser type
SUITES = {
    'mochitest-browser-chrome': {
        'names':  ["mochitest-browser-chrome", "mochitest-bc"],
    },
    'mochitest-browser-chrome-e10s': {
        'names': ["mochitest-browser-chrome-e10s",
                  "mochitest-e10s-browser-chrome",
                  "mochitest-bc-e10s"],
    },
    'mochitest-devtools-chrome': {
        'names': ['mochitest-devtools-chrome'],
    },
    'mochitest-e10s-devtools-chrome': {
        'names': ['mochitest-e10s-devtools-chrome'],
    },
    'mochitest-gl': {
        'names': ['mochitest-gl'],
    },
    'mochitest-plain-e10s': {
        'names': ['mochitest-e10s'],
    },
    'mochitest-plain': {
        'names': ['mochitest', 'mochitest-debug'],
    },
}

# a mapping from plaform type to enabled suites.
PLATFORMS = {
    'linux-opt': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain-e10s',
        'mochitest-plain',
    ],
    'linux-debug': [
        'mochitest-browser-chrome',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain-e10s',
        'mochitest-plain',
    ],
    'linux64-opt': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-devtools-chrome',
        'mochitest-e10s-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain-e10s',
        'mochitest-plain',
    ],
    'linux64_gecko-debug': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-plain-e10s',
        'mochitest-plain',
    ],
    'linux64-debug': [
        'mochitest-browser-chrome',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain-e10s',
        'mochitest-plain',
    ],
    'macosx64-opt': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'macosx64-debug': [
        'mochitest-browser-chrome',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'macosx64_gecko-opt': [
        'mochitest-browser-chrome',
        'mochitest-plain',
    ],
    'win32-opt': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'win32-debug': [
        'mochitest-browser-chrome',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'win64-opt': [
        'mochitest-browser-chrome',
        'mochitest-browser-chrome-e10s',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'win64-debug': [
        'mochitest-browser-chrome',
        'mochitest-devtools-chrome',
        'mochitest-gl',
        'mochitest-plain',
    ],
    'android-api-9-opt': [
        'mochitest-plain',
        'mochitest-gl',
    ],
    'android-api-11-opt': [
        'mochitest-plain',
        'mochitest-gl',
    ],
    'android-api-11-debug': [
        'mochitest-plain',
    ],
    'linux32_gecko-opt': [
        'mochitest-plain',
    ],
    'linux64_gecko-opt': [
        'mochitest-plain',
    ],
    'emulator-opt': [
        'mochitest-plain',
    ],
    'emulator-debug': [
        'mochitest-plain',
    ],
    'mulet-opt': [
        'mochitest-plain',
    ],
}
