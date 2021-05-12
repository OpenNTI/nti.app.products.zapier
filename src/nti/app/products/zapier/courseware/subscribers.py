#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope.event import notify

from nti.app.products.zapier.courseware.interfaces import IZapierUserProgressUpdatedEvent

from nti.contenttypes.completion.interfaces import IUserProgressUpdatedEvent

from nti.contenttypes.courses.interfaces import ICourseInstance


@component.adapter(ICourseInstance, IUserProgressUpdatedEvent)
def _handle_progress_update(_unused_course, event):
    # Convert to internal event more conducive to the permission
    # checks performed by nti.webhooks, since ICourseInstance seems
    # insufficient a check for progress specific to both a user and course
    zapier_event = IZapierUserProgressUpdatedEvent(event)
    notify(zapier_event)
