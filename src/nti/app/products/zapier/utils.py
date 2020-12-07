#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.webhooks.dialect import DefaultWebhookDialect


class ZapierWebhookDialect(DefaultWebhookDialect):

    externalizer_name = 'zapier-webhook-delivery'