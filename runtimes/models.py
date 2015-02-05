# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mongoengine import (
    DictField,
    Document,
    IntField,
    StringField,
)


class Suite(Document):
    name = StringField(required=True)
    platform = StringField(required=True)
    buildid = StringField(required=True)
    revision = StringField(required=True)
    timestamp = IntField(required=True)
    runtimes = DictField(default={})
