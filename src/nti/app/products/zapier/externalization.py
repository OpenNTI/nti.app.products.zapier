#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.products.zapier.interfaces import IUserDetails

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.externalization.standard_fields import timestamp_to_string

from nti.externalization.interfaces import IInternalObjectExternalizer


@component.adapter(IUserDetails)
@interface.implementer(IInternalObjectExternalizer)
class ZapierUserDetailsExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = IUserDetails

    def __init__(self, context, iface_upper_bound=None, validate_after_update=False):
        super(ZapierUserDetailsExternalizer, self).__init__(context,
                                                            iface_upper_bound,
                                                            validate_after_update)
        self.context = context

    @Lazy
    def user(self):
        return self.context.user

    def toExternalObject(self, **kwargs):
        result = super(ZapierUserDetailsExternalizer, self).toExternalObject(**kwargs)

        result.pop("CreatedTime")
        result["createdTime"] = timestamp_to_string(self.user.createdTime)
        result['lastLogin'] = timestamp_to_string(self.user.lastLoginTime)
        result['lastSeen'] = timestamp_to_string(self.user.lastSeenTime)

        return result
