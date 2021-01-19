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

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestCreateUser(ApplicationLayerTest, ZapierTestMixin):

    default_origin = 'https://alpha.nextthought.com'

    def _call_FUT(self, data, **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        create_users_href = self.get_workspace_link('create_user',
                                                    **workspace_kwargs)
        success = urllib_parse.quote_plus('https://alpha.nextthought.com/reset')
        path = b'%s?success=%s' % (create_users_href, success,)

        res = self.testapp.post_json(path,
                                     data,
                                     **kwargs)

        return res

    def _test_success(self, **kwargs):
        data = {'Username': 'booradley',
                'Realname': 'Arthur Radley',
                'Email': 'boo@maycomb.com'}

        res = self._call_FUT(data, **kwargs)

        assert_that(res.json_body, has_entries({
            "Username": "booradley",
            "Email": "boo@maycomb.com",
            "Realname": "Arthur Radley",
            "LastSeen": not_none(),
            "LastLogin": not_none(),
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

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_no_username(self):
        data = {'Realname': 'Arthur Radley',
                'Email': 'boo@maycomb.com'}

        res = self._call_FUT(data, status=422)

        body = res.json_body
        assert_that(body, has_entries({
            "code": "RequiredMissing",
            'field': 'Username',
            "message": "Username",
        }))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_no_realname(self):
        data = {'Username': 'booradley',
                'Email': 'boo@maycomb.com'}

        res = self._call_FUT(data, status=422)

        body = res.json_body
        assert_that(body, has_entries({
            "code": "RequiredMissing",
            "field": "Realname",
            "message": "Missing data",
        }))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_no_email(self):
        data = {'Username': 'booradley',
                'Realname': 'Arthur Radley'}

        res = self._call_FUT(data, status=422)

        body = res.json_body
        assert_that(body, has_entries({
            "code": "RequiredMissing",
            'field': 'Email',
            "message": "Missing data",
        }))

    @WithSharedApplicationMockDS(users=("joe.schmoe",),
                                 testapp=True)
    def test_no_authentication(self):
        with mock_ds.mock_db_trans(self.ds,
                                   site_name="alpha.nextthought.com"):
            joe = self._get_user('joe.schmoe')
            joe_env = self._make_extra_environ(joe.username)

        path = b'/dataserver2/++etc++hostsites/alpha.nextthought.com/++etc++site/default/authentication/users'

        unauth_env = self._make_extra_environ(username=None)
        self.testapp.post_json(path, status=401,
                               extra_environ=unauth_env)

        self.testapp.post(path, status=403, extra_environ=joe_env)
