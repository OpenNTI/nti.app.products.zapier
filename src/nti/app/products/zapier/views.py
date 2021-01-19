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

from zope.security import checkPermission

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.zapier import MessageFactory as _
from nti.app.products.zapier import SUBSCRIPTIONS_VIEW

from nti.app.products.zapier.interfaces import IWebhookSubscriber
from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.products.zapier.model import SubscriptionRequest

from nti.app.products.zapier.traversal import IntegrationProviderPathAdapter

from nti.appserver.ugd_edit_views import UGDDeleteView

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.webhooks.interfaces import IWebhookSubscription
from nti.webhooks.interfaces import IWebhookSubscriptionManager

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IntegrationProviderPathAdapter,
             permission=ACT_READ,
             name="resolve_me")
class AuthenticatedUserView(AbstractAuthenticatedView):

    def __call__(self):
        return to_external_object(IUserDetails(self.remoteUser),
                                  policy_name='zapier')


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
             context=IntegrationProviderPathAdapter,
             name=SUBSCRIPTIONS_VIEW)
class AddSubscriptionView(SubscriptionViewMixin,
                          AbstractAuthenticatedView,
                          ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        input = super(AddSubscriptionView, self).readInput(value=value)
        input.setdefault("MimeType", SubscriptionRequest.mimeType)
        return input

    def _subscriber(self):
        subpath = self.request.subpath
        if len(subpath) < 2:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Must specify a object type and event in url."),
                             },
                             None)
        subscriber_name = "%s.%s" % (subpath[0], subpath[1])
        subscriber = component.queryAdapter(self.request,
                                            IWebhookSubscriber,
                                            name=subscriber_name)
        if subscriber is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Unsupported object and event type combination"),
                             },
                             None)
        return subscriber

    def _do_call(self):
        creator = self.remoteUser
        subscription = self.readCreateUpdateContentObject(creator)
        site_manager = getSite().getSiteManager()
        subscriber = self._subscriber()

        internal_subscription = \
            subscriber.subscribe(site_manager,
                                 subscription.target)

        self.request.response.status_int = 201

        # Choose our externalizer to conform to our docs
        ext_obj = to_external_object(internal_subscription,
                                     policy_name='zapier',
                                     name="zapier-webhook")

        return ext_obj


@view_config(route_name='objects.generic.traversal',
             request_method='DELETE',
             renderer='rest',
             context=IWebhookSubscription,
             permission=nauth.ACT_DELETE)
class DeleteSubscriptionView(UGDDeleteView):

    def _do_delete_object(self, theObject):
        del theObject.__parent__[theObject.__name__]
        return theObject


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IntegrationProviderPathAdapter,
             name=SUBSCRIPTIONS_VIEW)
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
                         if checkPermission(ACT_READ.id, subscription)]

        reverse = self.sortOrder == "descending"
        return sorted(subscriptions, key=attrgetter(self.sortOn), reverse=reverse)

    def __call__(self, site=None):
        self._predicate()
        result = LocatedExternalDict()
        items = self.get_subscriptions()
        self._batch_items_iterable(result, items)
        result[TOTAL] = result[ITEM_COUNT]

        return to_external_object(result,
                                  policy_name='zapier',
                                  name="zapier-webhook")
