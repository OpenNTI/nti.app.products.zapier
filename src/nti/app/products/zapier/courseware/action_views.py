#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.products.courseware.views.course_admin_views import AbstractUserCourseEnrollView

from nti.app.products.zapier.courseware.interfaces import ICourseEnrollmentDetails

from nti.app.products.zapier.traversal import EnrollmentsPathAdapter

from nti.common.string import is_true

from nti.contenttypes.courses.interfaces import ENROLLMENT_SCOPE_VOCABULARY
from nti.contenttypes.courses.interfaces import ES_PUBLIC
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import is_instructor_in_hierarchy

from nti.coremetadata.interfaces import IUser

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.dataserver.interfaces import ISiteAdminUtility

from nti.dataserver.users import User

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.app.externalization.error import raise_json_error

from nti.app.products.zapier import MessageFactory as _

from nti.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             context=EnrollmentsPathAdapter,
             request_method='POST',
             renderer='rest')
class EnrollUserView(AbstractUserCourseEnrollView):

    @Lazy
    def _is_admin(self):
        return is_admin(self.remoteUser)

    @Lazy
    def _is_site_admin(self):
        return is_site_admin(self.remoteUser)

    def _can_admin_user(self, user):
        # Verify a site admin is administering a user in their site.
        result = True
        if self._is_site_admin:
            admin_utility = component.getUtility(ISiteAdminUtility)
            result = admin_utility.can_administer_user(self.remoteUser, user)
        return result

    def _predicate(self, user):
        # 403 if not admin or instructor or self
        return  (self._is_admin or self._is_site_admin) \
                and self._can_admin_user(user)

    def _get_user(self, values):
        username = values.get('Username')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'Username',
                                 'message': _(u'Missing data'),
                                 'code': 'RequiredMissing'
                             },
                             None)

        user = User.get_user(username)
        if not user or not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'Username',
                                 'message': _(u"User not found."),
                                 'code': 'UserNotFound',
                             },
                             None)

        return user

    def _get_course(self, values):
        # get validate course entry
        course_ntiid = values.get('CourseId')
        if not course_ntiid:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'CourseId',
                                 'message': _(u'Missing data'),
                                 'code': 'RequiredMissing'
                             },
                             None)

        course = find_object_with_ntiid(course_ntiid)
        course = ICourseInstance(course, None)
        if course is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'CourseId',
                                 'message': _(u"Course not found."),
                                 'code': 'CourseNotFound',
                             },
                             None)
        return course

    def _get_scope(self, values):
        scope = values.get('scope', ES_PUBLIC)
        if not scope or scope not in ENROLLMENT_SCOPE_VOCABULARY.by_token:
            valid_scopes = ENROLLMENT_SCOPE_VOCABULARY.by_token.keys()
            valid_scopes = ', '.join(valid_scopes)
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'Scope',
                                 'message': _(u"Invalid scope, must be one of: ${scopes}",
                                              mapping={'scopes': valid_scopes}),
                                 'code': 'InvalidScope',
                             },
                             None)

        return scope

    def _validate_non_instructor(self, course, user):
        if is_instructor_in_hierarchy(course, user):
            msg = _(u'User is an instructor in course hierarchy.')
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': 'Username',
                                 'message': msg,
                                 'code': 'UserIsInstructor',
                             },
                             None)

    def __call__(self):
        values = self.readInput()
        user = self._get_user(values)

        if not self._predicate(user):
            raise_json_error(self.request,
                             hexc.HTTPForbidden,
                             {
                                 'message': _(u"Cannot modify user enrollments."),
                                 'code': 'CannotAccessUserEnrollmentsError',
                             },
                             None)

        course = self._get_course(values)
        scope = self._get_scope(values)
        self._validate_non_instructor(course, user)
        interaction = is_true(values.get('email') or values.get('interaction'))

        enrollment = self._do_course_enrollment(course, user, scope, interaction)

        return to_external_object(ICourseEnrollmentDetails(enrollment),
                                  policy_name='zapier')
