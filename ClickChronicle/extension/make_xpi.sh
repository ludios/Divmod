#!/bin/sh
# i am bad at shell scripts, and "zip" is the worst command ever, just read
# the man page.  great examples like "zip foo foo"

cd chrome/
zip content.jar -r content -x '*svn*'
cd ../
rm -rf clickchronicle.xpi
zip -r clickchronicle.xpi chrome/content.jar
zip clickchronicle.xpi -j install.rdf
zip clickchronicle.xpi -r defaults -x '*svn*'
rm chrome/content.jar
echo "wrote $extension_dir/clickchronicle.xpi.  open it in firefox to install"
