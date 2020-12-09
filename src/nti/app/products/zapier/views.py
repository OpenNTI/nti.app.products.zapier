#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from operator import attrgetter

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.security.interfaces import IPrincipal

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.zapier import MessageFactory as _

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS

from nti.app.products.zapier.traversal import SubscriptionsPathAdapter
from nti.app.products.zapier.traversal import get_integration_provider

from nti.appserver.ugd_edit_views import UGDDeleteView

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.dataserver.authorization_acl import has_permission

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.webhooks.api import subscribe_to_resource

from nti.webhooks.interfaces import IWebhookSubscription
from nti.webhooks.interfaces import IWebhookSubscriptionManager

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


class SubscriptionViewMixin(object):

    @Lazy
    def is_admin(self):
        return is_admin(self.remoteUser)

    def _predicate(self):
        if not self.is_admin and not is_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden(_('Cannot view subscriptions.'))

    def __call__(self):
        self._predicate()
        return super(SubscriptionViewMixin, self).__call__()
        

@view_config(route_name='objects.generic.traversal',
             request_method='POST',
             renderer='rest',
             context=SubscriptionsPathAdapter)
class AddSubscriptionView(SubscriptionViewMixin,
                          AbstractAuthenticatedView,
                          ModeledContentUploadRequestUtilsMixin):

    def _do_call(self):
        creator = self.remoteUser
        subscription = self.readCreateUpdateContentObject(creator)

        principal_id = IPrincipal(creator).id

        site_manager = getSite().getSiteManager()

        internal_subscription = \
            subscribe_to_resource(site_manager,
                                  to=subscription.target,
                                  for_=subscription.for_,
                                  when=subscription.when,
                                  dialect_id=get_integration_provider(self.request),
                                  owner_id=principal_id,
                                  permission_id=ACT_VIEW_EVENTS.id)

        # TODO: could use a different externalizer by defining
        #   `_v_nti_render_externalizable_name` on the request
        self.request.response.status_int = 201
        return internal_subscription


@view_config(route_name='objects.generic.traversal',
             request_method='DELETE',
             renderer='rest',
             context=IWebhookSubscription,
             permission=nauth.ACT_DELETE)
class DeleteSubscriptionView(SubscriptionViewMixin,
                             UGDDeleteView):

    def _do_delete_object(self, theObject):
        del theObject.__parent__[theObject.__name__]
        return theObject


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=SubscriptionsPathAdapter)
class ListSubscriptions(SubscriptionViewMixin,
                        AbstractAuthenticatedView,
                        BatchingUtilsMixin):

    _DEFAULT_BATCH_SIZE = 30
    _DEFAULT_BATCH_START = 0

    _ALLOWED_SORTING = {
        'owner': 'owner_id',
        'owner_id': 'owner_id',
        'target': 'to',
        'to': 'to',
        'active': 'active',
        'status_message': 'status_message',
        'createdTime': 'createdTime',
        'CreatedTime': 'createdTime',
    }

    _DEFAULT_SORT = 'createdTime'

    @Lazy
    def params(self):
        return CaseInsensitiveDict(**self.request.params)

    @Lazy
    def sortOn(self):
        # pylint: disable=no-member
        sort = self.params.get('sortOn')
        return self._ALLOWED_SORTING.get(sort) or self._DEFAULT_SORT

    @property
    def sortOrder(self):
        # pylint: disable=no-member
        return self.params.get('sortOrder', 'ascending')

    def get_subscriptions(self):
        utilities_in_current_site = component.getUtilitiesFor(IWebhookSubscriptionManager)
        subscriptions = [subscription
                         for _, sub_manager in utilities_in_current_site
                         for subscription in sub_manager.values()
                         if has_permission(ACT_READ, subscription, self.remoteUser)]

        reverse = self.sortOrder == "descending"
        return sorted(subscriptions, key=attrgetter(self.sortOn), reverse=reverse)

    def __call__(self, site=None):
        result = LocatedExternalDict()
        items = self.get_subscriptions()
        self._batch_items_iterable(result, items)
        result[TOTAL] = result[ITEM_COUNT]
        return result
