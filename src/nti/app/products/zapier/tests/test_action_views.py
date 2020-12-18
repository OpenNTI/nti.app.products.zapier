#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import not_none

from six.moves import urllib_parse

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestCreateUser(ApplicationLayerTest):

    default_origin = 'https://alpha.nextthought.com'

    def _test_success(self, **kwargs):
        data = {'Username': 'booradley',
                'realname': 'Arthur Radley',
                'email': 'boo@maycomb.com'}

        success = urllib_parse.quote_plus('https://alpha.nextthought.com/reset')
        path = b'/dataserver2/zapier/users?success=%s' % (success,)

        res = self.testapp.post_json(path,
                                     data,
                                     **kwargs)

        assert_that(res.json_body, has_entries({
            "username": "booradley",
            "email": "boo@maycomb.com",
            "name": "Arthur Radley",
            "lastSeen": not_none(),
            "lastLogin": not_none(),
        }))

    @WithSharedApplicationMockDS(users=("site.admin",),
                                 testapp=True)
    def test_site_admin(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            admin = self._get_user('site.admin')
            admin_env = self._make_extra_environ(admin.username)

            site = getSite()
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, admin.username)

        self._test_success(extra_environ=admin_env)

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_platform_admin(self):
        self._test_success()

    @WithSharedApplicationMockDS(users=("joe.schmoe",),
                                 testapp=True)
    def test_no_authentication(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            joe = self._get_user('joe.schmoe')
            joe_env = self._make_extra_environ(joe.username)

        path = b'/dataserver2/zapier/users'

        unauth_env = self._make_extra_environ(username=None)
        self.testapp.post_json(path, status=401,
                               extra_environ=unauth_env)

        self.testapp.post(path, status=403, extra_environ=joe_env)
