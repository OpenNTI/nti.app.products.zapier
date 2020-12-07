#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import IPrincipalPermissionMap

from zope.securitypolicy.settings import Unset

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS

from nti.app.users.utils import get_site_admins

from nti.coremetadata.interfaces import IUser


@component.adapter(IUser)
@interface.implementer(IPrincipalPermissionMap)
class UserPrincipalPermissionMap(object):

    SITE_ADMIN_PERM_IDS = (ACT_VIEW_EVENTS.id,)

    def __init__(self, context):
        self.context = context

    @Lazy
    def _adminsForCurrentSite(self):
        return [user.username for user in get_site_admins()]

    def getPrincipalsForPermission(self, perm):
        # Ensure our site admins have access to users in their site
        # e.g. for checking user object access when sending webhooks created
        # by the site admin
        result = []
        if perm in self.SITE_ADMIN_PERMS:
            for principal_id in self._adminsForCurrentSite:
                # TODO: Do we need to check that the principal can admin
                #   the user in self.context?
                result.append((principal_id, Allow))
        return result

    def getPermissionsForPrincipal(self, principal_id):
        if principal_id in self._adminsForCurrentSite:
            return [(perm, Allow) for perm in self.SITE_ADMIN_PERM_IDS]

        return []

    def getSetting(self, permission_id, principal_id, default=Unset):
        if permission_id in self.SITE_ADMIN_PERM_IDS:
            if principal_id in self._adminsForCurrentSite:
                return Allow

        return default

    def getPrincipalsAndPermissions(self):
        result = []
        for principal_id in self._adminsForCurrentSite:
            for perm in self.SITE_ADMIN_PERM_IDS:
                result.append((perm, principal_id, Allow))
