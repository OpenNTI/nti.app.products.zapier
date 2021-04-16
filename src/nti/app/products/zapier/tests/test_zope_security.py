#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import has_length
from hamcrest import is_

from zope.component.hooks import getSite
from zope.security import checkPermission
from zope.securitypolicy.interfaces import IPrincipalPermissionManager

from zope.securitypolicy.interfaces import IPrincipalPermissionMap
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager

from zope.securitypolicy.settings import Allow
from zope.securitypolicy.settings import Unset

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contenttypes.courses.enrollment import DefaultCourseInstanceEnrollmentRecord

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.authorization_utils import zope_interaction

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site


class TestUserPrincipalPermissionMap(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=("site.admin",
                                        "diff.site.admin",
                                        "not.site.admin"))
    def test_mixed_admins(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            # A user that can administer "not.site.admin"
            admin = self._get_user('site.admin')
            site = getSite()
            site_name = site.__name__
            set_user_creation_site(admin, site_name)
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, admin.username)

            # A user that cannot administer "not.site.admin"
            diff_site_admin = self._get_user('diff.site.admin')
            set_user_creation_site(diff_site_admin, 'janux.ou.edu')
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME,
                                      diff_site_admin.username)

            # User to check against
            not_admin = self._get_user('not.site.admin')
            set_user_creation_site(not_admin, site_name)

            ppm = IPrincipalPermissionMap(not_admin)
            principals = ppm.getPrincipalsForPermission(ACT_VIEW_EVENTS.id)
            assert_that(principals, has_length(1))
            assert_that(principals, contains((admin.username, Allow)))

            perms = ppm.getPermissionsForPrincipal(admin.username)
            assert_that(perms, has_length(1))
            assert_that(perms, contains((ACT_VIEW_EVENTS.id, Allow)))

            perms = ppm.getPermissionsForPrincipal(diff_site_admin.username)
            assert_that(perms, has_length(0))

            setting = ppm.getSetting(ACT_VIEW_EVENTS.id, admin.username)
            assert_that(setting, is_(Allow))

            setting = ppm.getSetting(ACT_VIEW_EVENTS.id, diff_site_admin.username)
            assert_that(setting, is_(Unset))

            prin_perms = ppm.getPrincipalsAndPermissions()
            assert_that(prin_perms, has_length(1))
            assert_that(prin_perms, contains((admin.username, ACT_VIEW_EVENTS.id, Allow)))

            # Our diff site user should be able to admin themselves
            ppm = IPrincipalPermissionMap(diff_site_admin)
            principals = ppm.getPrincipalsForPermission(ACT_VIEW_EVENTS.id)
            assert_that(principals, has_length(1))
            assert_that(principals, contains((diff_site_admin.username, Allow)))

            perms = ppm.getPermissionsForPrincipal(admin.username)
            assert_that(perms, has_length(0))

            perms = ppm.getPermissionsForPrincipal(diff_site_admin.username)
            assert_that(perms, has_length(1))
            assert_that(perms, contains((ACT_VIEW_EVENTS.id, Allow)))

            setting = ppm.getSetting(ACT_VIEW_EVENTS.id, admin.username)
            assert_that(setting, is_(Unset))

            setting = ppm.getSetting(ACT_VIEW_EVENTS.id, diff_site_admin.username)
            assert_that(setting, is_(Allow))

            prin_perms = ppm.getPrincipalsAndPermissions()
            assert_that(prin_perms, has_length(1))
            assert_that(prin_perms, contains((diff_site_admin.username, ACT_VIEW_EVENTS.id, Allow)))

    @WithSharedApplicationMockDS(users=("alpha.user.1",
                                        "diff-site.user",
                                        "alpha.user.2"))
    def test_no_admins(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            site = getSite()
            site_name = site.__name__

            alpha_one = self._get_user('alpha.user.1')
            set_user_creation_site(alpha_one, site_name)
            diff_site_user = self._get_user('diff-site.user')
            set_user_creation_site(diff_site_user, 'diff-site')
            alpha_two = self._get_user('alpha.user.2')
            set_user_creation_site(alpha_two, site_name)

            ppm = IPrincipalPermissionMap(alpha_two)
            principals = ppm.getPrincipalsForPermission(ACT_VIEW_EVENTS.id)
            assert_that(principals, has_length(0))

            perms = ppm.getPermissionsForPrincipal(alpha_one.username)
            assert_that(perms, has_length(0))

            setting = ppm.getSetting(ACT_VIEW_EVENTS.id, alpha_one.username)
            assert_that(setting, is_(Unset))

            prin_perms = ppm.getPrincipalsAndPermissions()
            assert_that(prin_perms, has_length(0))


class TestEnrollmentRecordPermissions(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=("site.admin",
                                        "nti.admin",
                                        "regular.joe",
                                        "not.regular.joe"))
    def test_permissions(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            # A site admin w/ access to everything under site
            site_admin = self._get_user('site.admin')
            site = getSite()
            site_name = site.__name__
            set_user_creation_site(site_admin, site_name)
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, site_admin.username)

            # An nti admin (nti.admin) w/ no principal permissions
            nti_admin = self._get_user('nti.admin')
            self._assign_role(ROLE_ADMIN, username=nti_admin.username)

            # Owning user
            joe = self._get_user('regular.joe')
            set_user_creation_site(joe, site_name)

            # Not owning user
            not_joe = self._get_user('not.regular.joe')
            set_user_creation_site(not_joe, site_name)

            record = DefaultCourseInstanceEnrollmentRecord(Principal=joe)

            # Just need to ensure it's under the site, somewhere
            record.__parent__ = getSite().getSiteManager()

            with zope_interaction(joe.username):
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(site_admin.username):
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(nti_admin.username):
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(not_joe.username):
                assert_that(checkPermission(ACT_READ.id, record), is_(False))

            ppm = IPrincipalPermissionManager(record)
            principals = ppm.getPrincipalsForPermission(ACT_READ.id)
            assert_that(principals, has_length(1))
            assert_that(principals, contains((joe.username, Allow)))

            ppm = IRolePermissionManager(record)
            roles = ppm.getRolesForPermission(ACT_READ.id)
            assert_that(roles, has_length(1))
            assert_that(roles, contains((ROLE_ADMIN.id, Allow)))
