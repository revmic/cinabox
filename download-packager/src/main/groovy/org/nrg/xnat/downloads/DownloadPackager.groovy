package org.nrg.xnat.downloads
/*
 * Copyright (c) 2013. Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 */

import com.twmacinta.util.MD5
import groovy.json.JsonBuilder
import groovy.json.JsonSlurper
import groovy.text.GStringTemplateEngine
import groovy.time.TimeCategory
import groovy.time.TimeDuration
import groovy.util.logging.Log
import org.apache.commons.cli.Option

import java.nio.charset.Charset
import java.nio.file.DirectoryNotEmptyException
import java.nio.file.FileVisitResult
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.SimpleFileVisitor
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.BasicFileAttributes
import java.security.MessageDigest
import java.util.logging.Level

/**
 * Handles creating a download package from a set of Ant-formatted include paths.
 */
@Log
class DownloadPackager {

    public static void main(String[] args) {
        try {
            def packager = new DownloadPackager(args)
            packager.process()
        } catch (DownloadPackagerException exception) {
            if (exception.message) {
                println exception.message
            }
            cli.usage()
        }
    }

    /**
     * Constructor processes download packaging options from command-line formatted String array.
     * @param args Strings in a command-line format.
     */
    def DownloadPackager(String[] args) {
        fixUpTheMetaClasses()

        options = cli.parse(args)

        // Show usage text when -h or --help option is used
        if (!options || options.h) {
            throw new DownloadPackagerException()
        }

        // Show the version information if requested.
        if (options.v) {
            println "Version 1.0"
            throw new DownloadPackagerException()
        }

        if (!options.a || !options.d || !options.o || !options.r) {
            throw new DownloadPackagerException("You must specify values for each of the -a, -d, -o, and -r options!")
        }
    }

    /**
     * Processes the download package based on the configuration set in the constructor.
     */
    public boolean process() throws DownloadPackagerException {
        start = new Date()

        validate()
        buildMigratedFolders()

        ant.fileset(id: "files", dir: scratch.parent.toFile()) {
            include: '**/*'
        }

        createPayloadManifest(findPayload(ant))
        // createBoilerplates()

        ant.zip(destfile: packaged.toFile(), duplicate: "preserve") {
            fileset(refid: "files")
        }

        if (Files.exists(packaged)) {
            success = true
            def size = Files.readAttributes(packaged, BasicFileAttributes.class).size()
            finish = new Date()
            TimeDuration duration = TimeCategory.minus(finish, start)
            message = "Completed archive operation into file ${packaged.toString()}: Wrote ${size} bytes total in ${duration}."
            def md5File = new File("${packaged.toString()}.md5")
            md5File << packaged.toFile().md5()
        } else {
            success = false
            message = "Failed to write file ${packaged.toString()}. Check logs for errors."
        }
        if (log.isLoggable(Level.INFO)) {
            def verb = success ? "succeeded" : "failed"
            log.info("Packaging operation ${verb}: ${message}")
        }
        audit << "Subject: ${subject}, definition: ${options.d}, ${message}\n"
        audit.close()
        success
    }

    private void validate() {
        subject = options.s
        if (!subject) {
            throw new DownloadPackagerException("You must specify a subject ID.")
        }

        if (options.m) {
            options.ms.each { String option ->
                if (option) {
                    def (key, value) = option.split("=")
                    migrations.put((String) key, (String) value)
                    //println "key=" + key
                    //println "value=" + value
                }
            }
        }

        String definitionId = options.d
        if (!definitionId) {
            throw new DownloadPackagerException("You must specify a definition ID.")
        }
        loadDefinition(definitionId)

        Path output = Paths.get(options.o).validateFolder()
        audit = Files.newBufferedWriter(output.resolve("packaging.log"), Charset.defaultCharset(), StandardOpenOption.APPEND, StandardOpenOption.CREATE)
        Path subjectOutput = output.resolve(subject).validateFolder()
        def prefix = getMigrationPrefix()
        def template = definition.outputName ?: "${subject}_${definitionId}_preproc.zip"
        def archiveName = formatTemplate(template, [subject: subject, prefix: prefix, definitionId: definitionId])
        packaged = subjectOutput.resolve(archiveName)

        archiveRoot = Paths.get((String) options.a)
        if (!Files.exists(archiveRoot)) {
            throw new DownloadPackagerException("The archive root $archiveRoot does not exist!")
        }

        if (definition.packageOffset) {
            packageOffset = definition.packageOffset
        }

        // Initialize our scratch space.
        Path working = (options.w ? Paths.get(options.w) : Files.createTempDirectory(Paths.get(System.getProperty('java.io.tmpdir')), "download-packager-"))
        task = working.resolve(stripExtension(archiveName)).validateFolder()

        scratch = task.resolve(subject).validateFolder()

        if (log.isLoggable(Level.CONFIG)) {
            log.config("Creating scratch space in folder: " + scratch.toString())
        }

        if (definition.nestedPath) {
            nestedPath = scratch.resolve((String) definition.nestedPath).validateFolder()
        }

        if (!options.f) {
            Runtime.getRuntime().addShutdownHook(new Thread() {
                public void run() {

                    if (log.isLoggable(Level.CONFIG)) {
                        log.config("Deleting task space folder: " + task.toString())
                    }

                    Files.walkFileTree(task, new SimpleFileVisitor<Path>() {

                        @Override
                        public FileVisitResult visitFile(Path file, BasicFileAttributes attributes) throws IOException {
                            Files.delete(file);
                            return FileVisitResult.CONTINUE;
                        }

                        @Override
                        public FileVisitResult postVisitDirectory(Path dir, IOException exception) throws IOException {
                            if (exception == null) {
                                try {
                                    Files.delete(dir);
                                } catch (DirectoryNotEmptyException thrown) {
                                    System.err.println "Unable to delete task directory: " + thrown.getFile() + "\n *** Reason given: " + thrown.getReason()
                                }
                                return FileVisitResult.CONTINUE;
                            } else {
                                throw exception;
                            }
                        }
                    })
                }
            })
        }
    }

    private void buildMigratedFolders() {
        definition.stems.reverseEach { stem ->
            def root = archiveRoot.resolve(subject ? "${subject}_$stem" : stem)
            if (root && Files.exists(root)) {
                if (migrations.size() > 0) {
                    migrations.each { from, to ->
                        def realized = packageOffset ? Paths.get(root.toString(), formatTemplate(packageOffset, [fMRIName: from])) : root
                        def realized_np = packageOffset ? Paths.get(root.toString(), formatTemplate(packageOffset, [fMRIName: from]).toString().replaceFirst(/_preproc$/,"")) : root
                        if (realized && Files.exists(realized)) {
                            buildMigratedFolder(realized, from, to)
                        } else if (realized && realized.toString().endsWith("_preproc") && Files.exists(realized_np)) {
                            buildMigratedFolder(realized_np, from, to)
                        } 
                    }
                } else {
                    def realized = packageOffset ? Paths.get(root.toString(), packageOffset) : root
                    if (realized && Files.exists(realized)) {
                        buildMigratedFolder(realized)
                    }
                }
            }
        }
    }

    private void buildMigratedFolder(Path source, String... mappings) {
        if (!source || !Files.exists(source)) {
            return
        }
        String from, to
        if (mappings != null && mappings.length > 0) {
            from = mappings[0]
            to = mappings[1]
        } else {
            from = ""
            to = ""
        }
        def pathSpec = resolveDefinition(from)
        def migrator = new AntBuilder()
        migrator.fileset(id: "migrator", dir: source.toFile()) {
            pathSpec.each { path ->
                include(name: path)
            }
        }
        def scanner = migrator.fileScanner {
            fileset(refid: "migrator")
        }
        Path realized = null
        scanner.each { f ->
            assert f instanceof File
            if (log.isLoggable(Level.FINE)) {
                log.fine("Migrating file $f")
            }
            Path original = ((File) f).toPath()
            realized = (nestedPath ?: scratch).resolve(source.relativize(original).toString().replaceAll(from, to))
            realized.parent.validateFolder()
            if (!Files.exists(realized)) {
                if (isWindows) {
                    Files.copy(original, realized)
                } else {
                    Files.createSymbolicLink(realized, original)
                }
            }
        }
    }

    private List findPayload(AntBuilder ant) {
        def files = []
        def scanner = ant.fileScanner {
            fileset(refid: 'files')
        }
        scanner.each { f ->
            assert f instanceof File
            if (log.isLoggable(Level.FINE)) {
                log.fine("Found file $f")
            }
            Path uri = null
            for (Path path : Paths.get(f.toURI())) {
                if (path.toString().equals(subject)) {
                    uri = path
                } else if (uri != null) {
                    uri = uri.resolve(path)
                }
            }
            files.add([Name: "${f.name}", URI: "${uri}", Size: "${f.length()}", Checksum: "${f.md5()}"])
        }
        files
    }

    private Path createPayloadManifest(files) {
        def manifest = new JsonBuilder()
        manifest.DownloadManifest() {
            Subject(subject)
            Version('1.0.20130214')
            Includes(files.collect {
                [Name: it.Name, URI: it.URI, Size: it.Size, Checksum: it.Checksum]
            })
        }
        Path metafolder = scratch.resolve(".xdlm").validateFolder()
        def file = metafolder.resolve(getJsonFileName(packaged.getFileName().toString()))
        def writer = Files.newBufferedWriter(file, Charset.defaultCharset())
        manifest.writeTo(writer)
        writer.close()
        if (log.isLoggable(Level.CONFIG)) {
            log.config("Wrote manifest to ${file.toString()}")
        }
        file
    }

    private def createBoilerplates() {
        def files = []
        boilerplates.each {
            def file = scratch.resolve(it)
            def output = Files.newBufferedWriter(file, Charset.defaultCharset())
            new BufferedReader(new InputStreamReader(getClass().getResourceAsStream("$boilerplatePackage$it"))).readLines().each { output << it }
            output.close()
            if (log.isLoggable(Level.CONFIG)) {
                log.config("Wrote realized definition to ${file.toString()}")
            }
            files.add(file)
        }
        files
    }

    private List<String> resolveDefinition(String value) {
        def pathSpec = []
        definition.paths.each {
            def spec = formatTemplate((String) it, [fMRIName: value])
            if (log.isLoggable(Level.CONFIG)) {
                log.config("Adding to path to definition specification: ${spec}")
            }
            pathSpec.add(spec)
        }
        pathSpec
    }

    private def formatTemplate(final String template, Map variables) {
        def writer = new StringWriter()
        formatter.createTemplate(template).make(variables).writeTo(writer)
        writer.flush()
        writer.toString()
    }

    private void loadDefinition(final String definitionId) {
        def registry = Paths.get(options.r)
        if (!Files.exists(registry)) {
            throw new DownloadPackagerException("The registry folder $registry.toString() does not exist!")
        }

        def definitionFile = registry.resolve("${definitionId}.json")
        if (!definitionFile || !Files.exists(definitionFile)) {
            throw new DownloadPackagerException("The indicated package ${definitionId}.json does not exist in the specified registry folder $registry!")
        }

        if (log.isLoggable(Level.CONFIG)) {
            log.config("Found valid definition file path: " + definitionFile.toAbsolutePath())
        }
        def slurper = new JsonSlurper()
        definition = slurper.parse(Files.newBufferedReader(definitionFile, Charset.defaultCharset())).definition
    }

    private String getMigrationPrefix() {
        String common = null
        if (migrations.size() > 0) {
            migrations.values().each {
                if (!common) {
                    common = it
                } else {
                    common = common.commonPrefix(it)
                }
            }
        }
        common
    }

    /**
     * Returns the filename without an extension.
     * @param filename    The filename to be stripped.
     * @return The filename without extension.
     */
    private static String stripExtension(final String filename) {
        if (!filename.contains('.')) {
            return filename
        }
        def offset = filename.lastIndexOf('.')
        filename.substring(0, offset)
    }

    /**
     * Takes the relative file name, strips the extension, and adds ".json"
     * @param relative    The relative file name (i.e. output file to which this JSON file is related)
     * @return The name of the JSON file to create
     */
    private static String getJsonFileName(final String relative) {
        def stripped = stripExtension(relative)
        "${stripped}.json"
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

        File.metaClass.md5 = {->
            try {
                Class.forName("com.twmacinta.util.MD5")
                MD5.asHex(MD5.getHash((File) delegate))
            } catch (ClassNotFoundException ignored) {
                def digest = MessageDigest.getInstance("MD5")
                delegate.withInputStream() { is ->
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

        String.metaClass.commonPrefix { compare ->
            String a = delegate
            String b = compare
            int minLength = Math.min(a.length(), b.length());
            def tmp = null
            for (int i = 0; i < minLength; i++) {
                if (a.charAt(i) != b.charAt(i)) {
                    tmp = a.substring(0, i);
                    break;
                }
            }
            if (!tmp) {
                tmp = a.substring(0, minLength).trim()
            };
            while (tmp.endsWith('_')|| tmp.endsWith('-')) {
                tmp = tmp.substring(0, tmp.length() - 1)
            }
            tmp
        }
    }

    private static final boolean isWindows = System.getProperty("os.name").toLowerCase().contains("win")

    static final CliBuilder cli = new CliBuilder(usage: 'org.nrg.xnat.downloads.DownloadPackager.groovy -[adefhorv]',
            header: 'Used to create download package from a subset of files in a specified archive path based on a particular package definition file.',
            footer: '(C) 2013 Washington University School of Medicine')

    static {
        // Create the list of options.
        cli.with {
            a longOpt: 'archive-root', args: 1, argName: 'path', 'Specifies the archive root path from which references should be resolved.'
            d longOpt: 'definition', args: 1, argName: 'package-definition', 'Specifies the package definition to be used for building the download package.'
            f longOpt: 'forensics', args: 0, 'Indicates whether the scratch or working space should be left for forensic analysis.'
            h longOpt: 'help', 'Show usage information'
            m longOpt: 'migrate', args: Option.UNLIMITED_VALUES, argName: 'map1=x,map2=y...mapN=...', 'Specifies migration mappings for particular values. This allows us to map a value as it currently exists in the archive to the value to which it should eventually be migrated.', type: String, valueSeparator: ','
            o longOpt: 'output', args: 1, argName: 'folder-spec', 'Indicates the path to the root output folder. The output file will be created in a subfolder with the subject ID.'
            r longOpt: 'registry', args: 1, argName: 'registry-folder', 'Specifies the path from which package definitions can be loaded.'
            s longOpt: 'subject', args: 1, argName: 'subject-id', 'Specifies the subject ID.'
            v longOpt: 'version', 'Display script version information'
            w longOpt: 'working-folder', args: 1, argName: 'folder-spec', 'The folder to use for intermediate scratch space', type: String
        }
    }

    def boilerplatePackage = "/"
    def boilerplates = ["README.md", "README.txt"]

    GStringTemplateEngine formatter = new GStringTemplateEngine()
    Date start, finish
    OptionAccessor options
    AntBuilder ant = new AntBuilder()
    String subject, message, packageOffset
    Map<String, String> migrations = [:]
    Map definition
    Path packaged, archiveRoot, task, scratch, nestedPath
    BufferedWriter audit
    boolean success
}
