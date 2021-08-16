#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import zope.i18nmessageid

MessageFactory = zope.i18nmessageid.MessageFactory(__name__)

#: Path of users off of our ISiteAuthentication
AUTH_USERS_PATH = "users"

#: Path name for enrollments path adapter
ENROLLMENTS_PATH = "enrollments"

#: Zapier workspace
ZAPIER = "zapier"

#: Path name for path adapter
ZAPIER_PATH = "zapier"

#: Subscriptions view
SUBSCRIPTIONS_VIEW = "subscriptions"

#: Subscription delivery history view
DELIVERY_HISTORY_VIEW = "DeliveryHistory"

#: Delivery attempt request
DELIVERY_REQUEST_VIEW = "Request"

#: Delivery attempt response
DELIVERY_RESPONSE_VIEW = "Response"

#: Authenticated user resolve view
RESOLVE_ME = "resolve_me"

#: View name for searching users
USER_SEARCH = "user_search"
