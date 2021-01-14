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

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.zapier import ZAPIER

from nti.app.products.zapier.interfaces import IZapierWorkspace

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.workspaces.interfaces import IUserService

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.externalization import to_external_object

from nti.testing.matchers import verifiably_provides

from nti.traversal import traversal


class TestWorkspaces(ApplicationLayerTest):

    default_origin = 'http://alpha.nextthought.com'

    @WithSharedApplicationMockDS(testapp=True)
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

            assert_that(traversal.resource_path(workspace),
                        is_('/dataserver2/users/e.sobeck/zapier'))
            assert_that(workspace.name, is_(ZAPIER))

            # Collections
            assert_that(workspace.collections, has_length(0))

            # Links
            site_auth = component.getUtility(ISiteAuthentication)
            site_auth_path = traversal.resource_path(site_auth)

            ws_ext = to_external_object(workspace)
            create_user_link = self.link_with_rel(ws_ext, 'create_user')
            assert_that(create_user_link['method'], is_('POST'))
            assert_that(create_user_link['href'], is_(site_auth_path + '/users'))

        user_env = self._make_extra_environ(username=username)
        self.testapp.get('/dataserver2/users/e.sobeck/zapier',
                         extra_environ=user_env,
                         status=200)

