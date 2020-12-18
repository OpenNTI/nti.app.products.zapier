#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.authentication import get_remote_user

from nti.app.products.zapier import MessageFactory as _

from nti.app.products.zapier.interfaces import IUserDetails

from nti.app.products.zapier.traversal import ZapierUsersPathAdapter

from nti.appserver.account_creation_views import create_account_as_admin

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin

from nti.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             context=ZapierUsersPathAdapter,
             request_method='POST',
             renderer='rest')
def create_user(request):
    remote_user = get_remote_user(request)
    if not is_admin(remote_user) and not is_site_admin(remote_user):
        raise hexc.HTTPForbidden(_('Cannot create users.'))

    result = create_account_as_admin(request)

    return to_external_object(IUserDetails(result),
                              policy_name='zapier')
