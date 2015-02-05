# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import OrderedDict
from Queue import Queue
import re
import threading
import traceback

from mozlog.structured import reader
import mozfile
import requests

from .config import (
    get_config,
    get_logger,
    SUITES,
    PLATFORMS,
)
from .models import Suite


# save tests bundles so we don't have to download a new one for each platform
tests_cache = OrderedDict()
build_queue = Queue(maxsize=100)

config = None
logger = None

INSTALLER_SUFFIXES = ('.tar.bz2', '.zip', '.dmg', '.exe', '.apk', '.tar.gz')

lock = threading.Lock()


class RuntimeHandler(reader.LogHandler):
    runtimes = {}
    start_time = None

    def test_start(self, data):
        self.start_time = data['time']

    def test_end(self, data):
        runtime = data['time'] - self.start_time
        self.runtimes[data['test'].replace('.', config.dot_escape)] = runtime


class Worker(threading.Thread):
    """
    Class that repeatedly processes builds sent into the build_queue.
    Processing is as follows:

    1. Download tests bundle and build configuration file.
    2. Filter tests of all relevant suites to the platform.
    3. Save results to the database.
    """
    def __init__(self):
        threading.Thread.__init__(self, target=self.do_work)
        self.daemon = True

        global logger
        logger = get_logger()

        global config
        config = get_config()

    def do_work(self):
        while True:
            data = build_queue.get()  # blocking
            try:
                self.process_suite(data)
            except:
                # keep on truckin' on
                logger.error("encountered an exception:\n{}.".format(
                    traceback.format_exc()))
            build_queue.task_done()

    def process_suite(self, data):
        platform = '{}-{}'.format(data['platform'], data['buildtype'])
        build_str = "{}-{}".format(data['buildid'], platform)

        suite_name = self.get_suite_name(data['test'], platform)
        if not suite_name:
            return

        logs = [url for fn, url in data['blobber_files'].iteritems()
                if fn.endswith('_raw.log')]
        # return if there are no _raw.log files
        if not logs:
            return

        logger.debug("now processing build '{}'".format(build_str))
        handler = RuntimeHandler()
        for url in logs:
            log_path = self._prepare_mozlog(url)
            with open(log_path, 'r') as log:
                iterator = reader.read(log)
                reader.handle_log(iterator, handler)
            mozfile.remove(log_path)
        runtimes = handler.runtimes

        with lock:
            # create an entry for this build in the db
            suite, is_new = Suite.objects.get_or_create(
                name=suite_name,
                buildid=data['buildid'],
                platform=platform,
                timestamp=data['builddate'],
                revision=data['revision'],
            )
            suite.runtimes.update(runtimes)
            suite.save()

    def _download(self, url):
        r = requests.get(url)
        if r.status_code == 401:
            if hasattr(config, 'auth'):
                auth = (config.auth['user'], config.auth['password'])
                r = requests.get(url, auth=auth)
            else:
                logger.error("The url '{}' requires authentication!".format(
                    url))
        r.raise_for_status()
        return r.content

    def _prepare_mozlog(self, url):
        with mozfile.NamedTemporaryFile(prefix='ti', delete=False) as f:
            f.write(self._download(url))
            return f.name

    def get_suite_name(self, suite_chunk, platform):
        for suite in PLATFORMS[platform]:
            for name in SUITES[suite]['names']:
                possible = re.compile(name + '(-[0-9]+)?$')
                if possible.match(suite_chunk):
                    return suite
        return None
