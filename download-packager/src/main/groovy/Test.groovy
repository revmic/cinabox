/*
 * Test.groovy
 * Copyright (c) 2043. Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 */

/**
 * Test
 *
 * @author rherri04
 * @since 4/3/43
 */

import groovy.json.JsonBuilder

import java.security.MessageDigest

InputStream.metaClass.eachByte = { int len, Closure c ->
    def read
    byte[] buffer = new byte[len]
    while ((read = delegate.read(buffer)) > 0) {
        c(buffer, read)
    }
}

File.metaClass.md5 = {->
    def digest = MessageDigest.getInstance("MD5")
    delegate.withInputStream() { is ->
        is.eachByte(8192) { buffer, bytesRead ->
            digest.update(buffer, 0, bytesRead)
        }
    }
    new BigInteger(1, digest.digest()).toString(16).padLeft(32, '0')
}

def ant = new AntBuilder()

ant.fileset(id: "core", dir: "src/test") {
    include(name:"**/*.groovy")
}
// lets create a scanner of filesets
def files = []
def scanner = ant.fileScanner {
    fileset(refid: "core")
}
scanner.each { f ->
    println("Found file $f")
    assert f instanceof File
    assert f.name.endsWith(".groovy")
    files.add([Name: "${f.name}", URI: "${f.toURI()}", Size: "${f.length()}", Checksum: "${f.md5()}"])
}

def manifest = new JsonBuilder()
manifest.DownloadManifest() {
    Version('1.0.20130214')
    Files(files.collect {
        [Name: it.Name, URI: it.URI, Size: it.Size, Checksum: it.Checksum]
    })
}

def file = File.createTempFile("manifest", ".json")
def writer = new FileWriter(file)
manifest.writeTo(writer)
writer.close()
println "Everything persisted to ${file.absolutePath}"

ant.fileset(id: "manifest", dir: file.parent) {
    include(name: file.name)
}

def filesets = ["core", "manifest"]
def result = ant.zip(destfile: "src/test/test.zip") {
    filesets.each { fileset(refid: it) }
}

println "File completed and stred at ${result.destFile}, stored a total of ${result.destFile.length()} bytes"


