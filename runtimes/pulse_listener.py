#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

from multiprocessing import cpu_count
from Queue import Full
import json
import signal
import sys
import time
import traceback
import uuid

from configman import Namespace
from mozillapulse.consumers import NormalizedBuildConsumer
import mongoengine

from .config import (
    get_config,
    get_logger,
    PLATFORMS,
)
from .worker import (
    Worker,
    build_queue,
)

config = None
logger = None


def on_build_event(data, message):
    # ack the message to remove it from the queue
    message.ack()
    payload = data['payload']
    platform = '{}-{}'.format(payload['platform'], payload['buildtype'])

    skip = None
    if 'blobber_files' not in payload:
        skip = "there are no blobber files"
    elif platform not in PLATFORMS:
        skip = "platform not configured"

    if skip:
        logger.debug("Skipping '{}' build, because {}".format(platform, skip))
        return

    logger.debug("Recieved build from pulse:\n{}".format(
        json.dumps(payload, indent=2)))
    logger.info("Processing a '{}' build from revision {}".format(
        platform, payload['revision']))
    try:
        build_queue.put(payload, block=False)
    except Full:
        # if backlog is too big, discard oldest build
        discarded = build_queue.get()
        logger.warning("Did not process buildid '{}', backlog too big!".format(
            discarded['buildid']))
        build_queue.put(payload, block=False)


def run(args=sys.argv[1:]):
    pulse = Namespace()
    pulse.add_option(
        name='user',
        default=None,
        doc="Pulse username",
    )
    pulse.add_option(
        name='password',
        default=None,
        doc="Pulse password",
    )
    pulse.add_option(
        name='applabel',
        default='test-runtimes',
        doc="Pulse app label",
    )
    pulse.add_option(
        name='durable',
        default=False,
        doc="Use a durable queue",
    )

    settings = Namespace()
    settings.add_option(
        name='branch',
        default='mozilla-inbound',
        doc="Tree to listen on",
    )
    settings.add_option(
        name='num_workers',
        default=cpu_count(),
        doc="Number of threads to use for workers",
    )
    global config
    config = get_config(pulse=pulse, settings=settings)

    global logger
    logger = get_logger()
    logger.info("Gathering test runtimes")

    # Connect to db
    db = config.db
    logger.debug("Connecting to {} on '{}:{}'".format(
        db.database, db.host, db.port))
    mongoengine.connect(db.database, host=db.host, port=db.port)

    # Start worker threads
    settings = config.settings
    logger.debug("Spawning {} worker threads".format(settings.num_workers))
    for _ in range(settings.num_workers):
        worker = Worker()
        worker.start()

    label = 'test-runtimes-{}'.format(uuid.uuid4())
    topic = 'unittest.{}.#'.format(settings.branch)

    # defaults
    pulse_args = {
        'applabel': label,
        'topic': topic,
        'durable': False,
    }
    pulse_args.update(config.pulse)

    def cleanup(sig=None, frame=None):
        # delete the queue if durable set with a unique applabel
        if pulse_args['durable'] and pulse_args['applabel'] == label:
            pulse.delete_queue()
        sys.exit(0)
    signal.signal(signal.SIGTERM, cleanup)

    # Connect to pulse
    sanitized_args = pulse_args.copy()
    if 'password' in sanitized_args:
        sanitized_args['password'] = 'hunter1'
    logger.debug("Connecting to pulse with the following arguments:\n"
                 "{}".format(json.dumps(sanitized_args, indent=2)))

    pulse = NormalizedBuildConsumer(callback=on_build_event, **pulse_args)
    try:
        while True:
            logger.info("Listening on '{}'...".format(pulse_args['topic']))
            try:
                pulse.listen()
            except KeyboardInterrupt:
                raise
            except IOError:
                pass  # these are common and not worth logging
            except:  # keep on listening
                logger.warning(traceback.format_exc())
    except KeyboardInterrupt:
        logger.info("Waiting for threads to finish processing {} builds, "
                    "press Ctrl-C again to exit now...".format(
                        build_queue.unfinished_tasks))
        try:
            # do this instead of Queue.join() so KeyboardInterrupts get caught
            while build_queue.unfinished_tasks:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(1)
    finally:
        logger.info("Threads finished, cleaning up...")
        cleanup()


if __name__ == "__main__":
    sys.exit(run())
