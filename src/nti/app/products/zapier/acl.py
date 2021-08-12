#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.coremetadata.interfaces import IACLProvider

from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL

from nti.webhooks.interfaces import IWebhookSubscription


@interface.implementer(IACLProvider)
@component.adapter(IWebhookSubscription)
class SubscriptionACLProvider(object):
    """
    Permissioning is via zope
    """

    def __init__(self, context):
        self.context = context

    @property
    def __parent__(self):
        # See comments in nti.dataserver.authorization_acl:has_permission
        return self.context.__parent__

    @Lazy
    def __acl__(self):
        return acl_from_aces([ACE_DENY_ALL])