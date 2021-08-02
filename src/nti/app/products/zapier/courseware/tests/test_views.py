#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import shutil

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length

from zope import component

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.zapier.courseware.model import CourseCreatedEvent
from nti.app.products.zapier.courseware.model import CourseDetails

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site

from nti.ntiids.ntiids import find_object_with_ntiid


class TestSubscriptions(ApplicationLayerTest, ZapierTestMixin):

    layer = PersistentInstructedCourseApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    def _create_subscription(self, obj_type, event_type, target_url, **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        base_create_path = self.get_workspace_link('create_subscription',
                                                   **workspace_kwargs)

        path = b'/'.join(filter(None, (base_create_path, obj_type, event_type)))
        res = self.testapp.post_json(path,
                                     {
                                         "target": target_url
                                     },
                                     **kwargs)
        return res

    def _get_admin_href(self):
        service_res = self.fetch_service_doc()
        workspaces = service_res.json_body['Items']
        courses_workspace = next(
            x for x in workspaces if x['Title'] == 'Courses'
        )
        admin_href = self.require_link_href_with_rel(courses_workspace,
                                                     "AdminLevels")
        return admin_href

    def _create_admin_level(self, key, **kwargs):
        admin_href = self._get_admin_href()
        admin_res = self.testapp.post_json(admin_href, {'key': key},
                                           **kwargs).json_body
        return admin_res

    def _create_course(self, admin_href, **kwargs):
        """
        Create course and return ext
        """
        new_course = self.testapp.post_json(admin_href,
                                            {'ProviderUniqueID': 'ZapierTestCourse',
                                             'title': 'ZapierTestCourse',
                                             'RichDescription': 'ZapierTestCourse',
                                             'Preview': False},
                                            **kwargs)

        new_course = new_course.json_body
        entry_url = self.require_link_href_with_rel(new_course, 'CourseCatalogEntry')
        self.testapp.put_json(entry_url, {'Preview': False})
        return new_course

    def _test_course_created(self, admin_level_href, subscription_env, course_env):
        target_url = "https://localhost/course_created"
        res = self._create_subscription("course", "created", target_url,
                                        extra_environ=subscription_env)
        subscription_ntiid = res.json_body['Id']
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(0))

        self._create_course(admin_level_href, extra_environ=course_env)

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(1))
            assert_that(json.loads(subscription.values()[0].payload_data),
                        has_entries({
                            'MimeType': CourseCreatedEvent.mimeType,
                            'Data': has_entries({
                                'MimeType': CourseDetails.mimeType
                            })
                        }))

    @WithSharedApplicationMockDS(users=('site.admin',
                                        'nti.admin'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_course_created(self):
        nti_admin_env = self._make_extra_environ(user='nti.admin')

        site_admin_env = self._make_extra_environ(user='site.admin')
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
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

        # Create an admin level to store our course in
        admin_res = self._create_admin_level('ZapierTestKey',
                                             extra_environ=nti_admin_env)
        new_admin_href = admin_res['href']
        try:
            # Test w/ both envs and mixed, since this can affect subscription
            # security checks and, hence, the subscription is "applicable"
            self._test_course_created(new_admin_href, site_admin_env, site_admin_env)
            self._test_course_created(new_admin_href, nti_admin_env, nti_admin_env)
            self._test_course_created(new_admin_href, site_admin_env, nti_admin_env)
            self._test_course_created(new_admin_href, nti_admin_env, site_admin_env)
        finally:
            # Remove the admin level to avoid issues with rerunning test
            with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
                library = component.getUtility(IContentPackageLibrary)
                enumeration = IDelimitedHierarchyContentPackageEnumeration(library)
                # pylint: disable=no-member
                path = enumeration.root.absolute_path + "/Courses/ZapierTestKey"
                shutil.rmtree(path, True)
