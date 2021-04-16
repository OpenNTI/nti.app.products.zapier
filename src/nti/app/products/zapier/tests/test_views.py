#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import shutil

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import not_none

from zope import component

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.assessment.submission import AssignmentSubmission
from nti.assessment.submission import QuestionSetSubmission
from nti.assessment.submission import QuestionSubmission

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import find_object_with_ntiid


class TestResolveMe(ApplicationLayerTest, ZapierTestMixin):

    default_origin = 'https://alpha.nextthought.com'

    def _call_FUT(self, **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        path = self.get_workspace_link('resolve_me', **workspace_kwargs)

        res = self.testapp.get(path, **kwargs)

        return res

    @WithSharedApplicationMockDS(testapp=True)
    def test_success(self):
        with mock_ds.mock_db_trans():
            boo_user = self._create_user(u"booradley",
                                         external_value={
                                             u"email": u"boo@maycomb.com",
                                             u"realname": u"Arthur Radley"
                                         })
            user_env = self._make_extra_environ(boo_user.username)

        res = self._call_FUT(extra_environ=user_env)

        assert_that(res.json_body, has_entries({
            u"Username": u"booradley",
            u"Email": u"boo@maycomb.com",
            u"Realname": u"Arthur Radley",
            u"LastSeen": not_none(),
            u"LastLogin": not_none(),
        }))

    @WithSharedApplicationMockDS(testapp=True)
    def test_failure(self):
        self.testapp.get(b'/dataserver2/zapier/resolve_me',
                         status=401)


class TestSubscriptions(ApplicationLayerTest, ZapierTestMixin):

    layer = PersistentInstructedCourseApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def tearDown(self):
        """
        Our janux.ou.edu site should have no courses in it.
        """
        with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
            library = component.getUtility(IContentPackageLibrary)
            enumeration = IDelimitedHierarchyContentPackageEnumeration(library)
            # pylint: disable=no-member
            shutil.rmtree(enumeration.root.absolute_path, True)

    def _create_subscription(self, obj_type, event_type, target_url, **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        base_create_path = self.get_workspace_link('create_subscription',
                                                   **workspace_kwargs)

        path = b'%s/%s/%s' % (base_create_path, obj_type, event_type)
        res = self.testapp.post_json(path,
                                     {
                                         "target": target_url
                                     },
                                     **kwargs)
        return res

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_create(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url)

        assert_that(res.json_body, has_entries({
            "Target": target_url,
            "Id": not_none(),
            "OwnerId": self.extra_environ_default_user.lower(),
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_create_invalid(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user",
                                        "invalid_event_type",
                                        target_url,
                                        status=422)

        assert_that(res.json_body, has_entries({
            "message": "Unsupported object and event type combination",
        }))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_admin_created_subscriptions_fire(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url)

        subscription_ntiid = res.json_body['Id']
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(0))

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            import uuid
            self._create_user(uuid.uuid4().hex,
                              external_value={
                                  u'realname': u'Admin Created Test',
                                  u'email': u'zap-test-user@zaptest.org',
                              })

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(1))

    def _get_admin_href(self):
        service_res = self.fetch_service_doc()
        workspaces = service_res.json_body['Items']
        courses_workspace = next(
            x for x in workspaces if x['Title'] == 'Courses'
        )
        admin_href = self.require_link_href_with_rel(courses_workspace,
                                                     "AdminLevels")
        return admin_href

    def _publish(self, ext_obj):
        publish_url = self.require_link_href_with_rel(ext_obj, 'publish')
        return self.testapp.post_json(publish_url).json_body

    def _create_course(self):
        """
        Create course and return ext
        """
        admin_href = self._get_admin_href()
        test_admin_key = 'ZapierTestKey'
        admin_res = self.testapp.post_json(admin_href, {'key': test_admin_key}).json_body
        new_admin_href = admin_res['href']
        new_course = self.testapp.post_json(new_admin_href,
                                            {'ProviderUniqueID': 'ZapierTestCourse',
                                             'title': 'ZapierTestCourse',
                                             'RichDescription': 'ZapierTestCourse',
                                             'Preview': False})

        new_course = new_course.json_body
        entry_url = self.require_link_href_with_rel(new_course, 'CourseCatalogEntry')
        self.testapp.put_json(entry_url, {'Preview': False})
        return new_course

    def _create_assignment(self, ext_course):
        course_evaluations_url = \
            self.require_link_href_with_rel(ext_course, 'CourseEvaluations')

        ext_assn = {
            "MimeType": "application/vnd.nextthought.assessment.assignment",
            "title": "Zapier Test Assignment",
            "total_points": 100,
            "completion_passing_percent": 1,
            "auto_grade": True,
            "parts": [
                {
                    "Class": "AssignmentPart",
                    "MimeType": "application/vnd.nextthought.assessment.assignmentpart",
                    "question_set": {
                        "Class": "QuestionSet",
                        "MimeType": "application/vnd.nextthought.naquestionset",
                        "questions": [
                            {
                                "MimeType": "application/vnd.nextthought.naquestion",
                                "content": "Choose first",
                                "parts": [
                                    {
                                        "MimeType": "application/vnd.nextthought.assessment.multiplechoicepart",
                                        "content": "",
                                        "choices": ["Choice 1", "Choice 2"],
                                        "solutions": [
                                            {
                                                "Class": "MultipleChoiceSolution",
                                                "MimeType": "application/vnd.nextthought.assessment.multiplechoicesolution",
                                                "value": 0
                                            }
                                        ],
                                        "hints": []
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        assn = self.testapp.post_json(course_evaluations_url, ext_assn)

        return self._publish(assn.json_body)

    def _enroll(self, username, ext_course_instance):
        enroll_url = '/dataserver2/CourseAdmin/UserCourseEnroll'
        res = self.testapp.post_json(enroll_url,
                                     {'ntiid': ext_course_instance['NTIID'],
                                      'username': username})
        return res.json_body

    def _commence(self, ext_assignment, extra_environ):
        # Get the `Commence` url for the user and start the assignment
        user_assignment = self.testapp.get(ext_assignment['href'],
                                           extra_environ=extra_environ)
        commence_url = self.require_link_href_with_rel(user_assignment.json_body,
                                                       'Commence')
        self.testapp.post(commence_url, extra_environ=extra_environ)

    def _submit(self, ext_assignment, extra_environ=None):
        question_set = ext_assignment['parts'][0]['question_set']
        question_id = question_set['questions'][0]['NTIID']
        q_submission = QuestionSubmission(questionId=question_id,
                                          parts=[0])
        qset_submission = QuestionSetSubmission(questionSetId=question_set['NTIID'],
                                                questions=[q_submission])
        submission = AssignmentSubmission(assignmentId=ext_assignment['NTIID'],
                                          parts=[qset_submission])
        submission = toExternalObject(submission)

        self._commence(ext_assignment, extra_environ)

        # Submit the assignment
        submission_url = self.require_link_href_with_rel(ext_assignment, 'Submit')
        res = self.testapp.post_json(submission_url,
                                     submission,
                                     extra_environ=extra_environ)

        return res.json_body

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_course_progress_subscriptions_fire(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("course", "progress_updated", target_url)

        subscription_ntiid = res.json_body['Id']
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(0))

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            import uuid
            user = self._create_user(uuid.uuid4().hex,
                                     external_value={
                                         u'realname': u'Course Progress Test',
                                         u'email': u'zap-test-user@zaptest.org'
                                     })
            username = user.username

        # Submit a successful assignment
        course = self._create_course()
        assignment = self._create_assignment(course)
        self._enroll(username, course)
        user_env = self._make_extra_environ(username)
        self._submit(assignment, extra_environ=user_env)

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(1))

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_list(self):
        target_url = "https://localhost/handle_new_user"
        self._create_subscription("user", "created", target_url)

        res = self.testapp.get(b'/dataserver2/zapier/subscriptions')
        body = res.json_body
        assert_that(body, has_entries({
            "Items": has_length(1)
        }))

        assert_that(body["Items"][0], has_entries({
            "Target": target_url,
            "Id": not_none(),
            "OwnerId": self.extra_environ_default_user.lower(),
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))
