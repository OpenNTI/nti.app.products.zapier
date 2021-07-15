#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_

from nti.app.products.courseware.tests import InstructedCourseApplicationTestLayer

from nti.app.products.zapier.courseware.model import CourseDetails

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.externalization.externalization.standard_fields import datetime_to_string
from nti.externalization.externalization.standard_fields import timestamp_to_string

from nti.ntiids.ntiids import find_object_with_ntiid


class TestSearchCourses(ApplicationLayerTest, ZapierTestMixin):

    layer = InstructedCourseApplicationTestLayer

    default_origin = 'http://platform.ou.edu'

    def _call_FUT(self, params=None, expected_length=None, **kwargs):
        workspace_kwargs = {key: value for key, value in kwargs.items()
                            if key == 'extra_environ'}
        path = self.get_workspace_link('course_search',
                                       **workspace_kwargs)

        res = self.testapp.get(path, params, **kwargs)

        if expected_length is not None:
            assert_that(res.json_body['Items'], has_length(expected_length))

        return res

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_externalization(self):
        res = self._call_FUT(params={"filter": 'CS 1323-995'}, status=200)
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

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_links(self):
        res = self._call_FUT(params={"filter": 'CS 1323',
                                     "batchStart": 1,
                                     "batchSize": 1
                                     },
                             status=200,
                             expected_length=1)
        json_body = res.json_body

        assert_that(json_body['Items'], has_length(1))

        # Ensure we get our paging links, but not others that would
        # have been decorated for similar course collections used by this
        # view (e.g. "ByTag")
        links = json_body.get("Links") or ()
        assert_that(links, has_length(2))
        self.require_link_href_with_rel(json_body, "batch-next")
        self.require_link_href_with_rel(json_body, "batch-prev")
