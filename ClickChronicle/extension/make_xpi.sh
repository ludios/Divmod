#!/bin/sh
# i am bad at shell scripts, and "zip" is the worst command ever, just read
# the man page.  great examples like "zip foo foo"

base=$HOME/Projects/Divmod

if ! test -d $base
then
	echo "no directory $base, exiting"
	exit 1
fi

if test -d $base/trunk
then
	base=$base/trunk
fi

extension_dir=$base/ClickChronicle/extension
if ! test -d $extension_dir
then
	echo "no directory $extension_dir, exiting"
	exit
fi

cd $extension_dir/chrome/
mkdir /tmp/chrome
zip /tmp/chrome/content.jar -r content -x '*.svn*' > /dev/null
cd /tmp
zip -r clickchronicle.xpi chrome >/dev/null
zip clickchronicle.xpi -j $extension_dir/install.rdf >/dev/null
mv /tmp/clickchronicle.xpi $HOME
rm -rf /tmp/chrome 
echo "wrote $HOME/clickchronicle.xpi.  open it in firefox to install"




