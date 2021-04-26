#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
from datetime import timedelta

import fudge

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_properties
from hamcrest import none
from hamcrest import not_none
from nti.externalization.externalization.standard_fields import datetime_to_string
from nti.externalization.externalization.standard_fields import timestamp_to_string

from redis.client import timestamp_to_datetime

from six import text_type

from zope import interface

from nti.app.products.zapier.interfaces import IExternalUserProgressUpdatedEvent

from nti.app.products.zapier.model import CourseDetails
from nti.app.products.zapier.model import ExternalUserProgressUpdatedEvent
from nti.app.products.zapier.model import ProgressDetails
from nti.app.products.zapier.model import ProgressSummary
from nti.app.products.zapier.model import UserDetails
from nti.app.products.zapier.tests import ZapierTestCase

from nti.coremetadata.interfaces import IUser

from nti.externalization.externalization import toExternalObject

from nti.testing.matchers import verifiably_provides


class TestModel(ZapierTestCase):

    def _user_details(self, username):
        dt_now = timestamp_to_datetime(time.time())
        details = UserDetails(Username=username,
                              Email=u"%s@nti.com" % (username.lower(),),
                              Realname=u"%s Test" % (username.title(),),
                              LastLogin=dt_now,
                              LastSeen=dt_now)
        details.user = fudge.Fake('User')
        interface.alsoProvides(details.user, IUser)
        return details

    def _course_details(self, provider_id):
        dt_now = timestamp_to_datetime(time.time())
        return CourseDetails(
            Title=u"Test Course %s" % (provider_id,),
            Description=u"Fun with tests",
            Id=u"tag:nextthought.com,2011-10:%s" % (provider_id,),
            ProviderId=text_type(provider_id),
            StartDate=dt_now,
            EndDate=dt_now + timedelta(1),
            createdTime=0,
            lastModified=1
        )

    def _progress_updated_event(self, username, course_provider_id):
        user_details = self._user_details(username)
        course_details = self._course_details(course_provider_id)
        progress_details = ProgressDetails(AbsoluteProgress=1,
                                           MaxPossibleProgress=2)

        details = ProgressSummary(User=user_details,
                                  Course=course_details,
                                  Progress=progress_details)

        event = ExternalUserProgressUpdatedEvent(Data=details)

        return event

    def test_progress_updated_event(self):
        io = self._progress_updated_event("Venellope", "RACING-101")
        assert_that(io, verifiably_provides(IExternalUserProgressUpdatedEvent))

        ext_obj = toExternalObject(io, policy_name="webhook-delivery")
        assert_that(ext_obj, has_entries({
            "MimeType": ExternalUserProgressUpdatedEvent.mime_type,
            "Data": not_none(),
        }))

        assert_that(ext_obj['Data'], has_entries({
            "MimeType": ProgressSummary.mime_type,
            "User": not_none(),
            "Course": not_none(),
            "Progress": not_none(),
        }))

        assert_that(ext_obj['Data']['User'], has_entries({
            "MimeType": UserDetails.mime_type,
            "Username": "Venellope",
            "Realname": "Venellope Test",
            "Email": "venellope@nti.com",
            "LastLogin": datetime_to_string(io.Data.User.LastLogin),
            "LastSeen": datetime_to_string(io.Data.User.LastSeen),
        }))

        assert_that(ext_obj['Data']['Course'], has_entries({
            "MimeType": CourseDetails.mime_type,
            "Id": io.Data.Course.Id,
            "ProviderId": io.Data.Course.ProviderId,
            "StartDate": datetime_to_string(io.Data.Course.StartDate),
            "EndDate": datetime_to_string(io.Data.Course.EndDate),
            "Title": io.Data.Course.Title,
            "Description": io.Data.Course.Description,
            "CreatedTime": timestamp_to_string(io.Data.Course.createdTime),
            "Last Modified": timestamp_to_string(io.Data.Course.lastModified),
        }))

        assert_that(ext_obj['Data']['Progress'], has_entries({
            "MimeType": ProgressDetails.mime_type,
            "AbsoluteProgress": 1,
            "MaxPossibleProgress": 2,
            "PercentageProgress": 0.5,
        }))

    def test_progress_details_repr(self):
        details = ProgressDetails(1, 2)
        details = eval(repr(details))
        assert_that(details, has_properties(
            AbsoluteProgress=1,
            MaxPossibleProgress=2,
            PercentageProgress=0.5,
        ))

    def test_progress_details_default_percentage(self):
        details = ProgressDetails()
        assert_that(details.PercentageProgress, none())
