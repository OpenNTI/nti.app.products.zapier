#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.interface import Attribute

from zope.interface.interfaces import IObjectEvent

from zope.schema import TextLine
from zope.schema import vocabulary

from zope.traversing.interfaces import IPathAdapter

from nti.appserver.workspaces import IWorkspace

from nti.appserver.workspaces.interfaces import ICatalogCollection

from nti.base.interfaces import ICreated
from nti.base.interfaces import ICreatedTime
from nti.base.interfaces import ILastModified

from nti.base.schema import Number

from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import checkRealname

from nti.contenttypes.completion.interfaces import IProgress

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import DecodingValidTextLine
from nti.schema.field import Float
from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidChoice
from nti.schema.field import ValidDatetime
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine

EVENT_USER_CREATED = u"user.created"
EVENT_USER_ENROLLED = u"user.enrolled"
EVENT_COURSE_CREATED = u"course.created"
EVENT_PROGESS_UPDATED = u"course.progress_updated"

EVENTS = (EVENT_USER_CREATED,
          EVENT_USER_ENROLLED,
          EVENT_COURSE_CREATED,
          EVENT_PROGESS_UPDATED)

EVENT_VOCABULARY = vocabulary.SimpleVocabulary(
    [vocabulary.SimpleTerm(_x) for _x in EVENTS]
)


class IUserDetails(ICreatedTime):

    Username = DecodingValidTextLine(title=u'The username', min_length=5)

    Email = ValidTextLine(title=u'Email',
                          description=u'',
                          required=False,
                          constraint=checkEmailAddress)

    Realname = TextLine(title=u'Your name',
                        description=u"Your full name",
                        required=False,
                        constraint=checkRealname)

    LastLogin = ValidDatetime(title=u"Last login",
                              description=u"Last login time.",
                              required=False)

    LastSeen = ValidDatetime(title=u"Last seen",
                             description=u"The latest record of user activity.",
                             required=False)


class ICourseDetails(ILastModified):

    Id = ValidNTIID(title=u"Course catalog entry NTIID")

    ProviderId = ValidTextLine(title=u"The unique id assigned by the provider",
                               required=True,
                               max_length=32,
                               min_length=1)

    StartDate = ValidDatetime(title=u"The date on which the course begins",
                              description=u"Currently optional; a missing value means the course already started",
                              required=False)

    EndDate = ValidDatetime(title=u"The date on which the course ends",
                            description=u"Currently optional; a missing value means the course has no defined end date.",
                            required=False)

    Title = ValidTextLine(title=u"The human-readable section name of this item",
                          required=True,
                          min_length=1,
                          max_length=140)

    Description = ValidText(title=u"The human-readable description",
                            default=u'',
                            required=False)


class ISubscriptionRequest(ICreated):

    target = HTTPURL(title=u"Target Url",
                     required=True)


class IExternalEvent(interface.Interface):

    EventType = ValidChoice(title=u"Event Type",
                            vocabulary=EVENT_VOCABULARY,
                            required=True)

    Data = Attribute(u"The data object for the external event.")


class IUserCreatedEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a user is added.
    """

    Data = Object(IUserDetails,
                  title=u"Information for the newly created user.",
                  required=True)


class IIntegrationProviderPathAdapter(IPathAdapter):
    """
    Path adapter with the name of the integration provider (e.g. zapier)
    """


class IWebhookSubscriber(interface.Interface):
    """
    Intended as an adapter to find an appropriate factory given requested
    subscription type information.
    """

    def subscribe(context, target):
        """
        Register a new webhook subscription with the given arguments.

        :return:  The stored webhook subscription
        """


class IZapierWorkspace(IWorkspace):
    """
    A workspace for Zapier info and links.
    """


class IZapierCourseCatalogCollection(ICatalogCollection):
    """
    Provides context for view and available courses for course search
    """


class IProgressDetails(interface.Interface):
    """
    Indicates the progress made for a particular user and course
    """

    AbsoluteProgress = Number(title=u"A number indicating the absolute progress made on an item.",
                              default=None,
                              required=False)

    MaxPossibleProgress = Number(title=u"A number indicating the max possible progress that could be made on an item. May be null.",
                                 default=None,
                                 required=False)

    PercentageProgress = Float(title=u"A percentage measure of how much progress exists",
                               required=True,
                               readonly=True,
                               min=0.0,
                               max=1.0)


class IProgressSummary(interface.Interface):
    """
    Provides context information for user progress in a course when it is
    updated
    """

    User = Object(IUserDetails,
                  title=u"User",
                  description=u"The user whose progress was updated.",
                  required=True)

    Course = Object(ICourseDetails,
                  title=u"Course",
                  description=u"The course for which progress was updated.",
                  required=True)

    Progress = Object(IProgressDetails,
                  title=u"User Progress",
                  description=u"The current progress information for the "
                              u"related course and user.",
                  required=True)


class IExternalUserProgressUpdatedEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a user's progress
    for a course has been updated.
    """

    Data = Object(IProgressSummary,
                  title=u"Information for the newly created user.",
                  required=True)


class IZapierUserProgressUpdatedEvent(IObjectEvent):
    """
    Zapier-specific user progress updated event, triggered by the
    platform's IUserProgressUpdatedEvent, but with altered data that works
    better with nti.webhooks.
    """

    EnrollmentRecord = Object(ICourseInstanceEnrollmentRecord,
                              title=u"Course for which the progress is being updated.",
                              required=True)

    User = Object(IUserDetails,
                  title=u"User",
                  description=u"The user whose progress was updated.",
                  required=True)

    Progress = Object(IProgress,
                      title=u"Progress",
                      description=u"The current progress information for the "
                                  u"related course and user.",
                      required=True)
