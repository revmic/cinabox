/*
 * PackageVerifier.groovy
 * Copyright (c) 2013. Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 */

package org.nrg.xnat.downloads

import com.twmacinta.util.MD5
import groovy.json.JsonSlurper
import groovy.time.TimeCategory
import groovy.time.TimeDuration
import groovy.util.logging.Log

import java.nio.charset.Charset
import java.nio.file.DirectoryStream
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.attribute.BasicFileAttributes
import java.security.MessageDigest


/**
 * Takes a single argument of a root folder. From there, the package verifier will walk all subfolders below that root,
 * looking for the XNAT download manager metadata repository folder. From that metadata repository, it will load the
 * JSON for each package, then verify the files against their indicated checksum values.
 *
 * @author rherri01
 * @since 3/7/13 
 */
@Log
class PackageVerifier {
    public static void main(String[] args) {
        try {
            def verifier = new PackageVerifier(args)
            verifier.verify()
        } catch (DownloadPackagerException exception) {
            if (exception.message) {
                println exception.message
            }
            cli.usage()
        }
    }
    /**
     * Constructor processes package verifier options from command-line formatted String array.
     * @param args Strings in a command-line format.
     */
    def PackageVerifier(String[] args) {
        fixUpTheMetaClasses()

        options = cli.parse(args)

        // Show usage text when -h or --help option is used
        if (!options || options.h) {
            throw new DownloadPackagerException()
        }

        // Show the version information if requested.
        if (options.v) {
            throw new DownloadPackagerException("Version 1.0")
        }

        if (!options.d) {
            throw new DownloadPackagerException("You must specify a value for the -d option!")
        }

        root = Paths.get(options.d).validateFolder()
        verbose = options.x
    }

    def verify() {
        if (verbose) {
            println "Using verbose output setting"
        }

        println "Starting verification operation at folder ${root}"

        def start = new Date()
        def subjectCounter = 1
        DirectoryStream<Path> subjects = Files.newDirectoryStream(root, "[0-9][0-9][0-9][0-9][0-9][0-9]")
        for (Path subject : subjects) {
            println "--Subject ${subjectCounter}"
            verifySubject subject
            subjectCounter++
        }
        def finish = new Date()
        TimeDuration duration = TimeCategory.minus(finish, start)
	
        if (errors.size() == 0) {
            println "Complete, all files validated, ${duration} elapsed"
            0
        } else {
            final log = root.resolve("verify-errors-${start}.log")
            def writer = Files.newBufferedWriter(log, Charset.defaultCharset())
            writer.println "Errors found at ${root}"
            println "Complete, ${errors.size()} errors found, ${duration} elapsed, written to ${log.toString()}"
            for (String error : errors) {
                if (verbose) {
                    println " * ${error}"
                }
                writer.println  "* ${error}"
            }
            writer.close()
            1
        }
        // assert verify() == 1
    }

    def verifySubject(final Path path) {
        if (verbose) {
            println "Retrieving package manifests from ${path}"
        }
        DirectoryStream<Path> packages = Files.newDirectoryStream(path.resolve(".xdlm"), "*.json")
        for (Path pkg : packages) {
            verifyPackage pkg
        }
    }

    def verifyPackage(final Path pkg) {
        JsonSlurper slurper = new JsonSlurper()
        def manifest = slurper.parse(Files.newBufferedReader(pkg, Charset.defaultCharset())).DownloadManifest
        println "Verifying packages for subject ${manifest.Subject}"
        for (Map resource : manifest.Includes) {
            final String uri = resource.URI
            final String checksum = resource.Checksum
            final included = root.resolve(uri)
            final Error error = verifyFile included, checksum
            switch (error) {
                case Error.DoesNotExist:
                    errors.add("${included} does not exist")
                    break;
                case Error.FailsChecksum:
                    errors.add("${included} fails checksum")
                    break;
            }
        }
    }

    private Error verifyFile(final Path path, final String checksum) {
        if (Files.notExists(path)) {
            if (verbose) {
                println "File ${path} does not exist!"
            }
            Error.DoesNotExist
        } else {
            def start = new Date()
            def size = path.size()
            if (verbose) {
                println "File: ${path} (${size} bytes)"
            }

            String calculated = path.md5()
            final boolean pass = checksum.equalsIgnoreCase(calculated)
            def finish = new Date()
            TimeDuration duration = TimeCategory.minus(finish, start)
            if (verbose) {
                println " * Indicated:  ${checksum}"
                println " * Calculated: ${calculated} (in ${duration} ms)"
                println " * Verified:   ${pass ? 'Pass' : 'Fail'}"
            }
            pass ? Error.None : Error.FailsChecksum
        }
    }

    private static void fixUpTheMetaClasses() {
        InputStream.metaClass.eachByte = { int len, Closure c ->
            def read
            byte[] buffer = new byte[len]
            while ((read = delegate.read(buffer)) > 0) {
                c(buffer, read)
            }
        }

        InputStream.metaClass.getBytes = { ->
            def bytes = []
            delegate.eachByte { image << it }
            bytes
        }

        Path.metaClass.md5 = {->
            File file = ((Path) delegate).toFile()
            try {
                Class.forName("com.twmacinta.util.MD5")
                MD5.asHex(MD5.getHash(file))
            } catch (ClassNotFoundException ignored) {
                def digest = MessageDigest.getInstance("MD5")
                file.withInputStream() { is ->
                    is.eachByte(8192) { buffer, bytesRead ->
                        digest.update(buffer, 0, bytesRead)
                    }
                }
                new BigInteger(1, digest.digest()).toString(16).padLeft(32, '0')
            }
        }

        Path.metaClass.validateFolder = {->
            Path path = (Path) delegate
            if (!Files.exists(path)) {
                if (!Files.createDirectories(path)) {
                    throw new DownloadPackagerException("The location for the specified path did not exist and could not be created. Please check the specified path including permissions and access rights: " + path.toString())
                }
            } else if (!Files.isDirectory(path)) {
                throw new DownloadPackagerException("The specified path is not a folder: " + path.toString())
            }
            path
        }

        Path.metaClass.size = {->
            Path path = (Path) delegate
            Files.readAttributes(path, BasicFileAttributes.class).size()
        }
    }

    static final CliBuilder cli = new CliBuilder(usage: 'org.nrg.xnat.downloads.PackageVerifier.groovy -[dhvx]',
            header: 'Used to verify the contents of download packages starting at the indicated root folder.',
            footer: '(C) 2013 Washington University School of Medicine')

    static {
        // Create the list of options.
        cli.with {
            d longOpt: 'directory', args: 1, argName: 'package-folder', 'Specifies the root folder containing the download packages to be verified.', type: String
            h longOpt: 'help', 'Show usage information'
            v longOpt: 'version', args: 0, 'Display script version information'
            x longOpt: 'verbose', args: 0, 'Display more info on operations', type: boolean
        }
    }

    private enum Error {
        None,
        DoesNotExist,
        FailsChecksum
    }

    OptionAccessor options
    Path root
    boolean verbose
    List<String> errors = [] as List<String>
}
