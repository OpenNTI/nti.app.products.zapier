#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.securitypolicy.interfaces import IRolePermissionManager

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ACT_DELETE

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

from nti.webhooks.interfaces import IWebhookSubscriptionManager

generation = 2
PERMISSIONS_TO_GRANT = (ACT_READ, ACT_DELETE)

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def process_site(updated):
    utilities_in_current_site = component.getUtilitiesFor(IWebhookSubscriptionManager)
    updated_subscriptions = set()
    for _, sub_manager in utilities_in_current_site:
        for subscription in sub_manager.values():
            updated_subscriptions.add(subscription)
            role_per = IRolePermissionManager(subscription)
            for perm_id in PERMISSIONS_TO_GRANT:
                role_per.grantPermissionToRole(perm_id.id, ROLE_ADMIN.id)

    updated |= updated_subscriptions

    return bool(updated_subscriptions)


def do_evolve(context, generation=generation):
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
            "Hooks not installed?"

        sites = get_all_host_sites()
        updated = set()
        sites_updated = 0
        for site in sites:
            with current_site(site):
                if process_site(updated):
                    sites_updated += 1

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done.  Updated %s subscriptions in %d/%d sites',
                generation, len(updated), sites_updated, len(sites))


def evolve(context):
    """
    Evolve to generation 2 by updating the permissions for all subscriptions
    by providing ACT_READ and ACT_DELETE for the nti.admin role
    """
    do_evolve(context, generation)
