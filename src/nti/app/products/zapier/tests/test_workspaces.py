#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that

from zope import component

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.zapier import AUTH_USERS_PATH
from nti.app.products.zapier import RESOLVE_ME
from nti.app.products.zapier import SUBSCRIPTIONS_VIEW
from nti.app.products.zapier import USER_SEARCH
from nti.app.products.zapier import ZAPIER
from nti.app.products.zapier import ZAPIER_PATH

from nti.app.products.zapier.interfaces import IZapierWorkspace

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.workspaces.interfaces import IUserService

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.externalization import to_external_object

from nti.testing.matchers import verifiably_provides

from nti.traversal import traversal


class TestWorkspaces(ApplicationLayerTest):

    default_origin = 'http://alpha.nextthought.com'

    def require_link(self, ws_ext, rel, method, href):
        self.require_link_href_with_rel(ws_ext, rel)
        create_user_link = self.link_with_rel(ws_ext, rel)
        assert_that(create_user_link['method'], is_(method))
        assert_that(create_user_link['href'], is_(href))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True)
    def test_workspace(self):
        with mock_ds.mock_db_trans(self.ds, site_name="alpha.nextthought.com"):
            user = self._create_user(username='e.sobeck',
                                     external_value={
                                         'realname': u'Liz Sobeck',
                                     })
            username = user.username
            service = IUserService(user)

            workspaces = service.workspaces
            assert_that(workspaces,
                        has_item(verifiably_provides(IZapierWorkspace)))

            workspaces = [
                x for x in workspaces if IZapierWorkspace.providedBy(x)
            ]
            workspace = workspaces[0]

            ws_traversal_path = traversal.resource_path(workspace)
            assert_that(ws_traversal_path,
                        is_('/dataserver2/users/e.sobeck/' + ZAPIER))
            assert_that(workspace.name, is_(ZAPIER))

            # Collections
            assert_that(workspace.collections, has_length(0))

        user_env = self._make_extra_environ(username=username)
        self.testapp.get(ws_traversal_path,
                         extra_environ=user_env,
                         status=200)

    def _test_links(self,
                    site_auth_path,
                    include_admin_links=False,
                    **kwargs):
        res = self.testapp.get('/dataserver2/service', **kwargs)
        res = res.json_body
        workspaces = [
            x for x in res['Items'] if x.get('Title') == ZAPIER
        ]
        assert_that(workspaces, has_length(1))
        ws_ext = workspaces[0]

        # Links
        with mock_ds.mock_db_trans():
            ds_path = traversal.resource_path(self.ds.dataserver_folder)

        self.require_link(ws_ext,
                          'resolve_me',
                          'GET',
                          '/'.join((ds_path, ZAPIER_PATH, RESOLVE_ME)))

        if site_auth_path:
            self.require_link(ws_ext,
                              USER_SEARCH,
                              'GET',
                              site_auth_path + '/' + USER_SEARCH)

            if include_admin_links:
                self.require_link(ws_ext,
                                  'create_user',
                                  'POST',
                                  site_auth_path + '/' + AUTH_USERS_PATH)
            else:
                self.forbid_link_with_rel(ws_ext, 'create_user')
        else:
            self.forbid_link_with_rel(ws_ext, USER_SEARCH)
            self.forbid_link_with_rel(ws_ext, 'create_user')

        if include_admin_links:
            self.require_link(ws_ext,
                              SUBSCRIPTIONS_VIEW,
                              'GET',
                              '/'.join((ds_path, ZAPIER_PATH, SUBSCRIPTIONS_VIEW)))
            self.require_link(ws_ext,
                              'create_subscription',
                              'POST',
                              '/'.join((ds_path, ZAPIER_PATH, SUBSCRIPTIONS_VIEW)))
        else:
            self.forbid_link_with_rel(ws_ext, SUBSCRIPTIONS_VIEW)
            self.forbid_link_with_rel(ws_ext, 'create_subscription')

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True)
    def test_links_admin_no_site_auth(self):
        extra_env = self._make_extra_environ(HTTP_ORIGIN="http://localhost")
        self._test_links(None,
                         include_admin_links=True,
                         extra_environ=extra_env)

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True)
    def test_links_admin(self):
        with mock_ds.mock_db_trans(self.ds, site_name="alpha.nextthought.com"):
            site_auth = component.getUtility(ISiteAuthentication)
            site_auth_path = traversal.resource_path(site_auth)

        self._test_links(site_auth_path, include_admin_links=True)

    @WithSharedApplicationMockDS(testapp=True)
    def test_links_site_admin(self):
        with mock_ds.mock_db_trans(self.ds, site_name="alpha.nextthought.com"):
            user = self._create_user(username='e.sobeck',
                                     external_value={
                                         'realname': u'Liz Sobeck',
                                     })
            username = user.username

            site = getSite()
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN.id, user.username)

            site_auth = component.getUtility(ISiteAuthentication)
            site_auth_path = traversal.resource_path(site_auth)

        extra_environ = self._make_extra_environ(username)
        self._test_links(site_auth_path,
                         include_admin_links=True,
                         extra_environ=extra_environ)

    @WithSharedApplicationMockDS(testapp=True)
    def test_links_non_admin(self):
        with mock_ds.mock_db_trans(self.ds, site_name="alpha.nextthought.com"):
            user = self._create_user(username='e.sobeck',
                                     external_value={
                                         'realname': u'Liz Sobeck',
                                     })
            username = user.username

            site_auth = component.getUtility(ISiteAuthentication)
            site_auth_path = traversal.resource_path(site_auth)

        extra_environ = self._make_extra_environ(username)
        self._test_links(site_auth_path,
                         include_admin_links=False,
                         extra_environ=extra_environ)
