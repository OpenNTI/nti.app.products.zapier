#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import uuid

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_

from zope import component

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.products.zapier import USER_SEARCH

from nti.app.products.zapier.model import CourseDetails
from nti.app.products.zapier.model import UserDetails

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users import DynamicFriendsList
from nti.dataserver.users import FriendsList

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.externalization.standard_fields import datetime_to_string
from nti.externalization.externalization.standard_fields import timestamp_to_string

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal import traversal


class TestSearchUsers(ApplicationLayerTest, ZapierTestMixin):

    default_origin = 'https://alpha.nextthought.com'

    def _call_FUT(self, subpath, params=None, expected_length=None, **kwargs):
        workspace_kwargs = {key: value for key, value in kwargs.items()
                            if key == 'extra_environ'}
        base_search_path = self.get_workspace_link(USER_SEARCH,
                                                   **workspace_kwargs)
        path = b'%s/%s' % (base_search_path, subpath)

        res = self.testapp.get(path, params, **kwargs)

        if expected_length:
            assert_that(res.json_body['Items'], has_length(expected_length))

        return res

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_externalization(self):
        with mock_ds.mock_db_trans():
            username = u"testuser-%s" % (uuid.uuid4(),)
            email = u'%s@nextthought.com' % (username,)
            realname = u"%s Test" % (username,)
            self._create_user(username,
                              external_value=dict(
                                  email=email,
                                  realname=realname)
                              )

        res = self._call_FUT(username, status=200)

        json_body = res.json_body
        assert_that(json_body['Items'], has_length(1))
        assert_that(json_body['Items'][0],
                    has_entries({
                        "MimeType": UserDetails.mime_type,
                        "Username": username,
                        "Realname": realname,
                    }))

    @WithSharedApplicationMockDS(users=('user2',),
                                 testapp=True,
                                 default_authenticate=True)
    def test_users_only(self):
        with mock_ds.mock_db_trans():
            user1 = self.users['sjohnson@nextthought.com']
            user2 = self.users['user2']

            dfl = DynamicFriendsList(username=u'DynamicFriends')
            IFriendlyNamed(dfl).alias = u"Close Associates"
            dfl.creator = user1
            user1.addContainedObject(dfl)
            dfl.addFriend(user2)

            fl = FriendsList(username=u'StaticFriends')
            IFriendlyNamed(fl).alias = u"Super Friends"
            fl.creator = user1
            user1.addContainedObject(fl)
            fl.addFriend(user2)

        self._call_FUT('dynamic', status=200, expected_length=0)
        self._call_FUT('close', status=200, expected_length=0)
        self._call_FUT('static', status=200, expected_length=0)
        self._call_FUT('super', status=200, expected_length=0)

    @WithSharedApplicationMockDS(users=('user2',),
                                 testapp=True)
    def test_permissions(self):
        # Just need to test the view permissions, specifically that
        # auth/vs unauth'd users.  Base view should take care of
        # the rest
        with mock_ds.mock_db_trans(self.ds, site_name="alpha.nextthought.com"):
            site_auth = component.getUtility(ISiteAuthentication)
            site_auth_path = traversal.resource_path(site_auth)

        self.testapp.get(site_auth_path + '/' +  USER_SEARCH, status=401)

        user_env = self._make_extra_environ('user2')
        self._call_FUT('',
                       status=200,
                       extra_environ=user_env)


class TestSearchCourses(ApplicationLayerTest, ZapierTestMixin):

    layer = InstructedCourseApplicationTestLayer

    default_origin = 'http://platform.ou.edu'

    def _call_FUT(self, filter, params=None, expected_length=None, **kwargs):
        workspace_kwargs = {key: value for key, value in kwargs.items()
                            if key == 'extra_environ'}
        base_search_path = self.get_workspace_link('course_search',
                                                   **workspace_kwargs)
        from six.moves import urllib_parse
        quoted_filter = urllib_parse.quote_plus(filter)
        path = b'%s?filter=%s' % (base_search_path,
                                  quoted_filter)

        res = self.testapp.get(path, params, **kwargs)

        if expected_length:
            assert_that(res.json_body['Items'], has_length(expected_length))

        return res

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_externalization(self):
        res = self._call_FUT('CS 1323-995', status=200)
        json_body = res.json_body

        assert_that(json_body['Items'], has_length(1))
        course_ntiid = json_body['Items'][0]['Id']
        with mock_ds.mock_db_trans(site_name='platform.ou.edu'):
            course = find_object_with_ntiid(course_ntiid)
            assert_that(course, not_(none()))

            assert_that(json_body['Items'][0],
                        has_entries({
                            "MimeType": CourseDetails.mime_type,
                            "Id": not_(none()),
                            "Title": "Introduction to Computer Programming",
                            "ProviderId": 'CS 1323-995',
                            "StartDate": datetime_to_string(course.StartDate),
                            "EndDate": datetime_to_string(course.EndDate),
                            "Description": course.description,
                            "CreatedTime": timestamp_to_string(course.createdTime),
                            "Last Modified": timestamp_to_string(course.lastModified),
                        }))
