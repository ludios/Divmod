# -*- test-case-name: xmantissa.test.test_websession -*-

# Copyright 2005 Divmod, Inc.  See LICENSE file for details

"""Sessions that persist in the database.

Every SESSION_CLEAN_FREQUENCY seconds, a pass is made over all persistant
sessions, and those that are more than PERSISTENT_SESSION_LIFETIME seconds old
are deleted. Transient sessions die after TRANSIENT_SESSION_LIFETIME seconds.

These three globals can be overridden by passing appropriate values to the
PersistentSessionWrapper constructor: sessionCleanFrequency, persistentSessionLifetime,
and transientSessionLifetime.
"""

from twisted.cred import credentials

from epsilon import extime

from axiom import attributes, item, userbase

from nevow import guard


SESSION_CLEAN_FREQUENCY = 60 * 60 * 25  # 1 day, almost
PERSISTENT_SESSION_LIFETIME = 60 * 60 * 24 * 7 * 2 # 2 weeks
TRANSIENT_SESSION_LIFETIME = 60 * 12 + 32 # 12 minutes, 32 seconds.


def usernameFromRequest(request):
    """
    Take a HTTP request and return a username of the form <user>@<domain>.

    @type request: L{inevow.IRequest}
    @param request: A HTTP request

    @return: A C{str}
    """
    username = request.args.get('username', [''])[0]
    if '@' not in username:
        username = '%s@%s' % (username, request.getHeader('host').split(':')[0])
    return username



class PersistentSession(item.Item):
    """A session that persists on the database.

    These sessions should not store any state, but are used only to determine
    that the user has previously authenticated and should be given a transient
    session (a regular guard session, not database persistant) without
    providing credentials again.
    """
    typeName = 'persistent_session'
    schemaVersion = 1

    sessionKey = attributes.bytes()
    lastUsed = attributes.timestamp()

    authenticatedAs = attributes.bytes() # The username and domain
                                         # that this session was
                                         # authenticated as.

    def __init__(self, **kw):
        assert kw.get('sessionKey') is not None, "None cookie propogated to PersistentSession"
        kw['lastUsed'] = extime.Time()
        super(PersistentSession, self).__init__(**kw)

    def __repr__(self):
        return "PersistentSession(%r)" % (self.sessionKey, )

    def renew(self):
        """Renew the lifetime of this object.

        Call this when the user logs in so this session does not expire.
        """
        self.lastUsed = extime.Time()


class DBPassthrough(object):
    """A dictionaryish thing that manages sessions and interfaces with guard.

    This is set as the sessions attribute on a nevow.guard.SessionWrapper
    instance, or in this case, a subclass. Guard uses a vanilla dict by
    default; here we pretend to be a dict and introduce presistant-session
    behaviour.
    """
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self._transientSessions = {}

    def __contains__(self, key):
        # we use __get__ here so that transient sessions are always created.
        # Otherwise, sometimes guard will call __contains__ and assume the
        # transient session is there, without creating it.
        try:
            self[key]
        except KeyError:
            return False
        return True

    has_key = __contains__

    def __getitem__(self, key):
        if key is None:
            raise KeyError("None is not a valid session key")
        try:
            return self._transientSessions[key]
        except KeyError:
            if self.wrapper.authenticatedUserForKey(key):
                session = self.wrapper.sessionFactory(self.wrapper, key)
                self._transientSessions[key] = session
                session.setLifetime(self.wrapper.sessionLifetime) # screw you guard!
                session.checkExpired()
                return session
            raise

    def __setitem__(self, key, value):
        self._transientSessions[key] = value

    def __delitem__(self, key):
        del self._transientSessions[key]

    def __repr__(self):
        return 'DBPassthrough at %i; %r, with embelishments' % (id(self), self._transientSessions)


class PersistentSessionWrapper(guard.SessionWrapper):
    """
    Extends nevow.guard.SessionWrapper to reauthenticate previously
    authenticated users.

    There are 4 possible states:
    1) new user, no persistent session, no transient session
    2) anonymous user, no persistent session, transient session
    3) returning user, persistent session, no transient session
    4) active user, persistent session, transient session

    Guard will look it the sessions dict, and if it finds a key
    matching a cookie sent by the client, will return the value as the
    session. However, if a user has a persistent session cookie, but
    no transient session, one is created here.
    """
    def __init__(
        self,
        store,
        portal,
        transientSessionLifetime=TRANSIENT_SESSION_LIFETIME,
        persistentSessionLifetime=PERSISTENT_SESSION_LIFETIME,
        sessionCleanFrequency=SESSION_CLEAN_FREQUENCY,
        **kw):
        """Initialize the PersistentSessionWrapper
        """
        guard.SessionWrapper.__init__(self, portal, **kw)
        self.store = store
        self.sessions = DBPassthrough(self)
        self.cookieKey = 'divmod-user-cookie'
        self.sessionLifetime = transientSessionLifetime
        self.persistentSessionLifetime = persistentSessionLifetime
        self.sessionCleanFrequency = sessionCleanFrequency


    def createSessionForKey(self, key, user):
        PersistentSession(
            store=self.store,
            sessionKey=key,
            authenticatedAs=user)


    def authenticatedUserForKey(self, key):
        for session in self.store.query(PersistentSession, PersistentSession.sessionKey == key):
            session.renew()
            return session.authenticatedAs
        return None


    def removeSessionWithKey(self, key):
        for session in self.store.query(PersistentSession, PersistentSession.sessionKey == key):
            session.deleteFromStore()
            break
        # if the session doesn't exist, we ignore that fact here.


    def savorSessionCookie(self, request):
        """Make the session cookie last as long as the persistant session."""
        cookieValue = request.getSession().uid
        request.addCookie(self.cookieKey, cookieValue, path='/', max_age=PERSISTENT_SESSION_LIFETIME)


    def login(self, request, session, creds, segments):
        """Called to check the credentials of a user.

        Here we extend guard's implementation to preauthenticate users
        if they have a valid persistant session.
        """
        if isinstance(creds, credentials.Anonymous):
            preauth = self.authenticatedUserForKey(session.uid)
            if preauth is not None:
                self.savorSessionCookie(request)
                creds = userbase.Preauthenticated(preauth)

        def cbLoginSuccess(input):
            """User authenticated successfully.

            Create the persistent session, and associate it with the
            username. (XXX it doesn't work like this now)
            """

            user = request.args.get('username')
            if user is not None:
                # create a database session and associate it with this user
                cookieValue = session.uid
                if request.args.get('rememberMe'):
                    self.createSessionForKey(cookieValue, creds.username)
                    self.savorSessionCookie(request)
            return input

        return guard.SessionWrapper.login(self, request, session, creds, segments
                                          ).addCallback(cbLoginSuccess)


    def explicitLogout(self, session):
        """
        Here we override guard's behaviour for the logout action to
        delete the persistent session. In this case the user has
        explicitly requested a logout, so the persistent session must
        be deleted to require the user to log in on the next request.
        """
        guard.SessionWrapper.explicitLogout(self, session)
        self.removeSessionWithKey(session.uid)


    def getCredentials(self, request):
        """
        Override SessionWrapper.getCredentials to add the Host: header
        to the credentials.  This will make web-based virtual hosting
        work.
        """
        username = usernameFromRequest(request)
        password = request.args.get('password', [''])[0]
        return credentials.UsernamePassword(username, password)
