#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from Acquisition import aq_base

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.authentication import get_remote_user

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.internalization import update_object_from_external_object

from nti.app.products.zapier import MessageFactory as _

from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.products.zapier.model import UserDetails

from nti.app.products.zapier.traversal import ZapierUsersPathAdapter

from nti.appserver.account_creation_views import create_account_as_admin

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.externalization import to_external_object

from nti.externalization.internalization import find_factory_for

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             context=ZapierUsersPathAdapter,
             request_method='POST',
             renderer='rest')
def create_user(request):
    remote_user = get_remote_user(request)
    if not is_admin(remote_user) and not is_site_admin(remote_user):
        raise hexc.HTTPForbidden(_('Cannot create users.'))

    externalValue = read_body_as_external_object(request)

    # Not required by the model, but required by the view
    for field_name in ('Email', 'Realname'):
        if field_name not in externalValue:
            raise_json_error(request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'field': field_name,
                                 'message': _(u'Missing data'),
                                 'code': 'RequiredMissing'
                             },
                             None)

    externalValue.setdefault('MimeType', UserDetails.mime_type)
    factory = find_factory_for(externalValue)
    details = update_object_from_external_object(aq_base(factory()),
                                                 externalValue,
                                                 notify=False,
                                                 request=request)

    ext_obj = {
        'Username': details.Username,
        'realname': details.Realname,
        'email': details.Email
    }

    result = create_account_as_admin(request, ext_obj=ext_obj)

    return to_external_object(IUserDetails(result),
                              policy_name='zapier')
