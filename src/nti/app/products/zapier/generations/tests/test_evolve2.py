#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from contextlib import contextmanager

from hamcrest import assert_that
from hamcrest import is_

from zope import component

from zope import interface

from zope.component.hooks import getSite
from zope.component.hooks import site

from zope.lifecycleevent import IObjectAddedEvent

from zope.security.management import checkPermission
from zope.security.management import setSecurityPolicy

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager

from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy

from nti.app.products.zapier.generations import evolve2

from nti.app.products.zapier.generations.tests import GenerationLayerTest

from nti.app.site.hostpolicy import create_site

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.authorization_utils import zope_interaction

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

from nti.webhooks.api import subscribe_to_resource

import nti.dataserver.tests.mock_dataserver as mock_dataserver


class TestEvolve2(GenerationLayerTest):

    @WithMockDSTrans
    def test_evolve2(self):

        conn = mock_dataserver.current_transaction

        class _Context(object):
            pass
        context = _Context()
        context.connection = conn

        ds_folder = context.connection.root()['nti.dataserver']

        with site(ds_folder):
            ds_role_manager = IPrincipalRoleManager(ds_folder)
            nti_admin = User.create_user(username='nti.admin')
            ds_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id,
                                                  nti_admin.username)

        # Set up old state for a couple sites
        site_one = create_site('site.one')
        subscription_one_ntiid = \
            self.create_subscription_in_site(nti_admin, site_one)

        site_two = create_site('site.two')
        subscription_two_ntiid = \
            self.create_subscription_in_site(nti_admin, site_two)

        # Will need to reset the dataserver util since evolution sets its own
        mock_ds = component.getUtility(IDataserver)
        evolve2.do_evolve(context)
        component.provideUtility(mock_ds, IDataserver)

        # Ensure updated permissinos for both sites
        self.check_post_evolution_perms(site_one, subscription_one_ntiid)
        self.check_post_evolution_perms(site_two, subscription_two_ntiid)

    def check_post_evolution_perms(self, site_one, subscription_one_ntiid):
        with site(site_one):
            subscription = find_object_with_ntiid(subscription_one_ntiid)
            owner_username = site_one.__name__ + '.owner'
            owner = User.get_user(owner_username)
            nti_admin = User.get_user('nti.admin')
            site_admin_username = site_one.__name__ + '.admin'
            site_admin = User.get_user(site_admin_username)

            with _security_policy_context(ZopeSecurityPolicy):
                self.assert_user_perms(owner, subscription, has_perms=True)
                self.assert_user_perms(nti_admin, subscription, has_perms=True)
                self.assert_user_perms(site_admin, subscription, has_perms=False)

    def create_subscription_in_site(self, nti_admin, site_one):
        with site(site_one):
            site_admin_username = site_one.__name__ + '.admin'
            site_one_admin = User.create_user(username=site_admin_username)
            site_role_manager = IPrincipalRoleManager(site_one)
            site_role_manager.assignRoleToPrincipal(ROLE_SITE_ADMIN.id,
                                                    site_one_admin.username)

            owner_username= site_one.__name__ + '.owner'
            site_one_owner = User.create_user(username=owner_username)

            subscription = \
                subscribe_to_resource(getSite().getSiteManager(),
                                      to=str('https://google.com/'),
                                      for_=interface.Interface,
                                      when=IObjectAddedEvent,
                                      dialect_id='zapier',
                                      owner_id=site_one_owner.username,
                                      permission_id='zope.View')
            subscription_one_ntiid = to_external_ntiid_oid(subscription)

            # Remove existing perms for NTI admin to simulate old state
            role_per = IRolePermissionManager(subscription)
            perms = role_per.getPermissionsForRole(ROLE_ADMIN.id)

            for perm, setting in perms:
                role_per.unsetPermissionFromRole(perm, ROLE_ADMIN.id)

            with _security_policy_context(ZopeSecurityPolicy):
                self.assert_user_perms(site_one_owner, subscription, has_perms=True)
                self.assert_user_perms(nti_admin, subscription, has_perms=False)
                self.assert_user_perms(site_one_admin, subscription, has_perms=False)

        return subscription_one_ntiid

    @staticmethod
    def assert_user_perms(user, context, has_perms=True):
        with zope_interaction(user.username):
            assert_that(checkPermission('zope.View', context), is_(has_perms))
            assert_that(checkPermission('nti.actions.delete', context), is_(has_perms))


@contextmanager
def _security_policy_context(new_policy):
    old_security_policy = setSecurityPolicy(new_policy)
    try:
        yield
    finally:
        setSecurityPolicy(old_security_policy)
