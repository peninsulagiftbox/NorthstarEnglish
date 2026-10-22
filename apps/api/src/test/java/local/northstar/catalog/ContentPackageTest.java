package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.Files;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Path;

class ContentPackageTest {
    @TempDir Path temp;

    @Test void rejectsMissingTraversalTamperedAndSymlinkAudio() throws Exception {
        var content = new ContentPackage(temp.toString());
        assertThrows(IllegalStateException.class, () -> content.checkedAudio("../../etc/passwd", 5, "invalid"));
        assertThrows(java.io.IOException.class, () -> content.checkedAudio("demo-01/v1/audio/01.mp3", 5, "invalid"));
        Path file = temp.resolve("demo-01/v1/audio/01.mp3");
        Files.createDirectories(file.getParent());
        byte[] data = "test audio".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        Files.write(file, data);
        assertEquals(file, content.checkedAudio("demo-01/v1/audio/01.mp3", data.length, ContentPackage.sha256(data)));
        assertThrows(java.io.IOException.class, () -> content.checkedAudio("demo-01/v1/audio/01.mp3", data.length + 1, ContentPackage.sha256(data)));
        assertThrows(java.io.IOException.class, () -> content.checkedAudio("demo-01/v1/audio/01.mp3", data.length, "0".repeat(64)));
        // An existing file outside root must remain inaccessible through a symlink.
        Path outside = temp.resolveSibling(temp.getFileName() + "-outside.mp3");
        try {
            Files.write(outside, data);
            Path link = file.resolveSibling("02.mp3");
            Files.createSymbolicLink(link, outside);
            assertThrows(java.io.IOException.class, () -> content.checkedAudio("demo-01/v1/audio/02.mp3", data.length, ContentPackage.sha256(data)));
        } finally { Files.deleteIfExists(outside); }
    }

    @Test void loadsRealFrozenBundle() throws Exception {
        var bundle = new ContentPackage("../../content").load();
        assertEquals(10, bundle.lesson().path("sentences").size());
        assertFalse(bundle.manifest().path("releaseReady").asBoolean());
        var content = new ContentPackage("../../content");
        assertEquals(java.util.List.of(1,2), content.publishedVersions());
        assertEquals(2, content.activeVersion());
        assertEquals("demo-01-v2", content.load(2).lesson().path("versionId").asText());
        assertTrue(bundle.manifest().path("licenses").valueStream().allMatch(l -> l.path("reviewStatus").asText().equals("pending_review")));
    }
}
