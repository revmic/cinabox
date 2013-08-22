This is the Download Packager class for rolling download packages for the HCP Q2 data release. It's intended to be
driven by a build script that passes all of the required subject IDs and package definitions in. Each execution of the
Download Packager script creates one and only one output file, a Zip file that pulls in the files specified by the
package definition specified for the execution pass.
