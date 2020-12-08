#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from nti.coremetadata.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.authorization import ACT_CREATE
from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL


@interface.implementer(IPathAdapter)
class APIPathAdapter(Contained):

    __name__ = 'api'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context


@interface.implementer(IPathAdapter)
class IntegrationProviderPathAdapter(Contained):

    __name__ = "zapier"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

        request._integration_provider = self.__name__

    def __acl__(self):
        acl = [ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, type(self)),
               ACE_DENY_ALL]
        result = acl_from_aces(acl)
        return result


@interface.implementer(IPathAdapter)
class SubscriptionsPathAdapter(Contained):

    __name__ = "subscriptions"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    def __acl__(self):
        site_admin_perms = (ACT_CREATE, ACT_READ)
        acl = [ace_allowing(ROLE_SITE_ADMIN, site_admin_perms, type(self)),
               ACE_DENY_ALL]
        result = acl_from_aces(acl)
        return result


def get_integration_provider(request):
    return getattr(request, "_integration_provider", None)