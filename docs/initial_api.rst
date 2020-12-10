===========
Zapier API
===========


Auth Verification
=================
Not sure we have an existing call that does what we're after here. I believe logon.ping was suggested, but unfortunately it doesn't return any user data and also doesn't 401 in the case of invalid credentials.  logon.nti.password returns 401 with invalid credientials, but doesn't return user info on success, so we may need to implement our own here and have a view that returns the currently authenticated user.

GET ``/dataserver2/zapier/users/me``

Response
--------
For Zapier, we seem to need a non-empty response here with the user information.
Return an ``IUserDetails`` instance containing the following info:

``IUserDetails``
    :username:
    :email:
    :name:
    :noni18n_firstname:
    :noni18n_lastname:
    :created:
    :last_login:


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

Returns an ``ISubscriptionDetails`` object for the newly created subscription.

``ISubscriptionDetails``
    :event_type:  The event type used to create the subscription.  One of:
        user.create, user.enroll, course.create, course.complete
    :target:  The url to POST object data to when the trigger fires.
    :owner_id:  Owner of the subscription.
    :created: When the subscription was first created (ISO formatted date).
    :active:  Whether it's active.
    :status: Current status of the subscription
    :href:  Location of the subscription.

Will likely need to extend the current subscription to allow storage of
``event_type`` data.  This could, to a limited degree, be derived from the
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
.. note:: It might be useful to include items from the subscription that
    initiated the trigger in the events sent.  We can probably deduce
    ``event_type``, but the ``href`` of the subscription, for example, might
    also be good to include.

New User Created
----------------
When: ``IPrincipal``, ``IObjectAddedEvent``

Method: POST

Request
~~~~~~~
Sends an ``IUserCreatedEvent`` containing the details of the newly created user:

``IUserCreatedEvent``
    :event_type: ``user.create``
    :data:  Contains an ``object`` attribute with the ``IUserDetails`` of the
        created user.


New Course Created
------------------
When: ICourseInstance, IObjectAddedEvent
Method: POST

Request
~~~~~~~
Sends an ``ICourseCreatedEvent`` containing the details of the newly created course.

``ICourseCreatedEvent``
    :event_type:  ``course.create``
    :data:  Contains an ``object`` attribute with the ``ICourseDetails`` of the
        created course.

``ICourseDetails``
    :id: NTIID of course instance
    :provider_id:
    :title:
    :description:
    :start_date:
    :end_date:


New Enrollment Created
----------------------
When: ``ICourseInstanceEnrollmentRecord``, ``IStoreEnrollmentEvent``

Method: POST

Request
~~~~~~~
Sends an ``IUserEnrolledEvent`` containing the enrollment information.

``IUserEnrolledEvent``
    :event_type: ``user.enroll``
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
    :event_type: ``course.complete``
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

If we go the invitation route, do all sites have appropriate templates in place for this?  Going the other way (creating new users without a password) we'll need an updated template for new user creation that provides a link to set their initial password.  If we use the password recovery mechanism currently in place, we may also want to use a different landing page that doesn't say "Reset Password".

Request
~~~~~~~
Success: ``201 Created``

:username:
:email:
:realname:

Response
~~~~~~~~
The ``IUserDetails`` corresponding with the newly created user.


Enroll User in Course
---------------------
POST ``/dataserver2/zapier/enrollments``

Request
~~~~~~~

:username:
:course_id:
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
Our current user search api is limited to 1000 results.  Since I'm sure we
could have sites with many thousands, does allowing paging here cause
performance issues?  Should we continue to limit results in a similar way, or
allow paging, similar to the course search?  Also, should we limit to users
only (vs FL/DFLs)?

:filter:  Filter string used to search for matches by username, alias, and
    real name, depending on site policies.


Response
~~~~~~~~
Returns an item list of ``IUserDetails`` objects.


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
