#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.security.permission import Permission

#: Can receive events for the associated object
ACT_VIEW_EVENTS = Permission('nti.actions.view_events')
