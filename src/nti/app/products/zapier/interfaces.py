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

from nti.base.interfaces import ICreated
from nti.base.interfaces import ICreatedTime

from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import checkRealname

from nti.schema.field import DecodingValidTextLine
from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidChoice
from nti.schema.field import ValidTextLine

EVENT_USER_CREATE = u"user.create"
EVENT_USER_ENROLL = u"user.enroll"
EVENT_COURSE_CREATE = u"course.create"
EVENT_COURSE_COMPLETE = u"course.complete"

EVENTS = (EVENT_USER_CREATE,
          EVENT_USER_ENROLL,
          EVENT_COURSE_CREATE,
          EVENT_COURSE_COMPLETE)

EVENT_VOCABULARY = vocabulary.SimpleVocabulary(
    [vocabulary.SimpleTerm(_x) for _x in EVENTS]
)


class IUserDetails(ICreatedTime):

    username = DecodingValidTextLine(title=u'The username', min_length=5)

    email = ValidTextLine(title=u'Email',
                          description=u'',
                          required=False,
                          constraint=checkEmailAddress)

    name = TextLine(title=u'Your name',
                        description=u"Your full name",
                        required=False,
                        constraint=checkRealname)

    last_login = interface.Attribute("The last login time")


class IExternalSubscription(ICreated):

    event_type = ValidChoice(title=u"Event Type",
                             vocabulary=EVENT_VOCABULARY,
                             required=True)

    target = HTTPURL(title=u"Target Url",
                     required=True)


class IUserCreatedSubscription(IExternalSubscription):
    """
    Defines a subscription for receiving events when users are added
    to the system.
    """


class IExternalEvent(interface.Interface):

    event_type = ValidChoice(title=u"Event Type",
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
