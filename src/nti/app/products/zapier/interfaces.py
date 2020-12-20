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

from nti.base.interfaces import ICreated
from nti.base.interfaces import ICreatedTime

from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import checkRealname

from nti.schema.field import DecodingValidTextLine
from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidChoice
from nti.schema.field import ValidTextLine
from nti.schema.field import ValidDatetime

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


class ISubscriptionRequest(ICreated):

    target = HTTPURL(title=u"Target Url",
                     required=True)


class IExternalEvent(interface.Interface):

    eventType = ValidChoice(title=u"Event Type",
                            vocabulary=EVENT_VOCABULARY,
                            required=True)

    data = Attribute(u"The data object for the external event.")


class IUserCreatedEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a user is added.
    """

    data = Object(IUserDetails,
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