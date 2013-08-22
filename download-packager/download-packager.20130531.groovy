import org.nrg.xnat.downloads.DownloadPackager
import org.nrg.xnat.downloads.DownloadPackagerException

/*
 * download-packager.groovy
 * Copyright (c) 2013. Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 */

/**
 * download-packager
 *
 * @author rherri01
 * @since 2/6/13 
 */
DownloadPackager packager
try {
    packager = new DownloadPackager(args)
    packager.process()
} catch (DownloadPackagerException exception) {
    if (exception.message) {
        println exception.message
    }
    if (packager) {
        packager.cli.usage()
    }
}
