#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import unittest

from hamcrest import assert_that
from hamcrest import has_length

import zope

from nti.app.products.zapier import ZAPIER

from nti.dataserver.tests import DSInjectorMixin

from nti.testing.layers import ConfiguringLayerMixin
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver',
                       'nti.externalization',
                       'nti.app.products.zapier')

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass


class ZapierTestCase(unittest.TestCase):
    layer = SharedConfiguringTestLayer


class ZapierTestMixin(object):

    def get_workspace_link(self, rel_name, **kwargs):
        path = b'/dataserver2/service'
        res = self.testapp.get(path, **kwargs)
        zapier_ws = [ws for ws in res.json_body['Items'] if ws['Title'] == ZAPIER]
        assert_that(zapier_ws, has_length(1))
        zapier_ws = zapier_ws[0]
        create_users_href = self.require_link_href_with_rel(zapier_ws,
                                                            rel_name)
        return create_users_href
