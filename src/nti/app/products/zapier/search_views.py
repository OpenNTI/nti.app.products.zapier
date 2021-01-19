#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid.view import view_config

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.zapier import USER_SEARCH

from nti.app.products.zapier.interfaces import IUserDetails

from nti.appserver.usersearch_views import UserSearchView

from nti.coremetadata.interfaces import IUser

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
             context=ISiteAuthentication,
             permission=ACT_SEARCH,
             name=USER_SEARCH)
class ZapierUserSearchView(UserSearchView):

    def filter_result(self, all_results):
        results = []
        for result in all_results:
            if IUser.providedBy(result):
                results.append(IUserDetails(result))
        return super(ZapierUserSearchView, self).filter_result(results)

    def externalize_objects(self, results):
        return [to_external_object(user_details, policy_name='zapier')
                for user_details in results]

