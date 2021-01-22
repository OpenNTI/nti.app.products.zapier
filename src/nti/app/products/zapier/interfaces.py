#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.interface import Attribute

from zope.schema import TextLine
from zope.schema import vocabulary

from zope.traversing.interfaces import IPathAdapter

from nti.appserver.workspaces import IWorkspace

from nti.appserver.workspaces.interfaces import ICatalogCollection

from nti.base.interfaces import ICreated
from nti.base.interfaces import ICreatedTime
from nti.base.interfaces import ILastModified

from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import checkRealname

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import DecodingValidTextLine
from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidChoice
from nti.schema.field import ValidDatetime
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine

EVENT_USER_CREATED = u"user.created"
EVENT_USER_ENROLLED = u"user.enrolled"
EVENT_COURSE_CREATED = u"course.created"
EVENT_COURSE_COMPLETED = u"course.completed"

EVENTS = (EVENT_USER_CREATED,
          EVENT_USER_ENROLLED,
          EVENT_COURSE_CREATED,
          EVENT_COURSE_COMPLETED)

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
