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

from nti.dataserver.interfaces import ISiteAdminUtility


@component.adapter(IUser)
@interface.implementer(IPrincipalPermissionMap)
class UserPrincipalPermissionMap(object):
    """
    Ensure our site admins have access to users in their site
    e.g. for checking user object access when sending webhooks created
    by the site admin
    """

    SITE_ADMIN_PERM_IDS = (ACT_VIEW_EVENTS.id,)

    def __init__(self, context):
        self.context = context

    @Lazy
    def siteAdminUtility(self):
        return component.getUtility(ISiteAdminUtility)

    def _can_admin(self, site_admin):
        return self.siteAdminUtility.can_administer_user(site_admin,
                                                         self.context)

    @Lazy
    def _effectiveAdminsForUser(self):
        return [site_admin.username for site_admin in get_site_admins()
                if self._can_admin(site_admin)]

    def getPrincipalsForPermission(self, perm):
        result = []
        if perm in self.SITE_ADMIN_PERM_IDS:
            for principal_id in self._effectiveAdminsForUser:
                result.append((principal_id, Allow))
        return result

    def getPermissionsForPrincipal(self, principal_id):
        if principal_id in self._effectiveAdminsForUser:
            return [(perm, Allow) for perm in self.SITE_ADMIN_PERM_IDS]

        return []

    def getSetting(self, permission_id, principal_id, default=Unset):
        if permission_id in self.SITE_ADMIN_PERM_IDS:
            if principal_id in self._effectiveAdminsForUser:
                return Allow

        return default

    def getPrincipalsAndPermissions(self):
        result = []
        for principal_id in self._effectiveAdminsForUser:
            for perm in self.SITE_ADMIN_PERM_IDS:
                result.append((principal_id, perm, Allow))

        return result
