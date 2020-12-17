#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.externalization.interfaces import ExternalizationPolicy


#: An externalization policy that uses ISO 8601 date strings.
ISODateExternalizationPolicy = ExternalizationPolicy(
    use_iso8601_for_unix_timestamp=True
)