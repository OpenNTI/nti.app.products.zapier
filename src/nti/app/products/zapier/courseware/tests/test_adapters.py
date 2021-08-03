#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import time
from datetime import timedelta

import fudge

from hamcrest import assert_that
from hamcrest import has_properties
from hamcrest import is_
from hamcrest import not_none
from hamcrest import same_instance

from persistent import Persistent

from redis.client import timestamp_to_datetime

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.lifecycleevent import ObjectAddedEvent

from nti.app.products.zapier.courseware.interfaces import IZapierUserProgressUpdatedEvent

from nti.app.products.zapier.courseware.model import ZapierUserProgressUpdatedEvent

from nti.app.products.zapier.interfaces import EVENT_COURSE_CREATED
from nti.app.products.zapier.interfaces import EVENT_USER_ENROLLED

from nti.app.products.zapier.tests import ZapierTestCase

from nti.contenttypes.completion.interfaces import UserProgressUpdatedEvent
from nti.contenttypes.completion.interfaces import IProgress

from nti.contenttypes.completion.progress import Progress

from nti.contenttypes.courses import courses

from nti.contenttypes.courses.catalog import CourseCatalogEntry

from nti.contenttypes.courses.interfaces import ES_CREDIT_DEGREE
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.coremetadata.interfaces import IUser

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


def check_course_details(ext_details, catalog_entry):
    assert_that(ext_details, has_properties(
        Id=catalog_entry.ntiid,
        ProviderId=catalog_entry.ProviderUniqueID,
        StartDate=catalog_entry.StartDate,
        EndDate=catalog_entry.EndDate,
        Title=catalog_entry.title,
        Description=catalog_entry.description,
        RichDescription=catalog_entry.RichDescription,
        createdTime=catalog_entry.createdTime,
        lastModified=catalog_entry.lastModified
    ))


def _catalog_entry():
    catalog_entry = CourseCatalogEntry()
    catalog_entry.ntiid = u"tag:nextthought.com,2011-10:DET-1001"
    catalog_entry.title = u"Who Are You"
    catalog_entry.description = u"Who You Think You Are"
    catalog_entry.RichDescription = u"<p>Who You Think You Are</p>"
    catalog_entry.ProviderUniqueID = u"DET-1001"

    time_now = time.time()
    dt_now = timestamp_to_datetime(time_now)
    catalog_entry.StartDate = dt_now + timedelta(2)
    catalog_entry.EndDate = dt_now + timedelta(3)
    catalog_entry.createdTime = time_now + timedelta(1).total_seconds()
    catalog_entry.lastModified = time_now + timedelta(2).total_seconds()

    return catalog_entry


class TestProgressUpdatedAdapters(ZapierTestCase):

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

            catalog_entry = _catalog_entry()
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

            check_course_details(payload.Data.Course, catalog_entry)

            assert_that(payload.Data.Progress, has_properties(
                AbsoluteProgress=1,
                MaxPossibleProgress=2,
                PercentageProgress=0.5,
            ))

    @WithMockDS
    @fudge.patch('nti.app.products.zapier.courseware.adapters.get_enrollment_record')
    def test_user_progress_conversion(self, get_enrollment_record):
        enrollment_record = fudge.Fake('EnrollmentRecord')
        get_enrollment_record.is_callable().returns(enrollment_record)

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

            progress = fudge.Fake('Progress').has_attr(AbsoluteProgress=1,
                                                       MaxPossibleProgress=2,
                                                       PercentageProgress=0.5)
            adapter = fudge.Fake('ProgressAdapter').is_callable().returns(progress)
            with _provide_adapter(adapter, required=(IUser, ICourseInstance), provided=IProgress):
                zapier_event = IZapierUserProgressUpdatedEvent(event)

            assert_that(zapier_event.EnrollmentRecord, same_instance(enrollment_record))
            assert_that(zapier_event.User.username, is_(user.username))

            assert_that(zapier_event.Progress, has_properties(
                AbsoluteProgress=1,
                MaxPossibleProgress=2,
                PercentageProgress=0.5,
            ))


class TestCourseCreatedAdapters(ZapierTestCase):

    @WithMockDS
    def test_course_created_event(self):
        with mock_ds.mock_db_trans():
            catalog_entry = _catalog_entry()
            course = CourseInstance(catalog_entry)

            payload = component.getAdapter(course,
                                           IWebhookPayload,
                                           name="zapier-webhook-delivery")

            assert_that(payload.Data, not_none())
            assert_that(payload.EventType, EVENT_COURSE_CREATED)
            check_course_details(payload.Data, catalog_entry)


@interface.implementer(ICourseInstanceEnrollmentRecord)
class TestEnrollmentRecord(Contained, Persistent):

    def __init__(self, course, user, scope):
        self.CourseInstance = course
        self.Principal = user
        self.Scope = scope


class TestUserEnrolledAdapters(ZapierTestCase):

    @WithMockDS
    def test_user_enrolled_event(self):
        with mock_ds.mock_db_trans() as conn:
            user = User.create_user(username=u"jbender",
                                    external_value={
                                        'email': u"jbender@shermerhs.edu",
                                        'realname': u"John Bender"
                                    })

            catalog_entry = _catalog_entry()
            course = CourseInstance(catalog_entry)
            record = TestEnrollmentRecord(course, user, ES_CREDIT_DEGREE)
            conn.add(record)
            event = ObjectAddedEvent(record)

            payload = \
                component.getMultiAdapter((event.object, event),
                                          IWebhookPayload,
                                          name="zapier-webhook-delivery")

            assert_that(payload.EventType, EVENT_USER_ENROLLED)
            assert_that(payload.Data, not_none())
            assert_that(payload.Data.Id, not_none())
            assert_that(payload.Data.Scope, ES_CREDIT_DEGREE)

            check_course_details(payload.Data.Course, catalog_entry)

            assert_that(payload.Data.User, has_properties(
                Username=user.username,
                Email="jbender@shermerhs.edu",
                Realname=u"John Bender",
                createdTime=user.createdTime,
                LastLogin=datetime_from_timestamp(user.lastLoginTime),
                LastSeen=datetime_from_timestamp(user.lastSeenTime)
            ))


@contextlib.contextmanager
def _provide_adapter(adapter, **kwargs):
    gsm = component.getGlobalSiteManager()
    gsm.registerAdapter(adapter, **kwargs)
    try:
        yield
    finally:
        gsm.unregisterAdapter(adapter, **kwargs)
