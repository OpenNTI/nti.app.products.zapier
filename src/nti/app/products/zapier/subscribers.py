#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component

from zope.lifecycleevent import IObjectAddedEvent

from zope.securitypolicy.interfaces import IRolePermissionManager

from nti.dataserver.authorization import ROLE_ADMIN
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
        role_per.denyPermissionToRole(perm_id, ROLE_SITE_ADMIN.id)
        role_per.grantPermissionToRole(perm_id, ROLE_ADMIN.id)
