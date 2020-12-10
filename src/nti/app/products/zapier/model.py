#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from nti.app.products.zapier.interfaces import IUserCreatedEvent
from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import ISubscriptionRequest

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
@interface.implementer(ISubscriptionRequest)
class SubscriptionRequest(SchemaConfigured):
    createDirectFieldProperties(ISubscriptionRequest)

    mime_type = mimeType = 'application/vnd.nextthought.webhooks.subscription.request'

    target = alias('to')
