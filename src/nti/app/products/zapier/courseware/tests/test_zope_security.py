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

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager

from zope.securitypolicy.settings import Allow

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contenttypes.courses.courses import CourseAdministrativeLevel
from nti.contenttypes.courses.courses import CourseInstance

from nti.contenttypes.courses.enrollment import DefaultCourseInstanceEnrollmentRecord

from nti.contenttypes.courses.interfaces import ICourseEnrollmentManager
from nti.contenttypes.courses.interfaces import ICourseEnrollments

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.authorization_utils import zope_interaction

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site


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

            # Just need to ensure it's under the site, somewhere
            admin_level = CourseAdministrativeLevel()
            getSite().getSiteManager()['admin'] = admin_level
            course = CourseInstance()
            admin_level['course'] = course

            ICourseEnrollmentManager(course).enroll(joe)
            record = ICourseEnrollments(course).get_enrollment_for_principal(joe)

            with zope_interaction(joe.username):
                assert_that(checkPermission(ACT_READ.id, course), is_(False))
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(site_admin.username):
                assert_that(checkPermission(ACT_READ.id, course), is_(True))
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(nti_admin.username):
                assert_that(checkPermission(ACT_READ.id, course), is_(True))
                assert_that(checkPermission(ACT_READ.id, record), is_(True))

            with zope_interaction(not_joe.username):
                assert_that(checkPermission(ACT_READ.id, course), is_(False))
                assert_that(checkPermission(ACT_READ.id, record), is_(False))

            ppm = IPrincipalPermissionManager(record)
            principals = ppm.getPrincipalsForPermission(ACT_READ.id)
            assert_that(principals, has_length(1))
            assert_that(principals, contains((joe.username, Allow)))

            ppm = IRolePermissionManager(course)
            roles = ppm.getRolesForPermission(ACT_READ.id)
            assert_that(roles, has_length(1))
            assert_that(roles, contains((ROLE_ADMIN.id, Allow)))

            # If the record has no Principal, possible given the interface
            # specifies Principal as optional
            record = DefaultCourseInstanceEnrollmentRecord()

            ppm = IPrincipalPermissionManager(record)
            principals = ppm.getPrincipalsForPermission(ACT_READ.id)
            assert_that(principals, has_length(0))

