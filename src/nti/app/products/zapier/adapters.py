#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.lifecycleevent import IObjectAddedEvent

from nti.app.products.zapier.interfaces import EVENT_USER_CREATE
from nti.app.products.zapier.interfaces import IExternalSubscription

from nti.app.products.zapier.model import UserDetails
from nti.app.products.zapier.model import UserCreatedEvent
from nti.app.products.zapier.model import UserCreatedSubscription

from nti.coremetadata.interfaces import IUser

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.mailer.interfaces import IEmailAddressable

from nti.webhooks.interfaces import IWebhookPayload
from nti.webhooks.interfaces import IWebhookSubscription


def _email_for_user(user):
    addr = IEmailAddressable(user, None)
    return addr.email if addr is not None else None


def _realname_for_user(user):
    named = IFriendlyNamed(user, None)
    return named and named.realname


@component.adapter(IUser, IObjectAddedEvent)
@interface.implementer(IWebhookPayload)
def _user_payload(user):
    details = UserDetails(username=user.username,
                          email=_email_for_user(user),
                          name=_realname_for_user(user))

    details.createdTime = getattr(user, 'createdTime', 0)
    details.last_login = getattr(user, 'lastLoginTime', None)

    payload = UserCreatedEvent(event_type=EVENT_USER_CREATE,
                               data = details)
    interface.alsoProvides(payload, IWebhookPayload)
    return payload
