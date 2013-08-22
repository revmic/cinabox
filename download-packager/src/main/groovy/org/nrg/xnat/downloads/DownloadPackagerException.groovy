/**
 * DownloadPackagerException
 * (C) 2013 Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 *
 * Created on 1/3/13 by rherri01
 */
package org.nrg.xnat.downloads

class DownloadPackagerException extends Exception {
    DownloadPackagerException() {
        super()
    }
    DownloadPackagerException(String message) {
        super(message)
    }
}
