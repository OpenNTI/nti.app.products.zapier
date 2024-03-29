#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of an Atom/OData workspace and collection for badges.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.courseware.interfaces import IAvailableCoursesProvider

from nti.app.products.zapier import AUTH_USERS_PATH
from nti.app.products.zapier import ENROLLMENTS_PATH
from nti.app.products.zapier import SUBSCRIPTIONS_VIEW
from nti.app.products.zapier import USER_SEARCH
from nti.app.products.zapier import ZAPIER
from nti.app.products.zapier import ZAPIER_PATH

from nti.app.products.zapier.interfaces import IZapierWorkspace

from nti.app.products.zapier.courseware.interfaces import IZapierCourseCatalogCollection

from nti.appserver.workspaces import IWorkspace

from nti.appserver.workspaces.interfaces import IUserService

from nti.contenttypes.courses.interfaces import ICourseCatalog

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.authorization_acl import has_permission

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict

from nti.links.links import Link

from nti.property.property import alias

COURSES_COLLECTION = 'Courses'

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
        return (ZapierCourseCatalogCollection(self),)

    def _ds_folder(self):
        return component.getUtility(IDataserver).dataserver_folder

    @property
    def links(self):
        links = list()
        links.append(Link(self._ds_folder(),
                          rel='resolve_me',
                          method='GET',
                          elements=(ZAPIER_PATH,
                                    "resolve_me")))

        links.append(Link(self[COURSES_COLLECTION],
                          rel='course_search',
                          method='GET'))

        site_auth = component.queryUtility(ISiteAuthentication)
        if site_auth is not None:
            username = self.user.username
            if has_permission(nauth.ACT_MANAGE_SITE, site_auth, username):
                links.append(Link(site_auth,
                                  rel='create_user',
                                  method='POST',
                                  elements=(AUTH_USERS_PATH,)))

            if has_permission(nauth.ACT_SEARCH, site_auth, username):
                links.append(Link(site_auth,
                                  rel=USER_SEARCH,
                                  method='GET',
                                  elements=(USER_SEARCH,)))

        if is_admin(self.user):
            # Although views are permissioned to site admins as well,
            # expose link to only NTI admins for now (to drive UI).
            links.append(Link(self._ds_folder(),
                              rel=SUBSCRIPTIONS_VIEW,
                              method='GET',
                              elements=(ZAPIER_PATH,
                                        SUBSCRIPTIONS_VIEW)))

        if is_admin_or_site_admin(self.user):
            links.append(Link(self._ds_folder(),
                              rel='create_subscription',
                              method='POST',
                              elements=(ZAPIER_PATH,
                                        SUBSCRIPTIONS_VIEW)))
            links.append(Link(self._ds_folder(),
                              rel='enroll_user',
                              method='POST',
                              elements=(ZAPIER_PATH,
                                        ENROLLMENTS_PATH)))
        return tuple(links)

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


@interface.implementer(IZapierCourseCatalogCollection)
class ZapierCourseCatalogCollection(Contained):
    """
    Provides context for view and available courses for course search
    """
    name = COURSES_COLLECTION
    __name__ = name

    _workspace = alias('__parent__')
    accepts = ()
    links = ()

    def __init__(self, zapier_workspace):
        self.__parent__ = zapier_workspace

    class _IteratingDict(LocatedExternalDict):
        # BWC : act like a dict, but iterate like a list
        _v_container_ext_as_list = True

        def __iter__(self):
            return iter(self.values())

    def __init__(self, parent):
        self.__parent__ = parent

    @Lazy
    def catalog(self):
        return component.queryUtility(ICourseCatalog)

    @Lazy
    def available_entries(self):
        """
        Return a dict of course catalog entries the user is not enrolled
        in and that are available to be enrolled in.
        """
        course_provider = IAvailableCoursesProvider(self.__parent__.user)
        result = self._IteratingDict()
        for entry in course_provider.get_available_entries():
            result[entry.ntiid] = entry
        return result

    @Lazy
    def container(self):
        container = self.available_entries
        container.__name__ = self.catalog.__name__
        container.__parent__ = self.catalog.__parent__
        container.lastModified = self.catalog.lastModified
        return container

    def __len__(self):
        return len(self.container)
