#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.interface.interfaces import ObjectEvent

from nti.app.products.zapier.courseware.interfaces import ICompletionContextProgressDetails
from nti.app.products.zapier.courseware.interfaces import ICourseCreatedEvent
from nti.app.products.zapier.courseware.interfaces import ICourseDetails
from nti.app.products.zapier.courseware.interfaces import ICourseEnrollmentDetails
from nti.app.products.zapier.courseware.interfaces import IExternalUserProgressUpdatedEvent
from nti.app.products.zapier.courseware.interfaces import IProgressDetails
from nti.app.products.zapier.courseware.interfaces import IProgressSummary
from nti.app.products.zapier.courseware.interfaces import IUserEnrolledEvent
from nti.app.products.zapier.courseware.interfaces import IZapierUserProgressUpdatedEvent

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.webhooks.interfaces import IWebhookPayload


@WithRepr
@interface.implementer(ICourseDetails)
class CourseDetails(SchemaConfigured):
    createDirectFieldProperties(ICourseDetails)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.coursedetails'




@WithRepr
@interface.implementer(IProgressSummary)
class ProgressSummary(SchemaConfigured):
    createDirectFieldProperties(IProgressSummary)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.progresssummary'


@WithRepr
@interface.implementer(IExternalUserProgressUpdatedEvent, IWebhookPayload)
class ExternalUserProgressUpdatedEvent(SchemaConfigured):
    createDirectFieldProperties(IExternalUserProgressUpdatedEvent)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.event.userprogressupdated'
    __external_class_name__ = 'UserProgressUpdatedEvent'


@WithRepr
@interface.implementer(ICourseCreatedEvent, IWebhookPayload)
class CourseCreatedEvent(SchemaConfigured):
    createDirectFieldProperties(ICourseCreatedEvent)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.event.coursecreated'
    __external_class_name__ = 'CourseCreatedEvent'


@WithRepr
@interface.implementer(IZapierUserProgressUpdatedEvent)
class ZapierUserProgressUpdatedEvent(ObjectEvent):

    EnrollmentRecord = alias('object')

    def __init__(self, obj, user, progress):
        super(ZapierUserProgressUpdatedEvent, self).__init__(obj)
        self.User = user
        self.Progress = progress


@interface.implementer(IProgressDetails)
class ProgressDetails(object):
    # Taking a cue from the implementation of
    # nti.contenttypes.completion.progress.Progress:
    # There are use cases where lots of these may be created. Therefore,
    # we skip SchemaConfigured here to improve throughput. We're responsible
    # for setting our defaults and any validation. Since these are only built
    # internally, we at least have control over our fate.

    __slots__ = ('AbsoluteProgress', 'MaxPossibleProgress')
    __external_can_create__ = False

    __external_class_name__ = "ProgressDetails"
    mime_type = mimeType = 'application/vnd.nextthought.zapier.progressdetails'

    def __init__(self, AbsoluteProgress=None, MaxPossibleProgress=None):
        self.AbsoluteProgress = AbsoluteProgress
        self.MaxPossibleProgress = MaxPossibleProgress

    @property
    def PercentageProgress(self):
        try:
            result = float(self.AbsoluteProgress) / float(self.MaxPossibleProgress)
        except (TypeError, ZeroDivisionError, AttributeError):
            result = None
        return result

    def __repr__(self):
        clazz = self.__class__.__name__
        result = "%s(AbsoluteProgress=%r, MaxPossibleProgress=%r)" \
                 % (clazz, self.AbsoluteProgress, self.MaxPossibleProgress)
        return result


@WithRepr
@interface.implementer(ICompletionContextProgressDetails)
class CompletionContextProgressDetails(ProgressDetails):

    __external_can_create__ = False

    __external_class_name__ = "CompletionContextProgressDetails"
    mimeType = mime_type = "application/vnd.nextthought.zapier.completioncontextprogressdetails"

    def __init__(self, Completed=None, Success=None, *args, **kwargs):
        super(CompletionContextProgressDetails, self).__init__(*args, **kwargs)
        self.Completed = Completed
        self.Success = Success


@WithRepr
@interface.implementer(ICourseEnrollmentDetails)
class CourseEnrollmentDetails(SchemaConfigured):
    createDirectFieldProperties(ICourseEnrollmentDetails)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.courseenrollmentdetails'


@WithRepr
@interface.implementer(IUserEnrolledEvent, IWebhookPayload)
class UserEnrolledEvent(SchemaConfigured):
    createDirectFieldProperties(IUserEnrolledEvent)

    mime_type = mimeType = 'application/vnd.nextthought.zapier.event.userenrolled'
    __external_class_name__ = 'UserEnrolledEvent'
