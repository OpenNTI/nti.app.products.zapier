#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.lifecycleevent import IObjectAddedEvent

from zope.security.interfaces import IPrincipal

from nti.app.authentication import get_remote_user

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS

from nti.app.products.zapier.interfaces import EVENT_PROGESS_UPDATED
from nti.app.products.zapier.interfaces import EVENT_USER_CREATED
from nti.app.products.zapier.interfaces import ICourseDetails
from nti.app.products.zapier.interfaces import IProgressDetails
from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import IWebhookSubscriber
from nti.app.products.zapier.interfaces import IZapierUserProgressUpdatedEvent

from nti.app.products.zapier.model import CourseDetails
from nti.app.products.zapier.model import ExternalUserProgressUpdatedEvent
from nti.app.products.zapier.model import ProgressDetails
from nti.app.products.zapier.model import ProgressSummary
from nti.app.products.zapier.model import UserCreatedEvent
from nti.app.products.zapier.model import UserDetails
from nti.app.products.zapier.model import ZapierUserProgressUpdatedEvent

from nti.app.products.zapier.traversal import get_integration_provider

from nti.contenttypes.completion.interfaces import IProgress
from nti.contenttypes.completion.interfaces import IUserProgressUpdatedEvent

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.contenttypes.courses.utils import get_enrollment_record

from nti.coremetadata.interfaces import IUser

from nti.dataserver import authorization as nauth

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.datetime import datetime_from_timestamp

from nti.mailer.interfaces import IEmailAddressable

from nti.webhooks.api import subscribe_to_resource

from nti.webhooks.interfaces import IWebhookPayload


@interface.implementer(IZapierUserProgressUpdatedEvent)
@component.adapter(IUserProgressUpdatedEvent)
def _zapier_user_progress(event):
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


@interface.implementer(IProgressDetails)
@component.adapter(IProgress)
def _progress_details(progress):
    return ProgressDetails(
        AbsoluteProgress=progress.AbsoluteProgress,
        MaxPossibleProgress=progress.MaxPossibleProgress
    )


def _email_for_user(user):
    addr = IEmailAddressable(user, None)
    return addr.email if addr is not None else None


def _realname_for_user(user):
    named = IFriendlyNamed(user, None)
    return named and named.realname


@component.adapter(IUser)
@interface.implementer(IWebhookPayload)
def _user_payload(user):
    details = IUserDetails(user)

    payload = UserCreatedEvent(EventType=EVENT_USER_CREATED,
                               Data=details)
    return payload


@component.adapter(ICourseInstanceEnrollmentRecord, IZapierUserProgressUpdatedEvent)
@interface.implementer(IWebhookPayload)
def _course_progress_updated_payload(record, event):
    user_details = IUserDetails(event.User)
    course_details = ICourseDetails(record.CourseInstance)
    progress_details = IProgressDetails(event.Progress)

    data = ProgressSummary(User=user_details,
                           Course=course_details,
                           Progress=progress_details)

    payload = ExternalUserProgressUpdatedEvent(EventType=EVENT_PROGESS_UPDATED,
                                               Data=data)
    return payload


def _ts_to_datetime(timestamp):
    if timestamp is None:
        return None
    return datetime_from_timestamp(timestamp)


@component.adapter(IUser)
@interface.implementer(IUserDetails)
def _details_from_user(user):
    last_login = _ts_to_datetime(getattr(user, 'lastLoginTime', None))
    last_seen = _ts_to_datetime(getattr(user, 'lastSeenTime', None))
    created_time = getattr(user, 'createdTime', None)

    details = UserDetails(Username=user.username,
                          Email=_email_for_user(user),
                          Realname=_realname_for_user(user),
                          createdTime=created_time,
                          LastLogin=last_login,
                          LastSeen=last_seen)

    details.user = user

    return details


@component.adapter(ICourseCatalogEntry)
@interface.implementer(ICourseDetails)
def _details_from_catalog_entry(catalog_entry):
    created_time = getattr(catalog_entry, 'createdTime', None)
    last_modified = getattr(catalog_entry, 'lastModified', None)

    details = CourseDetails(
        Id=catalog_entry.ntiid,
        ProviderId=catalog_entry.ProviderUniqueID,
        StartDate=catalog_entry.StartDate,
        EndDate=catalog_entry.EndDate,
        Title=catalog_entry.title,
        Description=catalog_entry.description,
        createdTime=created_time,
        lastModified=last_modified
    )

    details.catalog_entry = catalog_entry

    return details


@component.adapter(ICourseInstance)
@interface.implementer(ICourseDetails)
def _details_from_course(course):
    catalog_entry = ICourseCatalogEntry(course, None)
    return ICourseDetails(catalog_entry, None)


@interface.implementer(IWebhookSubscriber)
class AbstractWebhookSubscriber(object):

    permission_id = ACT_VIEW_EVENTS.id

    def __init__(self, request):
        self.request = request

    @Lazy
    def owner_id(self):
        return IPrincipal(get_remote_user(self.request)).id

    @Lazy
    def dialect_id(self):
        return get_integration_provider(self.request)

    def subscribe(self, context, target):
        webhook_subscription = \
            subscribe_to_resource(context,
                                  to=target,
                                  for_=self.for_,
                                  when=self.when,
                                  dialect_id=self.dialect_id,
                                  owner_id=self.owner_id,
                                  permission_id=self.permission_id)
        return webhook_subscription


class UserCreatedWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = IUser
    when = IObjectAddedEvent


class CourseProgressUpdatedWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = ICourseInstanceEnrollmentRecord
    when = IZapierUserProgressUpdatedEvent
    permission_id = nauth.ACT_READ.id
