#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import nameparser

from zope import component
from zope import interface

from zope.i18n.interfaces import IUserPreferredLanguages

from nti.app.products.zapier.interfaces import IUserDetails

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.common.nameparser import constants as np_constants


@component.adapter(IUserDetails)
@interface.implementer(IExternalMappingDecorator)
class _EnglishFirstAndLastNameDecorator(Singleton):
    """
    If a user's first preferred language is English,
    then assume that they provided a first and last name and return that
    in the profile data.

    .. note::
            This is an incredibly Western and even US centric way of
            looking at things. The restriction to those that prefer
            English as their language is an attempt to limit the damage.
    """

    def decorateExternalMapping(self, original, external):
        realname = original.Realname
        if not realname or '@' in realname:
            return

        preflangs = IUserPreferredLanguages(original.user, None)
        if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
            # FIXME: Adapted from nti.dataserver.appserver.decorators
            # CFA: another suffix we see from certain financial quarters
            constants = np_constants(extra_suffixes=('cfa',))
            human_name = nameparser.HumanName(realname, constants=constants)
            last = human_name.last or human_name.first
            first = human_name.first or human_name.last
            if first:
                external['NonI18NFirstName'] = first
                external['NonI18NLastName'] = last
