===========
Zapier API
===========


Auth Verification
=================
Returns the details for the currently authenticated user.

GET ``/dataserver2/zapier/resolve_me``

Response
--------
Return an ``IUserDetails`` instance containing the following info:

``IUserDetails``
    :Class:
    :MimeType:
    :Username:
    :Email:
    :Realname:
    :NonI18NFirstName:
    :NonI18NLastName:
    :CreatedTime:
    :LastLogin:
    :LastSeen:


Subscription Management
=======================

Add Subscription
----------------
POST ``/dataserver2/zapier/subscriptions/user/created``
POST ``/dataserver2/zapier/subscriptions/user/enrolled``
POST ``/dataserver2/zapier/subscriptions/course/created``
POST ``/dataserver2/zapier/subscriptions/course/completed``


Request
~~~~~~~
Create a subscription for the object and event type provided in the url.

Response
~~~~~~~~
Success: ``201 Created``

Returns an ``WebhookSubscription`` object for the newly created subscription.

``WebhookSubscription``
    :EventType:  The event type used to create the subscription.  One of:
        user.create, user.enroll, course.create, course.complete
    :Target:  The url to POST object data to when the trigger fires.
    :OwnerId:  Owner of the subscription.
    :CreatedTime: When the subscription was first created (ISO formatted date).
    :Active:  Whether it's active.
    :Status: Current status of the subscription
    :href:  Location of the subscription.

Will likely need to extend the current subscription to allow storage of
``eventType`` data.  This could, to a limited degree, be derived from the
subscriptions ``for`` and ``when`` data, but we may not want to
expose that, and wouldn't match what was used during creation anyway.

Remove Subscription
-------------------
DELETE <href-of-subscription returned during creation>

Response
~~~~~~~~
Success: ``204 No Content``


Other Operations
----------------
While not strictly necessary for Zapier integration, it would be nice to have
a way to list manageable subscriptions for a site and all it's children.  Does
something like that currently exist, or is that left for the application
using with `nti.webhooks`.


Triggers
========
.. note:: It might be useful to include details of the subscription that
    initiated the trigger in the events sent.  We can probably deduce
    ``eventType``, but the ``href`` of the subscription, for example, might
    also be good to include.

New User Created
----------------
When: ``IPrincipal``, ``IObjectAddedEvent``

Method: POST

Request
~~~~~~~
Sends an ``IUserCreatedEvent`` containing the details of the newly created user:

``IUserCreatedEvent``
    :EventType: ``user.create``
    :Data:  Contains an ``object`` attribute with the ``IUserDetails`` of the
        created user.


New Course Created
------------------
When: ICourseInstance, IObjectAddedEvent
Method: POST

Request
~~~~~~~
Sends an ``ICourseCreatedEvent`` containing the details of the newly created course.

``ICourseCreatedEvent``
    :eventType:  ``course.create``
    :data:  Contains an ``object`` attribute with the ``ICourseDetails`` of the
        created course.

``ICourseDetails``
    :id: NTIID of course instance
    :providerId:
    :title:
    :description:
    :startDate:
    :endDate:


New Enrollment Created
----------------------
When: ``ICourseInstanceEnrollmentRecord``, ``IStoreEnrollmentEvent``

Method: POST

Request
~~~~~~~
Sends an ``IUserEnrolledEvent`` containing the enrollment information.

``IUserEnrolledEvent``
    :eventType: ``user.enroll``
    :data: Contains an ``object`` attribute with the ``ICourseEnrollmentDetails``
        with user and course info.

``ICourseEnrollmentDetails``
    :id:  NTIID of the enrollment record
    :user: The ``IUserDetails`` for the enrolled user.
    :course: The ``ICourseDetails`` for the associated course.
    :scope: Name of the enrollment scope.


Course Completed
----------------
Worth noting here that the course is the object of the event, so any attempt
to get the user will need to extract it from the event.

When: ``ICourseInstance``, ``IUserProgressUpdatedEvent``
or ``ICourseInstance``, ``ICourseCompletedEvent``
Method: POST

Request
~~~~~~~
Sends an ``ICourseCompletedEvent`` containing the completion info:

``ICourseCompletedEvent``
    :eventType: ``course.complete``
    :data: Contains an ``object`` attribute with the ``ICourseCompletionDetails``
        with user and course info.

``ICourseCompletionDetails``
    :user: The ``IUserDetails`` for the enrolled user.
    :course: The ``ICourseDetails`` for the associated course.


Actions
=======

Create New User
---------------
POST ``/dataserver2/zapier/users/``

Create a new user with the given information.  This will send an email to the
newly created user with a link to finish setting up their account.  A
``success`` param is required to use as the base url to provide for this
purpose.  This will need to be a page that submits the ``username`` and ``id``
provided as parameters in the link to the `/dataserver2/logon.reset.passcode`
view.

Request
~~~~~~~
Success: ``201 Created``

:Username:
:Email:
:Realname:

Response
~~~~~~~~
The ``IUserDetails`` corresponding with the newly created user.


Enroll User in Course
---------------------
POST ``/dataserver2/zapier/enrollments``

Request
~~~~~~~

:username:
:courseId:
:scope:

Response
~~~~~~~~
Returns an ``ICourseEnrollmentDetails`` for the new enrollment.


Search
======

Search User
-----------
GET ``/dataserver2/zapier/user_search``

Request
~~~~~~~
Search terms are sent via additional path info after the view, e.g.
`/dataserver2/zapier/user_search/collin`.  Currently limited to 1000 results,
and no paging is performed.

Response
~~~~~~~~
Returns an item list of ``IUserDetails`` objects, e.g.:

.. code-block:: json

    {
        "Items": [
            {
                "Class": "UserDetails",
                "CreatedTime": "2020-08-11T17:02:29Z",
                "Email": "bobby.hagen+atest@nextthought.com",
                "LastLogin": "2020-08-11T17:02:30Z",
                "LastSeen": "2020-08-11T17:02:30Z",
                "MimeType": "application/vnd.nextthought.zapier.userdetails",
                "NonI18NFirstName": "ATest",
                "NonI18NLastName": "Student",
                "Realname": "ATest Student",
                "Username": "atest.student"
            }
        ],
        "Last Modified": 0,
        "href": "/dataserver2/zapier/user_search/atest"
    }


Search Course
-------------
GET ``/dataserver2/zapier/course_search``

Request
~~~~~~~

:filter:  Filter string used to search for matches by title, description,
    provider id and tags
:sortOn:  The key on which to sort.  One of: "title", "startdate", or "enddate"
:sortOrder:  "ascending" or "descending"
:batchStart:  The absolute index of the first entry to return, after sorting.
:batchSize:  The number of items to return in the batch/page.


Response
~~~~~~~~
Returns an item list of ``ICourseDetails`` objects.
