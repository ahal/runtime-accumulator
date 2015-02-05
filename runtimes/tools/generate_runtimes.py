# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
import json
import os
import sys

from configman import Namespace
import mongoengine

from ..config import (
    get_config,
    get_logger,
    PLATFORMS,
)
from ..models import Suite


config = None
logger = None


class SumCount(object):
    def __init__(self):
        self.count = 0
        self.total = 0

    def __iadd__(self, item):
        self.count += 1
        self.total += item
        return self


def generate_runtimes(platform, suite, points=5, threshold=0):
    logger.info("Generating runtimes for {} on {}".format(suite, platform))
    suites = Suite.objects(name=suite,
                           platform=platform).order_by('-timestamp')[:points]

    tally = defaultdict(SumCount)

    def sum_values(other):
        for k, v in other.iteritems():
            tally[k] += v
    map(sum_values, [s.runtimes for s in suites])

    return {k.replace(config.dot_escape, '.'): v.total/v.count for k, v in
            tally.iteritems() if v.total/v.count >= threshold}


def run():
    gen = Namespace()
    gen.add_option(name='points',
                   default=5,
                   doc="Number of data points to average")
    gen.add_option(name='threshold',
                   default=0,
                   doc="Exclude tests below the specified runtime threshold "
                       "(in ms)")
    gen.add_option(name='outdir',
                   default=os.path.join(os.getcwd(), 'runtime_output'),
                   doc="Directory to store test runtime files")
    global config
    config = get_config(gen=gen)

    global logger
    logger = get_logger()

    db = config.db
    logger.debug("Connecting to {} on '{}:{}'".format(
        db.database, db.host, db.port))
    mongoengine.connect(db.database, host=db.host, port=db.port)

    gen = config.gen
    for platform, suites in PLATFORMS.iteritems():
        for suite in suites:
            runtimes = generate_runtimes(
                platform, suite, points=gen.points, threshold=gen.threshold)
            filename = '{}.runtimes.json'.format(suite)
            pdir = os.path.join(gen.outdir, platform)
            if not os.path.isdir(pdir):
                os.makedirs(pdir)
            with open(os.path.join(pdir, filename), 'w') as f:
                f.write(json.dumps(runtimes))


if __name__ == '__main__':
    sys.exit(run())
