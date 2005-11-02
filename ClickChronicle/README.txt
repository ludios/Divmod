Running
=======

Create a ClickChronicle-enabled database using the axiomatic command line tool:

    % axiomatic -d cc.axiom click-chronicle-site install
    ClickChronicle/axiom/plugins/clickcmd.py:67: DeprecationWarning: Set either
        sessioned or sessionless on 'TicketBooth'!  Falling back to deprecated
        providedBy() behavior
      booth.installOn(s)
    ClickChronicle/axiom/plugins/clickcmd.py:83: DeprecationWarning: Set either
        sessioned or sessionless on 'FreeTicketSignup'!  Falling back to
        deprecated providedBy() behavior
      ticketSignup.installOn(s)
    %

Optionally, configure a port number to use for HTTP:

    % axiomatic -d cc.axiom web --port 8080
    %

Start the database, either with daemonization:

    % axiomatic -d cc.axiom start
    %

Or without:

    % axiomatic -d cc.axiom start -n
    2005/11/02 17:46 EST [-] Log opened.
    2005/11/02 17:46 EST [-] twistd SVN-Trunk (/usr/bin/python 2.4.2) starting up
    2005/11/02 17:46 EST [-] reactor class: twisted.internet.selectreactor.SelectReactor
    2005/11/02 17:46 EST [-] xmantissa.website.AxiomSite starting on 8080
    2005/11/02 17:46 EST [-] Starting factory <xmantissa.website.AxiomSite instance at 0xb6f679ac>
    2005/11/02 17:46 EST [-] <Scheduler> ran 0 events
