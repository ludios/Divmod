
Purpose
=======

Combinator is a convenience utility for developers working on a large number of
Python projects simultaneously (like me).  The goal is that you can use
Combinator to easily set up a large number of projects on both Linux and
Windows environments.


Usage
=====

On UNIX, put this into your shell's startup file (currently only bash and zsh
are supported, patches for other shells accepted):

    eval `python .../your/projects/Divmod/trunk/Combinator/environment.py`


On Windows, path setup is less straighforward so Combinator is mainly concerned
with setting up your sys.path.  You can use it by setting your PYTHONPATH
environment variable to point to:
    .../your/projects/Divmod/trunk/Combinator/environment.py

It can then generate a batch file for you; in a cmd.exe shell, you can type
something like:

    C:\> python Y:\Divmod\trunk\Combinator\environment.py > paths.bat
    C:\> paths

to set both %PYTHONPATH% and %PATH% environment variables.  This will only
affect one shell, however.

To integrate with development tools such as Pythonwin, you will need to
(instead of running the previous commands) set your PYTHONPATH to point to
...\Divmod\trunk\Combinator\
