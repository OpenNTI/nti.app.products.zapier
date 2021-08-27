===========
Zapier API
===========


Auth Verification
=================
GET ``/dataserver2/zapier/resolve_me``

Returns the details for the currently authenticated user.

Response
--------
Return a `UserDetails`_ instance containing the following info:

.. _UserDetails:

``UserDetails``
    :Username:  A unique id for the user in the system.
    :Email:  The user's email address linked to the account.
    :Realname:  The users full real name, e.g. John Smith.
    :NonI18NFirstName:  First name of the user's real name, assuming one can be provided.
    :NonI18NLastName:  Last name of the user's real name, assuming one can be provided.
    :CreatedTime:  When the user was first created (ISO formatted date).
    :LastLogin: When the user last logged in to the system.
    :LastSeen:  When the user last interacted with the system.


Subscription Management
=======================

Add Subscription
----------------
| POST ``/dataserver2/zapier/subscriptions/user/created``
| POST ``/dataserver2/zapier/subscriptions/user/enrolled``
| POST ``/dataserver2/zapier/subscriptions/course/created``
| POST ``/dataserver2/zapier/subscriptions/course/progress_updated``

Creates a subscription for the object and event type provided in the url.

Request
~~~~~~~
Requires the following fields in the body of the request:

:target: Target URL to which a ``POST`` request will be sent with the details of
    the event, when triggered (see :ref:`Triggers` for the corresponding event
    type)

Response
~~~~~~~~
Success: ``201 Created``

Returns a `WebhookSubscription`_ object for the newly created subscription.

.. _WebhookSubscription:

``WebhookSubscription``
    :EventType:  The event type used to create the subscription.  One of:
        user.created, user.enrolled, course.created, course.completed
    :Target:  The url to POST object data to when the trigger fires.
    :OwnerId:  Owner of the subscription.
    :CreatedTime: When the subscription was first created (ISO formatted date).
    :Active:  Whether it's active.
    :Status: Current status of the subscription
    :href:  Location of the subscription.

Remove Subscription
-------------------
DELETE `<href-of-subscription returned during creation>`

Response
~~~~~~~~
Success: ``204 No Content``


List Subscriptions
------------------
GET ``/dataserver2/zapier/subscriptions``

List all subscriptions the authenticated user has permission to see for
the current site.  The link is available via a ``GET`` call to the
``subscriptions`` rel off of the ``zapier`` workspace.

Request
~~~~~~~
This is a batch list operation that will take the following parameters:

:batchSize:
    The size of the batch.  Both batchSize and batchStart must be
    specified for paging.Defaults to 30.
:batchStart:
    The starting batch index. Both batchSize and batchStart must be
    specified for paging. Defaults to 0.
:sortOn:
    The case insensitive field to sort on. Options are ``createdtime``,
    ``owner``, ``target``, ``active``, and ``status``.
    The default is by ``createdtime``.
:sortOrder:
    The sort direction. Options are ``ascending`` and
    ``descending``. Sort order is ascending by default.

Response
~~~~~~~~
Returns a list of `WebhookSubscription`_ objects that the user has
permission to see.


Delivery History
----------------
GET ``{subscription_path}/DeliveryHistory``

Return the delivery attempts for the subscription.  The link is available via
the ``delivery_history`` rel off of the subscription.

Request
~~~~~~~
This is a batch list operation that will take the following parameters:

:batchSize:
    The size of the batch.  Both batchSize and batchStart must be
    specified for paging.Defaults to 30.
:batchStart:
    The starting batch index.  Both batchSize and batchStart must be
    specified for paging.Defaults to 0.
:sortOn:
    The case insensitive field to sort on. Options are ``createdtime``
    and ``status``. The default is ``createdtime``.
:sortOrder:
    The sort direction. Options are ``ascending`` and
    ``descending``. Sort order is ascending by default.
:search:
        String to use for searching messages of the delivery attempts.

Response
~~~~~~~~
Returns a list of `DeliveryAttempt`_ objects associated with the
subscription.

.. _DeliveryAttempt:

``DeliveryAttempt``
    :NTIID:  Unique identifier for the object.
    :CreatedTime: When the delivery attempt was made (ISO formatted date).
    :Last Modified: When the delivery attempt was last modified.
    :status: Status of the delivery attempt.  One of ``successful``,
        ``pending``, or ``failed``.
    :message: Explanatory text that may contain error information or simply a
        status code and reason, if a response was received.

Get Delivery Attempt Request
----------------------------
GET ``{delivery_attempt_path}/Request``

Return information on the request sent to the remote host as part of this
delivery attempt. The link is available via the ``delivery_request`` rel
off of the delivery attempt.

Response
~~~~~~~~
Returns the `DeliveryAttemptRequest`_ object associated with the
delivery attempt.

.. _DeliveryAttemptRequest:

``DeliveryAttemptRequest``
    :url: Url used as the target to send the request.
    :method: The HTTP method used to send the request to the target url,
        e.g. ``POST``.
    :headers: Headers supplied in the request.
    :body: The body supplied for the request.
    :CreatedTime: When the request was made (ISO formatted date).
    :Last Modified: When the request was last modified.


Get Delivery Attempt Response
-----------------------------
GET ``{delivery_attempt_path}/Response``

Return information on the response received from the remote host as part
of this delivery attempt. The link is available via the
``delivery_request`` rel off of the delivery attempt.

Response
~~~~~~~~
Returns the `DeliveryAttemptResponse`_ object associated with the
delivery attempt.

.. _DeliveryAttemptResponse:

``DeliveryAttemptResponse``
    :status_code: Status code issued by the server in response to the
        request, e.g. ``403``.
    :reason: Text associated with the status code, e.g. ``Forbidden``.
    :headers: Headers provided in the response from the remote host.
    :content: The decoded body of the response, if any.
    :elapsed: The amount of time it took to send and receive.
    :CreatedTime: When the response was received (ISO formatted date).
    :Last Modified: When the response was last modified.


Triggers
========

New User Created
----------------
`Triggers <https://platform.zapier.com/docs/triggers>`_ when a new
user is created in the site.

:When: ``IUser``, ``IObjectAddedEvent``
:Method: POST

Request
~~~~~~~
Sends a `UserCreatedEvent`_ containing the details of the newly created user:

.. _UserCreatedEvent:

``UserCreatedEvent``
    :EventType: ``user.created``
    :Data:  Contains the `UserDetails`_ of the created user.

Available Zapier Fields
~~~~~~~~~~~~~~~~~~~~~~~
Fields available to subsequent steps in a Zap as a result of the trigger
firing:

    :Username:  A unique id for the user in the system.
    :Email:  The user's email address linked to the account.
    :Realname:  The users full real name, e.g. John Smith.
    :CreatedTime:  When the user was first created (ISO formatted
        date).
    :LastLogin: When the user last logged in to the system.


New Course Created
------------------
`Triggers <https://platform.zapier.com/docs/triggers>`_ when a new
course is created in the site.

:When: ``ICourseInstance``, ``ICourseInstanceAvailableEvent``
:Method: POST

Request
~~~~~~~
Sends a `CourseCreatedEvent`_ containing the details of the newly created course.

.. _CourseCreatedEvent:

``CourseCreatedEvent``
    :EventType:  ``course.created``
    :Data:  Contains the `CourseDetails`_ of the created course.

.. _CourseDetails:

``CourseDetails``
    :Id: NTIID of course instance
    :ProviderId: A unique id for the course, assigned by the provider.
    :Title: A short user-friendly title for the course to show to users.
    :Description: A longer text-only description of the course.
        Optional.
    :StartDate: The date on which the course begins. Optional.
    :EndDate: The date on which the course ends. Optional.

Available Zapier Fields
~~~~~~~~~~~~~~~~~~~~~~~
Fields available to subsequent steps in a Zap as a result of the trigger
firing:

    :Id: A unique id for the course, created by the system.
    :ProviderId: A unique id for the course, assigned by the provider.
    :Title: A short user-friendly title for the course to show to
        users.
    :Description: A longer text-only description of the course.
        Optional.
    :RichDescription: A longer description of the course that can
        contain html markup.  Typically the description populated when
        creating courses from the application.  Optional.
    :StartDate: The date on which the course begins. Optional.
    :EndDate: The date on which the course ends. Optional.
    :CreatedTime:  When the course was first created (ISO formatted
        date).
    :Last Modified: When the course was last modified.


New Enrollment Created
----------------------
`Triggers <https://platform.zapier.com/docs/triggers>`_ when a user is
enrolled in a course.

:When: ``ICourseInstanceEnrollmentRecord``, ``IObjectAddedEvent``
:Method: POST

Request
~~~~~~~
Sends a `UserEnrolledEvent`_ containing the enrollment information.

.. _UserEnrolledEvent:

``UserEnrolledEvent``
    :EventType: ``user.enrolled``
    :Data: Contains the `CourseEnrollmentDetails`_ with user and course info.

.. _CourseEnrollmentDetails:

``CourseEnrollmentDetails``
    :User: The `UserDetails`_ for the enrolled user.
    :Course: The `CourseDetails`_ for the associated course.
    :Scope: One of ``Public``, ``Purchased``, ``ForCredit``,
        ``ForCreditDegree``, or ``ForCreditNonDegree``


Course Progress Updated
-----------------------
`Triggers <https://platform.zapier.com/docs/triggers>`_ when a user
successfully completes a required item for a course, such as an
assignment.

:When: ``ICourseInstance``, ``IUserProgressUpdatedEvent``
:Method: POST

Request
~~~~~~~
Sends a `UserProgressUpdatedEvent`_ containing the completion info:

.. _UserProgressUpdatedEvent:

``UserProgressUpdatedEvent``
    :EventType: ``course.progress_updated``
    :Data: Contains the `ProgressSummary`_ with user and course info.

.. _ProgressSummary:

``ProgressSummary``
    :User: The `UserDetails`_ for the enrolled user.
    :Course: The `CourseDetails`_ for the associated course.
    :Progess: The `ProgressDetails`_ of the user in the course.

.. _ProgressDetails:

``ProgressDetails``
    :AbsoluteProgress: Number of items completed in the course.
    :MaxPossibleProgress: Total completable items in the course.
    :PercentageProgress: Percentage of items completed for the course.

Actions
=======

Create New User
---------------
POST ``/dataserver2/++etc++hostsites/{site-name}/++etc++site/default/authentication/users``

Create a new user with the given information.  This will send an email to the
newly created user with a link to finish setting up their account. The
link for this view is available off the ``zapier`` workspace with a rel
of ``create_user``. The workspace is also available off the user at
``/dataserver2/users/{authenticated_username}/zapier``.

Request
~~~~~~~
Requires the following fields in the body of the request:

:Username: Username for the user to be created.
:Email: Email address for the user to be created.
:Realname: Real name for the user to be created.

Response
~~~~~~~~
Success: ``201 Created``

The body will contain `UserDetails`_ for the newly created user.

Zapier Input Fields
~~~~~~~~~~~~~~~~~~~
All fields are required unless explicitly marked as optional.

:Username: Username for the user to be created.
:Email: Email address for the user to be created.
:Realname: Real name for the user to be created.


Enroll User in Course
---------------------
POST ``/dataserver2/zapier/enrollments``

Enrolls the provided user in the course with given scope, though scope is
optional and will default to ``Public`` if not provided.  The link for the view
is available off the ``zapier`` workspace with a rel of ``enroll_user``.

Request
~~~~~~~
Requires the following fields in the body of the request:

:Username: Username for the user to be enrolled.
:CourseId: ``Id`` of the course to enroll the user in.
:Scope: One of ``Public``, ``Purchased``, ``ForCredit``,
    ``ForCreditDegree``, or ``ForCreditNonDegree``

Response
~~~~~~~~
Success: ``201 Created`` or ``200 OK``

Returns a `CourseEnrollmentDetails`_ for the new enrollment.  If the record is
newly created, a status of ``201 Created`` will be returned.  If the user was
already enrolled, a status of ``200 OK`` will be returned instead.

Search
======

Search User
-----------
GET ``/dataserver2/++etc++hostsites/{site-name}/++etc++site/default/authentication/users``

Search for users by username, real name and alias.
The link for this view is available off the ``zapier`` workspace with a
rel of ``user_search``. The workspace is also available off the user at
``/dataserver2/users/{authenticated_username}/zapier``.

Request
~~~~~~~
Search terms are sent via additional path info after the view, e.g.
`/dataserver2/++etc++hostsites/{site-name}/++etc++site/default/authentication/users/atest`.
Currently limited to 1000 results, and no paging is performed.

Response
~~~~~~~~
Success: ``200 OK``

Returns an item list of `UserDetails`_ objects, e.g.:

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

Zapier Input Fields
~~~~~~~~~~~~~~~~~~~
All fields are required unless explicitly marked as optional.

:Name: String to use in the search for the user.  Only the first match
    is used in later actions, so it may need to be something unique,
    like a username.

Search Course
-------------
GET ``/dataserver2/zapier/Courses``

Search for courses by a course's title, provider id and tags.
The link for this view is available off the ``zapier`` workspace with a
rel of ``user_search``. The workspace is also available off the user at
``/dataserver2/users/{authenticated_username}/zapier``.

Request
~~~~~~~
This is a batch list operation that will take the following parameters,
all optional:

:batchSize:  The number of items to return in the batch/page.  Both
    batchSize and batchStart must be specified for paging.  Default
    is not to page.
:batchStart:  The absolute index of the first entry to return, after
    sorting. Both batchSize and batchStart must be specified for paging.
    Default is not to page.
:sortOn:  The key on which to sort.  One of: ``title``, ``startdate``,
    ``enddate``, ``provideruniqueid``, ``createdtime``,
    ``lastseentime``, or ``enrolled``.  The default is by ``title``,
    then ``startdate``.
:sortOrder:
    The sort direction. Options are ``ascending`` and
    ``descending``. Sort order is ascending by default.
:filter:  Filter string used to search for matches by ``Title``,
    ``ProviderId`` and tags.
:filterOperator:  Either union or intersection if multiple filters
            are supplied

Response
~~~~~~~~
Success: ``200 OK``

Returns an item list of `CourseDetails`_ objects.
