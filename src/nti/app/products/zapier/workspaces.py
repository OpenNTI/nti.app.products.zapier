#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of an Atom/OData workspace and collection for badges.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.appserver.workspaces import IWorkspace
from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.zapier import ZAPIER
from nti.app.products.zapier import AUTH_USERS_PATH

from nti.app.products.zapier.interfaces import IZapierWorkspace

from nti.appserver.workspaces.interfaces import IUserService

from nti.links.links import Link

from nti.property.property import alias

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IZapierWorkspace)
class _ZapierWorkspace(Contained):

    __name__ = ZAPIER
    name = alias('__name__', __name__)

    def __init__(self, user_service):
        self.context = user_service
        self.user = user_service.user

    @Lazy
    def collections(self):
        return ()

    @property
    def links(self):
        site_auth = component.getUtility(ISiteAuthentication)

        create_user = Link(site_auth,
                           rel='create_user',
                           method='POST',
                           elements=(AUTH_USERS_PATH,))
        return (create_user,)

    def __getitem__(self, key):
        """
        Make us traversable to collections.
        """
        # pylint: disable=not-an-iterable
        for i in self.collections:
            if i.__name__ == key:
                return i
        raise KeyError(key)

    def __len__(self):
        return len(self.collections)


@interface.implementer(IZapierWorkspace)
@component.adapter(IUserService)
def ZapierWorkspace(user_service):
    """
    The Zapier workspace resides at the path ``/users/$ME/Zapier``.
    """
    workspace = _ZapierWorkspace(user_service)
    workspace.__parent__ = workspace.user
    return workspace


@interface.implementer(IWorkspace)
def _zapier_workspace_for_user(user, _unused_request):
    user_service = IUserService(user)
    if user_service is not None:
        ws = _ZapierWorkspace(user_service)
        ws.__parent__ = user
        return ws


