===========
Zapier API
===========


Auth Verification
=================
Not sure we have an existing call that does what we're after here. I believe logon.ping was suggested, but unfortunately it doesn't return any user data and also doesn't 401 in the case of invalid credentials.  logon.nti.password returns 401 with invalid credientials, but doesn't return user info on success, so we may need to implement our own here and have a view that returns the currently authenticated user.

GET ``/dataserver2/api/zapier/users/me``

Response
--------
For Zapier, we seem to need a non-empty response here with the user information.
Return an ``IUserDetails`` instance containing the following info:

:username:
:email:
:name:
:created:
:last_login:


Subscription Management
=======================

Add Subscription
----------------
POST ``/dataserver2/api/zapier/subscriptions/``


Request
~~~~~~~

:event: One of: user.create, user.enroll, course.create, course.complete
:target: The url to POST object data to when the trigger fires.
:user_filter: Used for user.enroll or course.complete. Specifies a username
    to which the subscription should be restricted.
:course_filter: Used for user.enroll or course.complete. Specifies a course id (ntiid)
    to which the subscription should be restricted.

TODO: How would one hook into the subscription firing mechanisms to allow
filtering?  Would this be an extension of the current subscription implementation
and override of the ``__call__`` method?

Response
~~~~~~~~
Success: ``201 Created``

Returns an ``ISubscriptionDetails`` object, containing the following:

:event:  The event type used to create the subscription.
:target:  The url to POST object data to when the trigger fires.
:owner:  Owner of the subscription.
:created: When the subscription was first created (ISO formatted date).
:active:  Whether it's active.

Will likely need to extend the current subscription to allow storage of
``event`` data.  This could, to a limited degree, be derived from the
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

New User Created
----------------
When: ``IPrincipal``, ``IObjectAddedEvent``
Method: POST

Request
~~~~~~~
Sends the ``IUserDetails`` corresponding with the newly created user.


New Enrollment Created
----------------------
When: ``ICourseInstanceEnrollmentRecord``, ``IStoreEnrollmentEvent``
Method: POST

Request
~~~~~~~
Sends an ``ICourseEnrollmentDetails`` containing the user and course information:

:id:  NTIID? of the enrollment record?
:user: The ``IUserDetails`` for the enrolled user.
:course: The ``ICourseDetails`` for the associated course.
:scope: Name of the enrollment scope.

The ``ICourseDetails`` would contain the following information from the
course instance:

:id: NTIID?
:provider_id:
:title:
:start_date:
:end_date:


New Course Created
------------------
When: ICourseInstance, IObjectAddedEvent
Method: POST

Request
~~~~~~~
``ICourseDetails`` for the created course.


Course Completed
----------------
Worth noting here that the course is the object of the event, so any attempt
to get the user will need to extract it from the event.

When: ``ICourseInstance``, ``IUserProgressUpdatedEvent``
or ``ICourseInstance``, ``ICourseCompletedEvent``
Method: POST

Request
~~~~~~~
Sends an ``ICourseCompletionNotification``:

:user: The ``IUserDetails`` for the enrolled user.
:course: The ``ICourseDetails`` for the associated course.


Actions
=======

Create New User
---------------
POST ``/dataserver2/api/zapier/users/``

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
POST ``/dataserver2/api/zapier/users/<username>/enrollments``

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
TODO

Search Course
-------------
TODO