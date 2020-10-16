Initial Implementation
======================

.. warning:: FOR INTERNAL DISTRIBUTION ONLY

Useful Links
------------


`Zapier Platform Docs <https://platform.zapier.com/docs/zapier-intro>`_

`Zapier "CLI" Docs <https://platform.zapier.com/cli_docs/docs>`_

`Competitor Zapier Integrations <https://docs.google.com/spreadsheets/d/1oP41XkhHVPUTACdvSf3w_8KxhCnOPVBW1aHooWCgJdw/edit?usp=drive_web&ouid=113921017540674916733>`_


Authentication
--------------

Zapier supports several `authentication
<https://platform.zapier.com/docs/auth>`_ schemes. Unfortunately there
is `some suggestion
<https://platform.zapier.com/docs/auth#how-to-remove-or-change-zapier-integration-authentication-scheme>`_
in the documentation that the authentication scheme used can’t be
changed and it isn’t immediately clear if your zapier integration can
allow multiple options. Furthermore:

  Major versions of integrations—especially if authentication or API
  calls were changed and other breaking changes were added—will
  require users to re-create their Zaps with the new version of your
  integration. In that case, you won’t be able to migrate existing
  users but instead will need to promote the new version and deprecate
  the old one so new users and Zaps will be made with the new
  integration.

`Basic Auth <https://platform.zapier.com/docs/basic>`_ would work out
of the box for us but of course it requires the user providing their
username and password to zapier. This is the least amount of work, but
the least user friendly, and highest risk if there is a breach. They
also provide a `Session Auth
<https://platform.zapier.com/docs/session>`_ scheme geared towards
apis designed for session, cookie, or token auth. For us, I don’t see
the benefit over just going with Basic Auth between the two.

`API Key Auth <https://platform.zapier.com/docs/apikey>`_ allows
taking an API key, or other authentication information, via form and
providing to each call in a query parameter or header. This could be
applicable as we have some concept of bearer tokens for users, but,
Zapier specifically states that users must be able to manage these
keys in our UI. They can’t be obtained via support or other out of app
mechanisms. We might not be that far from that if we are worried about
basic auth.

.. note:: The keys must be obtainable without human intervention ONLY
          if the integration is being published publicly. Because of
          the usage requirements before that can even happen, we can
          probably get a long way with a support request.

`OAuth V2 Auth <https://platform.zapier.com/docs/oauth>`_ would be the
most user friendly scheme to use. It provides a standard oauth2
authorization flow that users are familiar with from services such as
Google, Facebook, etc. We are furthest from this.

For an initial version, let’s rule out OAuth V2 based on the work
required to support that scheme in the platform. That leaves us with
Basic Auth or API Key. Basic Auth is no work for us, but is the least
ideal for the user. We have server support for generating user tokens,
but no application UI. Perhaps that wouldn’t be much work? I think the
choice of going with Basic Auth first would be obvious except that
it’s an extreme pain to change authentication schemes going forward.

Teams
~~~~~

Zapier has a "teams" option that lets credentials ("connected
accounts") be shared amongst any number of people. I'm not sure how
we're doing licensing but that could be a way to sidestep per-seat
deals. Zapier changes $299/mo for teams so the breakeven point is
pretty high and probably not worth it.

But it could be important to remember, especially when it comes to
auditing; it's probably necessary to tag all actions taken through an
incoming API call from Zapier with that fact in logs, etc.

Even having a custom, semi-limited user or role that gets used
wouldn't necessarily be a bad thing for that reason. This all points
towards API keys and away from Basic Auth.

(But again, teams are probably highly unlikely I'm guessing. We should
probably document that for end-users if we do/not do anything that
makes auditing easier/harder.)

Triggers
--------

Triggers are powered by either a webhook subscription or polling an
api. These form the basis for how a workflow (zap) is
started. Triggers support input fields for filters, tags, etc. to
constrain the information that is considered. Zapier specifies no more
than five triggers for an initial integration release.

New User Created
~~~~~~~~~~~~~~~~

`Triggers <https://platform.zapier.com/docs/triggers>`_ when a new
user is created in the site. The shape of the object should be a
representation of the user object including at least the username and
the basic profile information (name, email, etc.).  New Enrollment
Created

Triggers when a user is enrolled in a course. The object should
include a representation of the user object including at least the
username and the basic profile information (name, email, etc.) as well
as a representation of the course the user is enrolled in, and an
identifier for the enrollment record.

This trigger should include an optional filter that allows narrowing
the scope of a trigger to a specific user or a specific course.

New Course Created
~~~~~~~~~~~~~~~~~~

Triggers when a new course is created in the site. The shape of the
object should be a representation of the catalog entry that includes
basic course information.

.. note:: It sounds like we don't want creation like we typically
          think of things, but rather when a course is published /
          becomes available. We should probably defer this trigger as
          that seems tricky to get right given the complication that
          publication isn't one and done. A course/catalog entry could
          move back and forth between visibility states.

Course Completed
~~~~~~~~~~~~~~~~

Triggers when a user has updated progress/completion information in a
course. The output of which should be the enrollment record
information (with progress/completion status).

This trigger should include an optional filter that allows narrowing
the scope of a trigger to a specific user or a specific course.

.. question:: Should we consider making this a more generic progress
              updated event with an optional threshold if you only
              care about completeness. For example hr.com integration
              and IMIS integration care about partial updates, they
              are polling for those currently.

Actions
-------

Create New User
~~~~~~~~~~~~~~~

Creates a new user in the site. Input is the same as our account
creation form minus the password. Output is a representation of the
user object including at least the username and the basic profile
information (name, email, etc.).

.. question:: How would we deal with authentication credentials here?
              Could the user go through the forgot password flow to
              set initial credentials? Would we give them a one time
              use link to set initial credentials? We could consider
              making this an "Invite User" action which effectively
              bypasses that potential issue. Aaron, seemed OK with that.

Enroll User in Course
~~~~~~~~~~~~~~~~~~~~~

Enrolls a given user in a given course.

Input: Username and course identifier

Output: Course enrollment information / identifier?

.. question:: What do we do about scope. that's largely hidden from
              users currently. Perhaps make an optional field
              defaulting to Public (Purchased?) or maybe that default
              becomes a site / course setting?


Searches
--------

`Searches <https://platform.zapier.com/docs/search-create>`_ are a
special type of action used to lookup or find data in the system. They
can optionally be paired with create actions to perform a “create if
not exist” style action. Searches return a list of matches. Zapier
specifies no more than five searches for an initial
integration. Proposed searches for initial version are:

.. _search_user:

Search User
~~~~~~~~~~~

Search for users in NextThought by
username. Expectation here is this is an exact match that returns the
matching user from the site, or empty if there is no match.

**Input**: Username

**Output**: Representation of the User Object including
basic profile information (name, email, etc) and any custom external
identifiers.

.. question:: This would actually be quite a bit more flexible if this
          worked like the existing UserSearch API. That has provision
          for exact matching username IIRC. It might also mean this
          could be used as the backing of a zapier `dynamic dropdown
          <https://platform.zapier.com/docs/input-designer#dropdown>`_.

Search Course
~~~~~~~~~~~~~

Search for CatalogEntry representation in
NextThought based on ID. Expectation here is this is an exact match
that returns the matching user from the site, or empty if there is no
match.

**Input**: NTIID?
**Output**: Representation of the Catalog Entry that includes basic course info (title, provider id, etc).

.. question:: Similar to :ref:`search_user` it would be nice if this could
          become the backing of a `dynamic dropdown
          <https://platform.zapier.com/docs/input-designer#dropdown>`_.

Other Thoughts
--------------

Zapier talks specifically about naming actions/triggers/searches in
ways that map to UI terminology in the application, not technical
terminology. I.e. course vs CatalogEntry or CourseInstance.

Zapier also talks about not returning to much information on the
objects returned to the user. Perhaps we need different externalizers
for these? Those objects become public API.

..  LocalWords:  Zapier zapier integrations Auth apis auth UI OAuth
..  LocalWords:  oauth
