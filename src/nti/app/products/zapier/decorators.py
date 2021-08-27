#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import nameparser

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.i18n.interfaces import IUserPreferredLanguages

from nti.app.products.zapier import DELIVERY_HISTORY_VIEW
from nti.app.products.zapier import DELIVERY_REQUEST_VIEW
from nti.app.products.zapier import DELIVERY_RESPONSE_VIEW

from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.dataserver.authorization import is_admin

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.singleton import Singleton

from nti.common.nameparser import constants as np_constants

from nti.links import Link

from nti.webhooks.interfaces import IWebhookDeliveryAttempt
from nti.webhooks.interfaces import IWebhookSubscription

LINKS = StandardExternalFields.LINKS


@component.adapter(IUserDetails)
@interface.implementer(IExternalMappingDecorator)
class _EnglishFirstAndLastNameDecorator(Singleton):
    """
    If a user's first preferred language is English,
    then assume that they provided a first and last name and return that
    in the profile data.

    .. note::
            This is an incredibly Western and even US centric way of
            looking at things. The restriction to those that prefer
            English as their language is an attempt to limit the damage.
    """

    def decorateExternalMapping(self, original, external):
        realname = original.Realname
        if not realname or '@' in realname:
            return

        preflangs = IUserPreferredLanguages(original.user, None)
        if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
            # FIXME: Adapted from nti.dataserver.appserver.decorators
            # CFA: another suffix we see from certain financial quarters
            constants = np_constants(extra_suffixes=('cfa',))
            human_name = nameparser.HumanName(realname, constants=constants)
            last = human_name.last or human_name.first
            first = human_name.first or human_name.last
            if first:
                external['NonI18NFirstName'] = first
                external['NonI18NLastName'] = last


@component.adapter(IWebhookSubscription, IRequest)
@interface.implementer(IExternalMappingDecorator)
class SubscriptionLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        if is_admin(self.remoteUser):
            links = result.setdefault(LINKS, [])
            links.append(Link(context,
                              rel='delivery_history',
                              elements=(DELIVERY_HISTORY_VIEW,)))


@component.adapter(IWebhookDeliveryAttempt, IRequest)
@interface.implementer(IExternalMappingDecorator)
class DeliveryAttemptLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        if is_admin(self.remoteUser):
            links = result.setdefault(LINKS, [])
            links.append(Link(context,
                              rel='delivery_request',
                              elements=(DELIVERY_REQUEST_VIEW,)))
            links.append(Link(context,
                              rel='delivery_response',
                              elements=(DELIVERY_RESPONSE_VIEW,)))
