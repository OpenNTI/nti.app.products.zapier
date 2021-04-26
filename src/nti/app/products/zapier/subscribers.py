#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope.event import notify

from zope.lifecycleevent import IObjectAddedEvent

from zope.securitypolicy.interfaces import IRolePermissionManager

from nti.app.products.zapier.interfaces import IZapierUserProgressUpdatedEvent

from nti.contenttypes.completion.interfaces import IUserProgressUpdatedEvent

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.webhooks.interfaces import IWebhookSubscription


_DEFAULT_PERMISSIONS = (
    'zope.View',
    'nti.actions.delete',
)


@component.adapter(IWebhookSubscription, IObjectAddedEvent)
def apply_security_to_subscription(subscription, _event):
    role_per = IRolePermissionManager(subscription)
    for perm_id in _DEFAULT_PERMISSIONS:
        # TODO: What about platform admins?  They currently have no access
        #  either.  Should that be granted?
        role_per.denyPermissionToRole(perm_id, ROLE_SITE_ADMIN.id)


@component.adapter(ICourseInstance, IUserProgressUpdatedEvent)
def _handle_progress_update(_unused_course, event):
    # Convert to internal event more conducive to the permission
    # checks performed by nti.webhooks, since ICourseInstance seems
    # insufficient a check for progress specific to both a user and course
    zapier_event = IZapierUserProgressUpdatedEvent(event)
    notify(zapier_event)
