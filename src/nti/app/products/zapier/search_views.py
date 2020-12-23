#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid.view import view_config

from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.products.zapier.traversal import IntegrationProviderPathAdapter

from nti.appserver.usersearch_views import UserSearchView

from nti.dataserver.authorization import ACT_SEARCH

from nti.externalization import to_external_object


logger = __import__('logging').getLogger(__name__)


def _user_externalizer():
    def _externalize_user(user):
        return to_external_object(IUserDetails(user),
                                  policy_name='zapier')

    return _externalize_user


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IntegrationProviderPathAdapter,
             permission=ACT_SEARCH,
             name="user_search")
class ZapierUserSearchView(UserSearchView):
    # TODO: May want to move this to a context under the
    #   host site, once we add that context for user creation

    users_only = True

    def item_externalizer(self, remote_user):
        return _user_externalizer()

