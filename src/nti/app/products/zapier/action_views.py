#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import interface

from zope.event import notify

from nti.app.authentication import get_remote_user

from nti.app.externalization import internalization as obj_io

from nti.app.externalization.error import raise_json_error

from nti.app.products.zapier import MessageFactory as _

from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.products.zapier.traversal import ZapierUsersPathAdapter

from nti.appserver.account_creation_views import _create_user

from nti.appserver.interfaces import UserCreatedByAdminWithRequestEvent

from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             context=ZapierUsersPathAdapter,
             request_method='POST',
             renderer='rest')
def create_user(request):
    # TODO: Should we move this logic to account_creation_views in appserver?
    remote_user = get_remote_user(request)
    if not is_admin(remote_user) and not is_site_admin(remote_user):
        raise hexc.HTTPForbidden(_('Cannot create users.'))

    externalValue = obj_io.read_body_as_external_object(request)

    # Must have email for this view, as we'll need to send the link to the
    # user to set their initial password.
    if not externalValue.get('email', None):
        raise_json_error(request,
                         hexc.HTTPUnprocessableEntity,
                         {
                             'field': 'email',
                             'message': _(u'Missing data'),
                             'code': 'RequiredMissing'
                         },
                         None)

    new_user = _create_user(request, externalValue, require_password=False)
    interface.alsoProvides(new_user, IRequireSetPassword)

    # Yay, we created one. Respond with the Created code, and location.
    request.response.status_int = 201

    # Respond with the location of the new_user
    __traceback_info__ = new_user
    assert new_user.__parent__
    assert new_user.__name__

    request.response.location = request.resource_url(new_user)
    logger.debug("Notifying of creation of new user %s", new_user)
    notify(UserCreatedByAdminWithRequestEvent(new_user, request))

    return to_external_object(IUserDetails(new_user),
                              policy_name='zapier')
