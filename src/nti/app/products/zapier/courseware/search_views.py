#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid.view import view_config

from nti.app.products.courseware.views.catalog_views import CourseCollectionView

from nti.app.products.zapier.courseware.interfaces import ICourseDetails
from nti.app.products.zapier.courseware.interfaces import IZapierCourseCatalogCollection

from nti.dataserver import authorization as nauth

from nti.externalization import to_external_object


logger = __import__('logging').getLogger(__name__)


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
