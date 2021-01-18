#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import not_none

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.ntiids.ntiids import find_object_with_ntiid


class TestResolveMe(ApplicationLayerTest):

    default_origin = 'https://alpha.nextthought.com'

    @WithSharedApplicationMockDS(testapp=True)
    def test_success(self):
        with mock_ds.mock_db_trans():
            boo_user = self._create_user(u"booradley",
                                         external_value={
                                             u"email": u"boo@maycomb.com",
                                             u"realname": u"Arthur Radley"
                                         })
            user_env = self._make_extra_environ(boo_user.username)

        res = self.testapp.get(b'/dataserver2/zapier/resolve_me',
                               extra_environ=user_env)

        assert_that(res.json_body, has_entries({
            u"Username": u"booradley",
            u"Email": u"boo@maycomb.com",
            u"Realname": u"Arthur Radley",
            u"LastSeen": not_none(),
            u"LastLogin": not_none(),
        }))

    @WithSharedApplicationMockDS(testapp=True)
    def test_failure(self):
        self.testapp.get(b'/dataserver2/zapier/resolve_me',
                         status=401)


class TestSubscriptions(ApplicationLayerTest):

    default_origin = 'https://alpha.nextthought.com'

    def _create_subscription(self, obj_type, event_type, target_url, **kwargs):
        path = b'/dataserver2/zapier/subscriptions/%s/%s' % (obj_type, event_type)
        res = self.testapp.post_json(path,
                                     {
                                         "target": target_url
                                     },
                                     **kwargs)
        return res

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_create(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url)

        assert_that(res.json_body, has_entries({
            "Target": target_url,
            "Id": not_none(),
            "OwnerId": self.extra_environ_default_user.lower(),
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_admin_created_subscriptions_fire(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url)

        subscription_ntiid = res.json_body['Id']
        with mock_ds.mock_db_trans(site_name="alpha.nextthought.com"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(0))

        with mock_ds.mock_db_trans(site_name="alpha.nextthought.com"):
            import uuid
            self._create_user(uuid.uuid4().hex,
                              external_value={
                                  u'realname': u'Admin Created Test',
                              })

        with mock_ds.mock_db_trans(site_name="alpha.nextthought.com"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(1))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_list(self):
        target_url = "https://localhost/handle_new_user"
        self._create_subscription("user", "created", target_url)

        res = self.testapp.get(b'/dataserver2/zapier/subscriptions')
        body = res.json_body
        assert_that(body, has_entries({
            "Items": has_length(1)
        }))

        assert_that(body["Items"][0], has_entries({
            "Target": target_url,
            "Id": not_none(),
            "OwnerId": self.extra_environ_default_user.lower(),
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))

