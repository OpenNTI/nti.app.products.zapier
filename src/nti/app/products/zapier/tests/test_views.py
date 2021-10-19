#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import uuid

import time

import shutil

from hamcrest import anything
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import is_
from hamcrest import not_
from hamcrest import not_none

from zope import component

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.products.courseware.tests import PersistentInstructedCourseApplicationTestLayer

from nti.app.products.zapier.tests import ZapierTestMixin

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.assessment.submission import AssignmentSubmission
from nti.assessment.submission import QuestionSetSubmission
from nti.assessment.submission import QuestionSubmission

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.coremetadata.interfaces import IUser

from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.users.common import set_user_creation_site

from nti.externalization.externalization import toExternalObject

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.webhooks.testing import _clear_mocks
from nti.webhooks.testing import begin_synchronous_delivery
from nti.webhooks.testing import mock_delivery_to


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

    default_username = 'admin.zapier@nextthought.com'

    def _create_subscription(self, obj_type, event_type, target_url,
                             created_time=None,
                             status_message=None,
                             active=True,
                             **kwargs):
        workspace_kwargs = dict()
        if 'extra_environ' in kwargs:
            workspace_kwargs['extra_environ'] = kwargs['extra_environ']
        base_create_path = self.get_workspace_link('create_subscription',
                                                   **workspace_kwargs)

        path = b'/'.join(filter(None, (base_create_path, obj_type, event_type)))
        res = self.testapp.post_json(path,
                                     {
                                         "target": target_url
                                     },
                                     **kwargs)

        if created_time or status_message or not active:
            with mock_ds.mock_db_trans():
                subscription = find_object_with_ntiid(res.json_body['Id'])

                if created_time:
                    subscription.createdTime = created_time

                if not active:
                    manager = subscription.__parent__
                    manager.deactivateSubscription(subscription)

                if status_message:
                    subscription.status_message = status_message

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

    @WithSharedApplicationMockDS(users=('subscription.owner',
                                        'non.owner.admin'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_get(self):
        owner_username = 'subscription.owner'
        owner_env = self._make_extra_environ(username=owner_username)
        nti_admin_env = self._make_extra_environ()
        non_owner_admin = 'non.owner.admin'
        non_owner_env = self._make_extra_environ(username=non_owner_admin)
        with mock_ds.mock_db_trans(site_name='janux.ou.edu'):
            self._make_site_admins(owner_username, non_owner_admin)

        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url,
                                        extra_environ=owner_env).json_body

        subscription_url = res['href']

        # Non owner can't fetch
        self.testapp.get(subscription_url, extra_environ=non_owner_env, status=403)

        # Owner can fetch
        self._test_fetch(owner_env, subscription_url,
                         expected_owner_id=owner_username,
                         expected_target_url=target_url)

        # NTI admins can fetch
        self._test_fetch(nti_admin_env, subscription_url,
                         expected_owner_id=owner_username,
                         expected_target_url=target_url)

    def _test_fetch(self, env, subscription_url,
                    expected_owner_id, expected_target_url):
        res = self.testapp.get(subscription_url, extra_environ=env)
        assert_that(res.json_body, has_entries({
            "Target": expected_target_url,
            "Id": not_none(),
            "OwnerId": expected_owner_id.lower(),
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))

    @WithSharedApplicationMockDS(users=('subscription.owner',
                                        'non.owner.admin'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_delete(self):
        owner_username = 'subscription.owner'
        owner_env = self._make_extra_environ(username=owner_username)
        non_owner_admin = 'non.owner.admin'
        non_owner_env = self._make_extra_environ(username=non_owner_admin)
        nti_admin_env = self._make_extra_environ()
        with mock_ds.mock_db_trans(site_name='janux.ou.edu'):
            self._make_site_admins(owner_username, non_owner_admin)

        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url,
                                        extra_environ=owner_env).json_body

        # Non owner can't delete
        self.testapp.delete(res['href'],
                            extra_environ=non_owner_env,
                            status=403)

        # Owner can delete
        delete_url = self.require_link_href_with_rel(res, 'delete')
        self.testapp.delete(delete_url,
                            extra_environ=owner_env,
                            status=204)

        # NTI admins can delete
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url,
                                        extra_environ=owner_env).json_body

        delete_url = self.require_link_href_with_rel(res, 'delete')
        self.testapp.delete(delete_url,
                            extra_environ=nti_admin_env,
                            status=204)

    @WithSharedApplicationMockDS(users=True,
                                 testapp=True,
                                 default_authenticate=True)
    def test_create_invalid_combo(self):
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
    def test_create_missing_object_or_event_type(self):
        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user",
                                        None,
                                        target_url,
                                        status=422)

        assert_that(res.json_body, has_entries({
            "message": "Must specify a object type and event in url.",
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

    def _create_admin_level(self, key):
        admin_href = self._get_admin_href()
        admin_res = self.testapp.post_json(admin_href, {'key': key}).json_body
        return admin_res

    def _create_course(self, admin_href):
        """
        Create course and return ext
        """
        new_course = self.testapp.post_json(admin_href,
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
        admin_res = self._create_admin_level('ZapierTestKey')
        new_admin_href = admin_res['href']
        try:
            course = self._create_course(new_admin_href)
            assignment = self._create_assignment(course)
            self._enroll(username, course)
            user_env = self._make_extra_environ(username)
            self._submit(assignment, extra_environ=user_env)
        finally:
            # Remove the admin level to avoid issues with rerunning test
            with mock_dataserver.mock_db_trans(site_name='janux.ou.edu'):
                library = component.getUtility(IContentPackageLibrary)
                enumeration = IDelimitedHierarchyContentPackageEnumeration(library)
                # pylint: disable=no-member
                path = enumeration.root.absolute_path + "/Courses/ZapierTestKey"
                shutil.rmtree(path, True)

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(1))

    @WithSharedApplicationMockDS(users=('site.admin.one',
                                        'site.admin.two',
                                        'non.admin'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_list(self):
        site_admin_one_env = self._make_extra_environ(username='site.admin.one')
        site_admin_two_env = self._make_extra_environ(username='site.admin.two')
        non_admin_env = self._make_extra_environ(username='non.admin')
        with mock_ds.mock_db_trans(site_name='janux.ou.edu'):
            self._make_site_admins('site.admin.one', 'site.admin.two')

        # Non-admins have no access
        self.testapp.get(b'/dataserver2/zapier/subscriptions',
                         extra_environ=non_admin_env, status=403)

        target_one = "https://localhost/handle_new_user_one"
        created_time = time.time()
        self._create_subscription("user", "created", target_one,
                                  extra_environ=site_admin_one_env,
                                  created_time=created_time)

        res = self.testapp.get(b'/dataserver2/zapier/subscriptions',
                               extra_environ=site_admin_one_env).json_body
        assert_that(res, has_entries({
            "Items": has_length(1)
        }))

        assert_that(res["Items"][0], has_entries({
            "Target": target_one,
            "Id": not_none(),
            "OwnerId": "site.admin.one",
            "CreatedTime": not_none(),
            "Active": True,
            "Status": "Active",
            "href": not_none(),
        }))

        target_two = "https://localhost/handle_new_user_two"
        created_time += 1
        self._create_subscription("user", "created", target_two,
                                  extra_environ=site_admin_two_env,
                                  created_time=created_time,
                                  status_message=u'1')

        res = self.testapp.get(b'/dataserver2/zapier/subscriptions',
                               extra_environ=site_admin_two_env).json_body
        assert_that(res, has_entries({
            "Items": has_length(1)
        }))

        # NTI Admins should see all subscriptions for the site
        res = self.testapp.get(b'/dataserver2/zapier/subscriptions').json_body
        assert_that(res, has_entries({
            "Items": has_length(2)
        }))

        # Create a third subscription to test paging
        created_time += 1
        target_three = "https://localhost/handle_new_user_three"
        self._create_subscription("user", "created", target_three,
                                  created_time=created_time,
                                  status_message=u'2',
                                  active=False)

        # Paging
        #   First page
        subscription_url = b'/dataserver2/zapier/subscriptions'
        res = self.testapp.get(subscription_url,
                               params={'batchSize': '2'}).json_body
        assert_that(res['Total'], is_(3))
        self.require_link_href_with_rel(res, 'batch-next')
        self.forbid_link_with_rel(res, 'batch-prev')

        #   Middle page
        res = self.testapp.get(subscription_url,
                               params={'batchStart': '1', 'batchSize': '1'}).json_body
        assert_that(res['Total'], is_(3))
        self.require_link_href_with_rel(res, 'batch-next')
        self.require_link_href_with_rel(res, 'batch-prev')

        #   Last page
        res = self.testapp.get(subscription_url,
                               params={'batchStart': '1', 'batchSize': '2'}).json_body
        assert_that(res['Total'], is_(3))
        self.forbid_link_with_rel(res, 'batch-next')
        self.require_link_href_with_rel(res, 'batch-prev')

        # Test sorting
        def assert_order(params, expected, key='Target'):
            res_ = self.testapp.get(subscription_url,
                                    params=params).json_body
            assert_that(res_['ItemCount'], is_(len(expected)))
            values = [item[key]
                      for item in res_['Items']]
            assert_that(values, contains(*expected))

        assert_order({},
                     (target_one, target_two, target_three))
        assert_order({'sortOn': 'createdtime'},
                     (target_one, target_two, target_three))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'invalid'},
                     (target_one, target_two, target_three))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'ascending'},
                     (target_one, target_two, target_three))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'descending'},
                     (target_three, target_two, target_one))
        assert_order({'sortOn': 'owner'},
                     (target_three, target_one, target_two))
        assert_order({'sortOn': 'target'},
                     (target_one, target_three, target_two))
        assert_order({'sortOn': 'status'},
                     (target_two, target_three, target_one))
        assert_order({'sortOn': 'active'},
                     (False, True, True),
                     key='Active')

    @WithSharedApplicationMockDS(users=("site.admin.one",
                                        "site.admin.two"),
                                 testapp=True,
                                 default_authenticate=False)
    def test_history(self):
        admin_env = self._make_extra_environ(username=self.default_username)
        site_admin_one_env = self._make_extra_environ(username='site.admin.one')
        site_admin_two_env = self._make_extra_environ(username='site.admin.two')
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            self._make_site_admins('site.admin.one', 'site.admin.two')

        target_url = "https://localhost/handle_new_user"
        res = self._create_subscription("user", "created", target_url,
                                        extra_environ=site_admin_one_env)

        subscription_ntiid = res.json_body['Id']
        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(0))

        usernames = list()
        # Status should be `failed`
        mock_delivery_to(target_url, status=403)
        usernames.append(self._do_create_user(u'user.one', u'User One').json_body['Username'])

        # Ensure we're getting non-duplicated values for `createdTime`
        time.sleep(1)

        # Status should be `successful`
        _clear_mocks()
        mock_delivery_to(target_url, status=200)
        usernames.append(self._do_create_user(u'user.two', u'User Two').json_body['Username'])
        time.sleep(1)

        # Status should be `pending`
        begin_synchronous_delivery()
        usernames.append(self._do_create_user(u'user.three', u'User Three').json_body['Username'])
        time.sleep(1)

        with mock_ds.mock_db_trans(site_name="janux.ou.edu"):
            subscription = find_object_with_ntiid(subscription_ntiid)
            assert_that(subscription, has_length(3))

        # Only admins get history decorated
        self.forbid_link_with_rel(res.json_body, "delivery_history")
        admin_res = self.testapp.get(res.json_body['href'], extra_environ=admin_env)
        history_url = self.require_link_href_with_rel(admin_res.json_body, "delivery_history")

        # Only owner and nti admins can fetch
        self.testapp.get(history_url, extra_environ=site_admin_two_env, status=403)

        #   Owner can fetch, but gets no links for request/response
        res = self.testapp.get(history_url,
                               extra_environ=site_admin_one_env).json_body
        assert_that(res['Items'], has_length(3))
        self.forbid_link_with_rel(res['Items'][0], "delivery_request")
        self.forbid_link_with_rel(res['Items'][0], "delivery_response")

        #   NTI admin can fetch and gets all links
        res = self.testapp.get(history_url, extra_environ=admin_env).json_body
        assert_that(res['Items'], has_length(3))
        self.require_link_href_with_rel(res['Items'][0], "delivery_request")
        self.require_link_href_with_rel(res['Items'][0], "delivery_response")

        assert_that(res["Items"][0], has_entries({
            "status": is_("failed"),
            "message": anything(),
        }))
        assert_that(res["Items"][0], not_(has_key("request")))
        assert_that(res["Items"][0], not_(has_key("response")))

        assert_that(res["Items"][1], has_entries(status='successful'))
        assert_that(res["Items"][2], has_entries(status='pending'))

        # Check search
        res = self.testapp.get(history_url,
                               params={
                                   'search': 'OK'
                               },
                               extra_environ=admin_env).json_body
        assert_that(res['Items'], has_length(1))
        assert_that(res['Items'][0], has_entries(status='successful'))

        # Fetch delivery response
        response_url = self.require_link_href_with_rel(res['Items'][0], 'delivery_response')
        res = self.testapp.get(response_url, extra_environ=admin_env).json_body
        assert_that(res['status_code'], is_(200))

        # Again, only NTI admins and owners can access
        self.testapp.get(response_url, extra_environ=site_admin_two_env, status=403)
        self.testapp.get(response_url, extra_environ=site_admin_one_env)

        def assert_order(params, expected):
            res = self.testapp.get(history_url,
                                   params=params,
                                   extra_environ=admin_env).json_body
            assert_that(len(res['Items']), is_(len(expected)))

            links = [self.require_link_href_with_rel(attempt, 'delivery_request')
                     for attempt in res['Items']]
            requests = [
                self.testapp.get(link,
                                 extra_environ=admin_env).json_body
                for link in links
            ]
            bodies = [request['body'] for request in requests]
            usernames = [json.loads(body)['Data']['Username'] if body else None
                         for body in bodies]
            assert_that(usernames, contains(*expected))

        # Third attempt not sent, body will be `None`
        assert_order({}, (usernames[0], usernames[1], None))
        assert_order({'sortOn': 'createdtime'},
                     (usernames[0], usernames[1], None))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'invalid'},
                     (usernames[0], usernames[1], None))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'ascending'},
                     (usernames[0], usernames[1], None))
        assert_order({'sortOn': 'createdtime', 'sortOrder': 'descending'},
                     (None, usernames[1], usernames[0]))
        assert_order({'sortOn': 'status', 'sortOrder': 'ascending'},
                     (usernames[0], None, usernames[1]))

    def _make_site_admins(self, *users):
        prm = IPrincipalRoleManager(getSite())
        for user in users:
            if IUser.providedBy(user):
                username = user.username
            else:
                username = user
                user = self._get_user(username=user)

            set_user_creation_site(user, getSite())
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN.id, username)

    def _do_create_user(self, username, name):
        path = '/dataserver2/account.create'
        email = u'%s@zaptest.org' % (username,)

        data = {
            'Username': username,
            'realname': name,
            'email': email,
            'password': uuid.uuid4().hex
        }

        extra_env = {"HTTP_ORIGIN": self.default_origin}
        res = self.testapp.post_json(path, data, extra_environ=extra_env)

        # Clear cookies so we're not logged in for subsequent iterations
        self.testapp.reset()

        return res