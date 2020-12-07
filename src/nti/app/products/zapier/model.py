#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.lifecycleevent import IObjectAddedEvent

from nti.app.products.zapier.interfaces import EVENT_USER_CREATE
from nti.app.products.zapier.interfaces import IUserCreatedEvent
from nti.app.products.zapier.interfaces import IUserCreatedSubscription
from nti.app.products.zapier.interfaces import IUserDetails

from nti.coremetadata.interfaces import IUser

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured


@WithRepr
@interface.implementer(IUserCreatedEvent)
class UserCreatedEvent(SchemaConfigured):
    createDirectFieldProperties(IUserCreatedEvent)

    mime_type = mimeType = 'application/vnd.nextthought.api.event.usercreated'


@WithRepr
@interface.implementer(IUserDetails)
class UserDetails(SchemaConfigured):
    createDirectFieldProperties(IUserDetails)

    mime_type = mimeType = 'application/vnd.nextthought.api.userdetails'


@WithRepr
@interface.implementer(IUserCreatedSubscription)
class UserCreatedSubscription(SchemaConfigured):
    createDirectFieldProperties(IUserCreatedSubscription)

    mime_type = mimeType = 'application/vnd.nextthought.api.subscription.usercreated'

    target = alias('to')

    @property
    def event_type(self):
        return EVENT_USER_CREATE

    @property
    def for_(self):
        return IUser

    @property
    def when(self):
        return IObjectAddedEvent
