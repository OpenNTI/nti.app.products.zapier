#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid.view import view_config

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.products.courseware.views.catalog_views import CourseCollectionView

from nti.app.products.zapier import USER_SEARCH

from nti.app.products.zapier.interfaces import ICourseDetails
from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import IZapierCourseCatalogCollection

from nti.appserver.usersearch_views import UserSearchView

from nti.coremetadata.interfaces import IUser

from nti.dataserver import authorization as nauth

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
             permission=nauth.ACT_SEARCH,
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


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IZapierCourseCatalogCollection,
             permission=nauth.ACT_READ)
class ZapierCourseCollectionView(CourseCollectionView):

    def _get_items(self):
        """
        Get the relevant courses details
        """
        result = super(ZapierCourseCollectionView, self)._get_items()
        result = [ICourseDetails(x) for x in result]
        return result

    def _externalize_result(self, result):
        return to_external_object(result,
                                  policy_name='zapier')
