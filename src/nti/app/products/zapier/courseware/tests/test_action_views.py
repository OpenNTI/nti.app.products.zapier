#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_property

from zope import component

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.testing import ITestMailDelivery

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.contenttypes.courses.interfaces import ES_PUBLIC

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site

from nti.mailer.interfaces import IEmailAddressable


class TestUserEnrollAction(ApplicationLayerTest, ZapierTestMixin):

    layer = PersistentInstructedCourseApplicationTestLayer

    default_origin = b'http://janux.ou.edu'

    course_ntiid = 'tag:nextthought.com,2011-10:NTI-CourseInfo-Fall2013_CLC3403_LawAndJustice'

    def _enroll_user(self, data, **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        enrollments_url = self.get_workspace_link('enroll_user',
                                                  **workspace_kwargs)

        res = self.testapp.post_json(enrollments_url,
                                     data,
                                     **kwargs)
        return res

    @WithSharedApplicationMockDS(users=('student_user',
                                        'nti.admin',
                                        'site.admin'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_user_enrollment(self):
        instructor_environ = self._make_extra_environ(username='harp4162')
        site_admin_env = self._make_extra_environ(username='site.admin')
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            site = getSite()
            site_name = site.__name__

            # User to be enrolled
            student_user = self._get_user('student_user')
            student_username = student_user.username
            set_user_creation_site(student_user, site_name)

            # A site admin who can administer user to be enrolled
            site_admin = self._get_user('site.admin')
            set_user_creation_site(site_admin, site_name)
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, site_admin.username)

            # An nti admin (nti.admin) w/ no principal permissions
            nti_admin = self._get_user('nti.admin')
            self._assign_role(ROLE_ADMIN, username=nti_admin.username)

        # No Username
        res = self._enroll_user({}, status=422).json_body
        assert_that(res, has_entries(
            field='Username',
            message='Missing data',
            code='RequiredMissing',
        ))

        # No matching user
        data = {'Username': 'unmatched_user'}
        res = self._enroll_user(data, status=422).json_body
        assert_that(res, has_entries(
            field='Username',
            message='User not found.',
            code='UserNotFound',
        ))

        # Only admins and site admins can access
        enrollments_url = '/dataserver2/zapier/enrollments'
        data = {'Username': student_username}
        res = self.testapp.post_json(enrollments_url, data, status=403,
                                     extra_environ=instructor_environ).json_body
        assert_that(res, has_entries(
            message='Cannot modify user enrollments.',
            code='CannotAccessUserEnrollmentsError',
        ))

        # No CourseId
        data = {'Username': student_username}
        res = self._enroll_user(data, status=422,
                                extra_environ=site_admin_env).json_body
        assert_that(res, has_entries(
            field='CourseId',
            message='Missing data',
            code='RequiredMissing',
        ))

        # No matching course
        data = {'Username': student_username,
                'CourseId': "invalid_course_id"}
        res = self._enroll_user(data, status=422,
                                extra_environ=site_admin_env).json_body
        assert_that(res, has_entries(
            field='CourseId',
            message='Course not found.',
            code='CourseNotFound',
        ))

        # Invalid Scope
        data = {'Username': student_username,
                'CourseId': self.course_ntiid,
                'Scope': 'invalid_scope'}
        res = self._enroll_user(data, status=422,
                                extra_environ=site_admin_env).json_body
        assert_that(res, has_entries(
            field='Scope',
            message='Invalid scope, must be one of: ForCreditNonDegree, ForCredit, Public, Purchased, ForCreditDegree',
            code='InvalidScope',
        ))

        # User is instructor
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            # Make instructor a site admin so they have access
            site = getSite()
            site_name = site.__name__

            instructor = self._get_user('harp4162')
            set_user_creation_site(instructor, site_name)
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, instructor.username)

        data = {'Username': 'harp4162',
                'CourseId': self.course_ntiid,
                'Scope': ES_PUBLIC}
        res = self._enroll_user(data, status=422,
                                extra_environ=site_admin_env).json_body
        assert_that(res, has_entries(
            field='Username',
            message='User is an instructor in course hierarchy.',
            code='UserIsInstructor',
        ))

        mailer = component.getUtility(ITestMailDelivery)
        del mailer.queue[:]

        # Successful, created
        data = {'Username': 'student_user',
                'CourseId': self.course_ntiid,
                'Scope': ES_PUBLIC}
        res = self._enroll_user(data, status=201).json_body
        assert_that(res, has_entries(
            User=has_entries(Username='student_user'),
            Course=has_entries(Id=self.course_ntiid),
            Scope=ES_PUBLIC
        ))
        assert_that(mailer.queue, has_length(0))

        # Successful, already created
        data = {'Username': 'student_user',
                'CourseId': self.course_ntiid,
                'Scope': ES_PUBLIC}
        res = self._enroll_user(data, status=200).json_body
        assert_that(res, has_entries(
            User=has_entries(Username='student_user'),
            Course=has_entries(Id=self.course_ntiid),
            Scope=ES_PUBLIC
        ))
        assert_that(mailer.queue, has_length(0))

        # Successful, created, interaction (will generate enrollment email)
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            # Will need our enrolled user to have an email
            user = self._get_user(self.default_username)
            IEmailAddressable(user).email = u'default@user.com'

        data = {'Username': self.default_username,
                'CourseId': self.course_ntiid,
                'Scope': ES_PUBLIC,
                'interaction': True}
        res = self._enroll_user(data, status=201).json_body
        assert_that(res, has_entries(
            User=has_entries(Username=self.default_username.lower()),
            Course=has_entries(Id=self.course_ntiid),
            Scope=ES_PUBLIC
        ))
        assert_that(mailer.queue, has_length(1))
        assert_that(mailer.queue[0],
                    has_property('subject', 'Welcome to Law and Justice'))
