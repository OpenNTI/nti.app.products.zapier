#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from nti.app.products.courseware.interfaces import ICourseInstanceEnrollment

from nti.app.products.zapier.adapters import AbstractWebhookSubscriber

from nti.app.products.zapier.courseware.interfaces import ICourseEnrollmentDetails

from nti.app.products.zapier.courseware.model import CourseCreatedEvent

from nti.app.products.zapier.interfaces import EVENT_COURSE_CREATED
from nti.app.products.zapier.interfaces import EVENT_PROGESS_UPDATED
from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import IWebhookSubscriber

from nti.app.products.zapier.courseware.interfaces import ICompletionContextProgressDetails
from nti.app.products.zapier.courseware.interfaces import ICourseDetails
from nti.app.products.zapier.courseware.interfaces import IProgressDetails
from nti.app.products.zapier.courseware.interfaces import IZapierUserProgressUpdatedEvent

from nti.app.products.zapier.courseware.model import CompletionContextProgressDetails
from nti.app.products.zapier.courseware.model import CourseDetails
from nti.app.products.zapier.courseware.model import CourseEnrollmentDetails
from nti.app.products.zapier.courseware.model import ExternalUserProgressUpdatedEvent
from nti.app.products.zapier.courseware.model import ProgressSummary
from nti.app.products.zapier.courseware.model import UserEnrolledEvent
from nti.app.products.zapier.courseware.model import ZapierUserProgressUpdatedEvent

from nti.app.products.zapier.interfaces import EVENT_USER_ENROLLED

from nti.contenttypes.completion.interfaces import IProgress
from nti.contenttypes.completion.interfaces import IUserProgressUpdatedEvent

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseInstanceAvailableEvent
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.contenttypes.courses.utils import get_enrollment_record

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User

from nti.webhooks.interfaces import IWebhookPayload


# User Progress adapters
from zope.lifecycleevent import IObjectAddedEvent


@interface.implementer(IZapierUserProgressUpdatedEvent)
@component.adapter(IUserProgressUpdatedEvent)
def zapier_user_progress(event):
    course = event.context
    user = event.user
    enrollment = get_enrollment_record(course, user)
    progress = component.queryMultiAdapter((user, course),
                                           IProgress)

    return ZapierUserProgressUpdatedEvent(
        enrollment,
        user,
        progress
    )


@interface.implementer(ICompletionContextProgressDetails)
@component.adapter(IProgress)
def progress_details(progress):
    success = progress.CompletedItem is not None and progress.CompletedItem.Success
    return CompletionContextProgressDetails(
        Completed=progress.Completed,
        Success=success,
        AbsoluteProgress=progress.AbsoluteProgress,
        MaxPossibleProgress=progress.MaxPossibleProgress
    )


@component.adapter(ICourseInstanceEnrollmentRecord, IZapierUserProgressUpdatedEvent)
@interface.implementer(IWebhookPayload)
def course_progress_updated_payload(record, event):
    user_details = IUserDetails(event.User)
    course_details = ICourseDetails(record.CourseInstance)
    progress_details = IProgressDetails(event.Progress)

    data = ProgressSummary(User=user_details,
                           Course=course_details,
                           Progress=progress_details)

    payload = ExternalUserProgressUpdatedEvent(EventType=EVENT_PROGESS_UPDATED,
                                               Data=data)
    return payload


@component.adapter(ICourseInstance)
@interface.implementer(ICourseDetails)
def details_from_course(course):
    catalog_entry = ICourseCatalogEntry(course)
    return ICourseDetails(catalog_entry)


@component.adapter(ICourseCatalogEntry)
@interface.implementer(ICourseDetails)
def details_from_catalog_entry(catalog_entry):
    created_time = getattr(catalog_entry, 'createdTime', None)
    last_modified = getattr(catalog_entry, 'lastModified', None)

    details = CourseDetails(
        Id=catalog_entry.ntiid,
        ProviderId=catalog_entry.ProviderUniqueID,
        StartDate=catalog_entry.StartDate,
        EndDate=catalog_entry.EndDate,
        Title=catalog_entry.title,
        Description=catalog_entry.description,
        RichDescription=catalog_entry.RichDescription,
        createdTime=created_time,
        lastModified=last_modified
    )

    details.catalog_entry = catalog_entry

    return details


@interface.implementer(IWebhookSubscriber)
class CourseProgressUpdatedWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = ICourseInstanceEnrollmentRecord
    when = IZapierUserProgressUpdatedEvent
    permission_id = nauth.ACT_READ.id


# Course Created adapters

@component.adapter(ICourseInstance)
@interface.implementer(IWebhookPayload)
def course_payload(user):
    details = ICourseDetails(user)

    payload = CourseCreatedEvent(EventType=EVENT_COURSE_CREATED,
                                 Data=details)
    return payload


@interface.implementer(IWebhookSubscriber)
class CourseCreatedWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = ICourseInstance
    when = ICourseInstanceAvailableEvent
    permission_id = nauth.ACT_READ.id


# User Enrolled adapters

@interface.implementer(IWebhookSubscriber)
class UserEnrolledWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = ICourseInstanceEnrollmentRecord
    when = IObjectAddedEvent
    permission_id = nauth.ACT_READ.id


@component.adapter(ICourseInstanceEnrollment)
@interface.implementer(ICourseEnrollmentDetails)
def enrollment_details(record):
    user = User.get_user(record.Username)
    user_details = IUserDetails(user)
    course_details = ICourseDetails(record.CourseInstance)

    scope = getattr(record, 'RealEnrollmentStatus', None)
    course_enrollment_details = CourseEnrollmentDetails(User=user_details,
                                                        Course=course_details,
                                                        Scope=scope)

    return course_enrollment_details


@component.adapter(ICourseInstanceEnrollmentRecord, IObjectAddedEvent)
@interface.implementer(IWebhookPayload)
def user_enrolled_payload(record, _event):
    user_details = IUserDetails(record.Principal)
    course_details = ICourseDetails(record.CourseInstance)

    course_enrollment_details = CourseEnrollmentDetails(User=user_details,
                                                        Course=course_details,
                                                        Scope=record.Scope)

    payload = UserEnrolledEvent(EventType=EVENT_USER_ENROLLED,
                                Data=course_enrollment_details)
    return payload
