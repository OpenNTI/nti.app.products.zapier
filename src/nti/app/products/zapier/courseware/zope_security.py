#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.interfaces import IRolePermissionManager
from zope.securitypolicy.principalpermission import AnnotationPrincipalPermissionManager
from zope.securitypolicy.rolepermission import AnnotationRolePermissionManager

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord

from nti.dataserver import authorization as nauth


@component.adapter(ICourseInstanceEnrollmentRecord)
@interface.implementer(IPrincipalPermissionManager)
class EnrollmentRecordPrincipalPermissionManager(AnnotationPrincipalPermissionManager):

    def __init__(self, context):
        super(EnrollmentRecordPrincipalPermissionManager, self).__init__(context)
        # We must call this here so that permissions are updated if the state changes
        self.initialize()

    @Lazy
    def __principal_id(self):
        principal = self._context.Principal
        return getattr(principal, 'id', None)

    def initialize(self):
        # Initialize with perms for the enrollment record owner
        if self.__principal_id:
            for permission in (nauth.ACT_READ,):
                self.grantPermissionToPrincipal(permission.id, self.__principal_id)
