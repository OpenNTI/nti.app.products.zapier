#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    from abc import ABC
except ImportError: # Python 2
    from abc import ABCMeta
    ABC = ABCMeta('ABC', (object,), {'__slots__': ()})

from abc import abstractproperty

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.lifecycleevent import IObjectAddedEvent

from zope.security.interfaces import IPrincipal

from nti.app.authentication import get_remote_user

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS

from nti.app.products.zapier.interfaces import EVENT_USER_CREATED
from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import IWebhookSubscriber

from nti.app.products.zapier.model import UserCreatedEvent
from nti.app.products.zapier.model import UserDetails

from nti.app.products.zapier.traversal import get_integration_provider

from nti.coremetadata.interfaces import IUser

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.datetime import datetime_from_timestamp

from nti.mailer.interfaces import IEmailAddressable

from nti.webhooks.api import subscribe_to_resource

from nti.webhooks.interfaces import IWebhookPayload


def _email_for_user(user):
    addr = IEmailAddressable(user, None)
    return addr.email if addr is not None else None


def _realname_for_user(user):
    named = IFriendlyNamed(user, None)
    return named and named.realname


@component.adapter(IUser)
@interface.implementer(IWebhookPayload)
def user_payload(user):
    details = IUserDetails(user)

    payload = UserCreatedEvent(EventType=EVENT_USER_CREATED,
                               Data=details)
    return payload


@component.adapter(IUser)
@interface.implementer(IUserDetails)
def details_from_user(user):
    last_login = datetime_from_timestamp(getattr(user, 'lastLoginTime', None))
    last_seen = datetime_from_timestamp(getattr(user, 'lastSeenTime', None))
    created_time = getattr(user, 'createdTime', None)

    details = UserDetails(Username=user.username,
                          Email=_email_for_user(user),
                          Realname=_realname_for_user(user),
                          createdTime=created_time,
                          LastLogin=last_login,
                          LastSeen=last_seen)

    details.user = user

    return details


class AbstractWebhookSubscriber(ABC):

    permission_id = ACT_VIEW_EVENTS.id

    def __init__(self, request):
        self.request = request

    @abstractproperty
    def for_(self):
        """
        Subclasses must implement this to define the object of the subscription.
        """
        raise NotImplementedError()

    @abstractproperty
    def when(self):
        """
        Subclasses must implement this to define the event of the subscription.
        """
        raise NotImplementedError()

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


@interface.implementer(IWebhookSubscriber)
class UserCreatedWebhookSubscriber(AbstractWebhookSubscriber):
    for_ = IUser
    when = IObjectAddedEvent
