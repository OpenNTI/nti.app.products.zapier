#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.interface.interfaces import IObjectEvent

from nti.app.products.zapier.interfaces import IUserDetails
from nti.app.products.zapier.interfaces import IExternalEvent

from nti.appserver.workspaces.interfaces import ICatalogCollection

from nti.base.interfaces import ILastModified

from nti.base.schema import Number

from nti.contentfragments.schema import HTMLContentFragment

from nti.contenttypes.completion.interfaces import IProgress

from nti.contenttypes.courses.interfaces import ENROLLMENT_SCOPE_VOCABULARY
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import Bool
from nti.schema.field import Float
from nti.schema.field import Object
from nti.schema.field import ValidChoice
from nti.schema.field import ValidDatetime
from nti.schema.field import ValidText
from nti.schema.field import ValidTextLine


class ICourseDetails(ILastModified):

    Id = ValidNTIID(title=u"Course catalog entry NTIID")

    ProviderId = ValidTextLine(title=u"The unique id assigned by the provider",
                               required=True,
                               max_length=32,
                               min_length=1)

    StartDate = ValidDatetime(title=u"The date on which the course begins",
                              description=u"Currently optional; a missing value means the course already started",
                              required=False)

    EndDate = ValidDatetime(title=u"The date on which the course ends",
                            description=u"Currently optional; a missing value means the course has no defined end date.",
                            required=False)

    Title = ValidTextLine(title=u"The human-readable section name of this item",
                          required=True,
                          min_length=1,
                          max_length=140)

    Description = ValidText(title=u"The human-readable description",
                            default=u'',
                            required=False)

    RichDescription = HTMLContentFragment(title=u"An embelished version of the description of this course",
                                          description=u"""An HTMLContentFragment providing an embelished description
                                          for the course.  This provides storage for a description with basic html formatting""",
                                          required=False,
                                          default=u'')


class IZapierCourseCatalogCollection(ICatalogCollection):
    """
    Provides context for view and available courses for course search
    """


class IProgressDetails(interface.Interface):
    """
    Indicates the progress made for a particular user and course
    """

    AbsoluteProgress = Number(title=u"A number indicating the absolute progress made on an item.",
                              default=None,
                              required=False)

    MaxPossibleProgress = Number(title=u"A number indicating the max possible progress that could be made on an item. May be null.",
                                 default=None,
                                 required=False)

    PercentageProgress = Float(title=u"A percentage measure of how much progress exists",
                               readonly=True,
                               min=0.0,
                               max=1.0)


class ICompletionContextProgressDetails(IProgressDetails):

    Completed = Bool(title=u"Indicates the user has completed the item.",
                     default=False)

    Success = Bool(title=u"Successfully completed",
                   description=u"Indicates the user has successfully completed this item.",
                   default=True)


class IProgressSummary(interface.Interface):
    """
    Provides context information for user progress in a course when it is
    updated
    """

    User = Object(IUserDetails,
                  title=u"User",
                  description=u"The user whose progress was updated.",
                  required=True)

    Course = Object(ICourseDetails,
                    title=u"Course",
                    description=u"The course for which progress was updated.",
                    required=True)

    Progress = Object(IProgressDetails,
                      title=u"User Progress",
                      description=u"The current progress information for the "
                                  u"related course and user.",
                      required=True)


class IExternalUserProgressUpdatedEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a user's progress
    for a course has been updated.
    """

    Data = Object(IProgressSummary,
                  title=u"Information for the newly created user.",
                  required=True)


class IZapierUserProgressUpdatedEvent(IObjectEvent):
    """
    Zapier-specific user progress updated event, triggered by the
    platform's IUserProgressUpdatedEvent, but with altered data that works
    better with nti.webhooks.
    """

    EnrollmentRecord = Object(ICourseInstanceEnrollmentRecord,
                              title=u"Course for which the progress is being updated.",
                              required=True)

    User = Object(IUserDetails,
                  title=u"User",
                  description=u"The user whose progress was updated.",
                  required=True)

    Progress = Object(IProgress,
                      title=u"Progress",
                      description=u"The current progress information for the "
                                  u"related course and user.",
                      required=True)


class ICourseCreatedEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a new course has
    been created.
    """

    Data = Object(ICourseDetails,
                  title=u"Information for the newly created course.",
                  required=True)


class ICourseEnrollmentDetails(interface.Interface):
    """
    Information regarding a user's enrollment in a course.
    """

    User = Object(IUserDetails,
                  title=u"The user information tied to the enrollment.",
                  required=True)

    Course = Object(ICourseDetails,
                    title=u"The course information tied to the enrollment.",
                    required=True)

    Scope = ValidChoice(title=u"The name of the enrollment scope",
                        vocabulary=ENROLLMENT_SCOPE_VOCABULARY,
                        required=False)


class IUserEnrolledEvent(IExternalEvent):
    """
    Sent to any applicable external subscriptions when a new course
    enrollment has been created (i.e. when a user has been enrolled).
    """
    Data = Object(ICourseEnrollmentDetails,
                  title=u"Information for the newly created course.",
                  required=True)
