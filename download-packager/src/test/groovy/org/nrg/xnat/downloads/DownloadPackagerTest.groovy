/**
 * DownloadPackagerTest
 * (C) 2012 Washington University School of Medicine
 * All Rights Reserved
 *
 * Released under the Simplified BSD License
 *
 * Created on 12/28/12 by rherri01
 */
package org.nrg.xnat.downloads

import org.junit.Rule
import org.junit.Test
import org.junit.experimental.theories.DataPoint
import org.junit.experimental.theories.Theories
import org.junit.experimental.theories.Theory
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith

import static org.junit.Assert.assertTrue

@RunWith(Theories.class)
class DownloadPackagerTest  {
    @Rule
    public TemporaryFolder testFolder = new TemporaryFolder();
    @DataPoint public static String[] diffusion = ["diffusion"]
    @DataPoint public static String[] functional = ["functional", "fMRIName:BOLD_GAMBLING1_RL"]
    @DataPoint public static String[] structural = ["structural"]

    /**
     * Specifies some invalid options. Expects a {@link DownloadPackagerException}.
     */
    @Test // (expected = DownloadPackagerException.class)
    void testMissingMandatoryOptions() {
//        String[] args = [ "-a", "D:/Tmp/packaging/archive/HCP_Phase2/arc001/100307_diff/RESOURCES/Diffusion", "-d", "D:/Code/Projects/1.6dev/download-packager/target/100307.zip", "-p", "structural", "-r", "D:/Code/Projects/1.6dev/download-packager/resources" ]
//        def packager = new DownloadPackager(args)
//        packager.process()
    }

    @Theory
    void testPackaging(String[] definition) {
//        def archiveRoot = new File(getClass().getResource("/data/aggregate").toURI()).getAbsolutePath()
//        def output = new File(testFolder.getRoot(), "diffusion.zip").getAbsolutePath()
//        def registry = new File(getClass().getResource("/data/packages").toURI()).getAbsolutePath()
//        String[] args = definition.length == 1 ?
//            [ "-a", archiveRoot, "-d", definition[0], "-o", output, "-r", registry ] :
//            [ "-a", archiveRoot, "-d", definition[0], "-e", definition[1], "-o", output, "-r", registry ]
//        def packager = new DownloadPackager(args)
//        packager.process()
//        assertTrue(packager.success)
//        assertTrue(packager.completed.exists())
    }
}
