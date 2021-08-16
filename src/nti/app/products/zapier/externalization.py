#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import ExternalizationPolicy
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.traversal.traversal import normal_resource_path

from nti.webhooks.externalization import DeliveryAttemptExternalizer

from nti.webhooks.interfaces import IWebhookDeliveryAttempt
from nti.webhooks.interfaces import IWebhookSubscription


#: An externalization policy that uses ISO 8601 date strings.
ISODateExternalizationPolicy = ExternalizationPolicy(
    use_iso8601_for_unix_timestamp=True
)


@component.adapter(IWebhookSubscription)
@interface.implementer(IInternalObjectExternalizer)
class SubscriptionExternalizer(InterfaceObjectIO):

    __external_class_name__ = "WebhookSubscription"

    _ext_iface_upper_bound = IWebhookSubscription

    _excluded_out_ivars_ = frozenset({
        # Dialect_id is better than dialect.
        'dialect',
        # for_ and when are arbitrary classes or interface
        # specifications. They're not meaningful to end users by themselves.
        'for_', 'when',
        # Redundant IDCTimes data
        'created', 'modified',
        'dialect_id', 'attempt_limit', 'permission_id'
    }) | InterfaceObjectIO._excluded_out_ivars_

    EXT_FIELD_MAP = {
        "active": "Active",
        "Last Modified": None,
        "NTIID": "Id",
        "owner_id": "OwnerId",
        "status_message": "Status",
        "to": "Target",
    }

    def toExternalObject(self, *args, **kwargs): # pylint:disable=signature-differs
        result = super(SubscriptionExternalizer, self).toExternalObject(*args, **kwargs)
        result.pop("OID", None)
        for name, ext_name in self.EXT_FIELD_MAP.items():
            value = result.pop(name, None)
            if value is not None and ext_name:
                result[ext_name] = value

        result["href"] = normal_resource_path(self._ext_self)

        return result


@component.adapter(IWebhookDeliveryAttempt)
@interface.implementer(IInternalObjectExternalizer)
class WebhookDeliveryAttemptExternalizer(DeliveryAttemptExternalizer):

    _ext_iface_upper_bound = IWebhookDeliveryAttempt

    _excluded_out_ivars_ = frozenset({
        'request',
        'response'
    }) | DeliveryAttemptExternalizer._excluded_out_ivars_

    def toExternalObject(self, *args, **kwargs): # pylint:disable=signature-differs
        result = super(WebhookDeliveryAttemptExternalizer, self).toExternalObject(*args, **kwargs)
        # result["href"] = normal_resource_path(self._ext_self)

        return result
