#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
from datetime import timedelta

import fudge

from hamcrest import assert_that
from hamcrest import has_properties
from hamcrest import not_none
from hamcrest import same_instance

from redis.client import timestamp_to_datetime

from zope import component
from zope import interface

from nti.app.products.zapier.interfaces import IZapierUserProgressUpdatedEvent

from nti.app.products.zapier.model import ZapierUserProgressUpdatedEvent

from nti.app.products.zapier.tests import ZapierTestCase

from nti.contenttypes.completion.interfaces import UserProgressUpdatedEvent

from nti.contenttypes.completion.progress import Progress

from nti.contenttypes.courses import courses

from nti.contenttypes.courses.catalog import CourseCatalogEntry

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.tests.mock_dataserver import WithMockDS

from nti.dataserver.users import User

from nti.externalization.datetime import datetime_from_timestamp

from nti.webhooks.interfaces import IWebhookPayload


class CourseInstance(courses.CourseInstance):

    def __init__(self, catalog_entry):
        self.catalog_entry = catalog_entry

    def __conform__(self, iface):
        if ICourseCatalogEntry.isOrExtends(iface):
            return self.catalog_entry


class TestAdapters(ZapierTestCase):

    def _zapier_user_progress_event(self, course, user):
        progress = Progress(AbsoluteProgress=1,
                            MaxPossibleProgress=2)
        record = fudge.Fake('CourseInstanceEnrollmentRecord')
        record.has_attr(CourseInstance=course)
        interface.alsoProvides(record, ICourseInstanceEnrollmentRecord)
        zevent = ZapierUserProgressUpdatedEvent(record, user, progress)

        return zevent

    @WithMockDS
    def test_progress_updated_payload(self):
        with mock_ds.mock_db_trans():
            user = User.create_user(username=u"jbender",
                                    external_value={
                                        'email': u"jbender@shermerhs.edu",
                                        'realname': u"John Bender"
                                    })

            catalog_entry = CourseCatalogEntry()
            catalog_entry.ntiid = u"tag:nextthought.com,2011-10:DET-1001"
            catalog_entry.title = u"Who Are You"
            catalog_entry.description = u"Who You Think You Are"
            catalog_entry.ProviderUniqueID = u"DET-1001"

            time_now = time.time()
            dt_now = timestamp_to_datetime(time_now)
            catalog_entry.StartDate = dt_now + timedelta(2)
            catalog_entry.EndDate = dt_now + timedelta(3)
            catalog_entry.createdTime = time_now + timedelta(1).total_seconds()
            catalog_entry.lastModified = time_now + timedelta(2).total_seconds()

            course = CourseInstance(catalog_entry)
            zevent = self._zapier_user_progress_event(course, user)

            payload = \
                component.getMultiAdapter((zevent.EnrollmentRecord, zevent),
                                          IWebhookPayload,
                                          name="zapier-webhook-delivery")

            assert_that(payload.Data, not_none())
            assert_that(payload.Data.User, has_properties(
                Username=user.username,
                Email="jbender@shermerhs.edu",
                Realname=u"John Bender",
                createdTime=user.createdTime,
                LastLogin=datetime_from_timestamp(user.lastLoginTime),
                LastSeen=datetime_from_timestamp(user.lastSeenTime)
            ))

            assert_that(payload.Data.Course, has_properties(
                Id=catalog_entry.ntiid,
                ProviderId=catalog_entry.ProviderUniqueID,
                StartDate=catalog_entry.StartDate,
                EndDate=catalog_entry.EndDate,
                Title=catalog_entry.title,
                Description=catalog_entry.description,
                createdTime=catalog_entry.createdTime,
                lastModified=catalog_entry.lastModified
            ))

            assert_that(payload.Data.Progress, has_properties(
                AbsoluteProgress=1,
                MaxPossibleProgress=2,
                PercentageProgress=0.5,
            ))

    @WithMockDS
    @fudge.patch('nti.app.products.zapier.adapters.get_enrollment_record',
                 'nti.app.products.zapier.adapters._user_progress')
    def test_user_progress_conversion(self,
                                      get_enrollment_record,
                                      get_user_progress):
        enrollment_record = fudge.Fake('EnrollmentRecord')
        get_enrollment_record.is_callable().returns(enrollment_record)
        progress = fudge.Fake('Progress').has_attr(AbsoluteProgress=1,
                                                   MaxPossibleProgress=2)
        get_user_progress.is_callable().returns(progress)

        with mock_ds.mock_db_trans():
            user = User.create_user(username=u"jbender",
                                    external_value={
                                        'email': u"jbender@shermerhs.edu",
                                        'realname': u"John Bender"
                                    })

            course = CourseInstance('entry_id')
            event = UserProgressUpdatedEvent(obj=course,
                                             user=user,
                                             context=course)
            zapier_event = IZapierUserProgressUpdatedEvent(event)
            assert_that(zapier_event.EnrollmentRecord, same_instance(enrollment_record))
            assert_that(zapier_event.User, same_instance(user))
            assert_that(zapier_event.Progress, same_instance(progress))