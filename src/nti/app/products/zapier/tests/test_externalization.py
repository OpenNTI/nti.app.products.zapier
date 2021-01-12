#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import not_
from hamcrest import not_none

from zope.lifecycleevent import IObjectAddedEvent

from nti.app.products.zapier.authorization import ACT_VIEW_EVENTS
from nti.app.products.zapier.tests import ZapierTestCase

from nti.coremetadata.interfaces import IUser

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.externalization import to_external_object

from nti.externalization.externalization.standard_fields import datetime_to_string

from nti.webhooks.api import subscribe_to_resource


class TestExternalization(ZapierTestCase):

    @WithMockDSTrans
    def testExternalization(self):
        obj = subscribe_to_resource(self.ds.dataserver_folder,
                                    to="https://google.com",
                                    for_=IUser,
                                    when=IObjectAddedEvent,
                                    dialect_id=u"zapier",
                                    owner_id=u"bargle",
                                    permission_id=ACT_VIEW_EVENTS.id)

        ext_obj = to_external_object(obj,
                                     policy_name='zapier',
                                     name="zapier-webhook")

        assert_that(ext_obj, has_entries({
            "Target": obj.to,
            "Id": not_none(),
            "OwnerId": obj.owner_id,
            "CreatedTime": datetime_to_string(obj.created),
            "Active": obj.active,
            "Status": obj.status_message,
            "DialectId": obj.dialect_id,
            "href": not_none(),
        }))

        removed_keys = (
            "active",
            "Last Modified",
            "NTIID",
            "OID",
            "owner_id"
            "status_message",
            "to",
            "dialect_id",
        )
        for key in removed_keys:
            assert_that(ext_obj, not_(has_key(key)), key)
