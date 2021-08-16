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

from nti.webhooks.interfaces import IWebhookDeliveryAttempt
from nti.webhooks.interfaces import IWebhookSubscription
from nti.webhooks.interfaces import IWebhookSubscriptionManager

CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE
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


class SubscriptionViewMixin(AbstractAuthenticatedView):

    @Lazy
    def is_admin(self):
        return is_admin(self.remoteUser)

    def _predicate(self):
        if not self.is_admin and not is_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden(_('Cannot view subscriptions.'))

    def _do_call(self):
        raise NotImplementedError()

    def externalize_result(self, result):
        return to_external_object(result,
                                  policy_name='zapier',
                                  name="zapier-webhook")

    def __call__(self):
        self._predicate()
        result = self._do_call()
        return self.externalize_result(result)


class AbstractSubscriptionUploadView(ModeledContentUploadRequestUtilsMixin,
                                     SubscriptionViewMixin):

    def __call__(self):
        self._predicate()
        result = super(AbstractSubscriptionUploadView, self).__call__()
        return self.externalize_result(result)


@view_config(route_name='objects.generic.traversal',
             request_method='POST',
             renderer='rest',
             context=IntegrationProviderPathAdapter,
             name=SUBSCRIPTIONS_VIEW)
class AddSubscriptionView(AbstractSubscriptionUploadView):

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

        return internal_subscription


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
             context=IWebhookSubscription,
             permission=nauth.ACT_READ)
class GetSubscriptionView(SubscriptionViewMixin):

    def _do_call(self):
        return self.context


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

    def _do_call(self):
        self._predicate()
        result = LocatedExternalDict()
        items = self.get_subscriptions()
        self._batch_items_iterable(result, items)
        result[TOTAL] = result[ITEM_COUNT]

        return result


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IWebhookSubscription,
             name='DeliveryAttempts',
             permission=nauth.ACT_READ)
class GetSubscriptionDeliveryAttemptsView(SubscriptionViewMixin):

    def _do_call(self):
        result_dict = LocatedExternalDict()

        result_dict[MIMETYPE] = 'application/vnd.nextthought.zapier.subscriptiondeliveryhistory'
        result_dict[CLASS] = 'SubscriptionDeliveryHistory'
        result_dict[ITEMS] = [x for x in self.context.values()]

        return result_dict


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IWebhookSubscription,
             name='DeliveryHistory',
             permission=nauth.ACT_READ)
class GetSubscriptionHistoryView(SubscriptionViewMixin,
                                 BatchingUtilsMixin):
    """
    Return the delivery attempts for the subscription.

    batchSize
            The size of the batch.  Defaults to 50.

    batchStart
            The starting batch index.  Defaults to 0.

    sortOn
            The case insensitive field to sort on. Options are ``createdtime``
            and ``status``.
            The default is ``createdtime``.

    sortOrder
            The sort direction. Options are ``ascending`` and
            ``descending``. Sort order is ascending by default.

    search
            String to use for searching messages of the delivery attempts.
    """

    _DEFAULT_BATCH_SIZE = 50
    _DEFAULT_BATCH_START = 0

    _default_sort = 'createdtime'
    _sort_keys = {
        'createdtime': lambda x: x.createdTime,
        'status': lambda x: x.status,
    }

    def _get_sorted_result_set(self, items, sort_key, sort_desc=False):
        """
        Get the sorted result set.
        """
        items = sorted(items, key=sort_key, reverse=sort_desc)
        return items

    def _get_sort_params(self):
        sort_on = self.request.params.get('sortOn') or ''
        sort_on = sort_on.lower()
        sort_on = sort_on if sort_on in self._sort_keys else self._default_sort
        sort_key = self._sort_keys.get(sort_on)

        # Ascending is default
        sort_order = self.request.params.get('sortOrder')
        sort_descending = bool(
            sort_order and sort_order.lower() == 'descending')

        return sort_key, sort_descending

    def _search_items(self, search_param, items):
        """
        For the given search_param, return the results for those users
        if it matches realname, alias, or displayable username.
        """

        def matches(item):
            return item.message and search_param in item.message.lower()

        results = [x for x in items if matches(x)]

        return results

    def _get_items(self, result_dict):
        """
        Sort and batch records.
        """
        search = self.request.params.get('search')
        search_param = search and search.lower()

        items = self.context.values()
        if search_param:
            items = self._search_items(search_param, items)

        sort_key, sort_descending = self._get_sort_params()

        result_set = self._get_sorted_result_set(items,
                                                 sort_key,
                                                 sort_descending)

        total_items = result_dict[TOTAL] = len(result_set)
        self._batch_items_iterable(result_dict,
                                   result_set,
                                   number_items_needed=total_items)

        return [record for record in result_dict.get(ITEMS)]

    def _do_call(self):
        result_dict = LocatedExternalDict()

        result_dict[MIMETYPE] = 'application/vnd.nextthought.zapier.subscriptiondeliveryhistory'
        result_dict[CLASS] = 'SubscriptionDeliveryHistory'
        result_dict[ITEMS] = self._get_items(result_dict)

        return result_dict


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IWebhookDeliveryAttempt,
             name='Request',
             permission=nauth.ACT_READ)
class GetDeliveryAttemptRequest(SubscriptionViewMixin):

    def _do_call(self):
        return self.context.request


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IWebhookDeliveryAttempt,
             name='Response',
             permission=nauth.ACT_READ)
class GetDeliveryAttemptResponse(SubscriptionViewMixin):

    def _do_call(self):
        return self.context.response
