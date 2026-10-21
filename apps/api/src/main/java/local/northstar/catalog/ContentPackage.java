package local.northstar.catalog;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.HexFormat;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@Component
public class ContentPackage {
    private final Path root;
    private final JsonMapper mapper = JsonMapper.builder().build();

    public ContentPackage(@Value("${northstar.content-root:../../content}") String root) {
        this.root = Path.of(root).toAbsolutePath().normalize();
    }

    public record Bundle(JsonNode lesson, JsonNode manifest, String lessonHash, String manifestHash) {}

    public Bundle load() throws IOException {
        byte[] raw = Files.readAllBytes(root.resolve("demo-01/v1/lesson.json"));
        byte[] manifestRaw = Files.readAllBytes(root.resolve("demo-01/v1/manifest.json"));
        JsonNode lesson = mapper.readTree(raw), manifest = mapper.readTree(manifestRaw);
        require(sha256(raw).equals(manifest.path("lessonSha256").asText()));
        require(lesson.path("id").asText().equals("demo-01") && lesson.path("versionId").asText().equals("demo-01-v1"));
        require(manifest.path("lessonId").asText().equals("demo-01") && manifest.path("versionId").asText().equals("demo-01-v1"));
        require(!lesson.path("releaseReady").asBoolean() && !manifest.path("releaseReady").asBoolean());
        require(lesson.path("sentences").size() == 10 && manifest.path("audioAssets").size() == 10);
        require(manifest.path("books").size() == 4 && lesson.path("bookId").isNull());
        var ids = new HashSet<String>();
        for (JsonNode book : manifest.path("books")) require(book.path("availability").asText().equals("catalog_only"));
        for (int i = 0; i < 10; i++) {
            JsonNode sentence = lesson.path("sentences").get(i), audio = manifest.path("audioAssets").get(i);
            String key = "demo-01/v1/audio/%02d.mp3".formatted(i + 1);
            require(ids.add(sentence.path("id").asText()) && ids.add(audio.path("id").asText()));
            require(sentence.path("audioAssetId").asText().equals(audio.path("id").asText()));
            require(sentence.path("sequence").asInt() == i + 1 && sentence.path("startMs").asInt() == 0);
            require(sentence.path("endMs").asInt() == audio.path("durationMs").asInt());
            require(audio.path("storageKey").asText().equals("audio/%02d.mp3".formatted(i + 1)));
            require(audio.path("mimeType").asText().equals("audio/mpeg"));
            checkedAudio(key, audio.path("byteSize").asLong(), audio.path("sha256").asText());
        }
        return new Bundle(lesson, manifest, sha256(raw), sha256(manifestRaw));
    }

    public Path checkedAudio(String key, long size, String expectedHash) throws IOException {
        require(key.matches("demo-01/v[1-9][0-9]*/audio/(0[1-9]|10)\\.mp3"));
        Path path = root.resolve(key).normalize();
        if (!path.startsWith(root) || !Files.isRegularFile(path) || !path.toRealPath().startsWith(root.toRealPath())) {
            throw new IOException("Content audio missing or outside content root");
        }
        byte[] raw = Files.readAllBytes(path);
        if (raw.length != size || !sha256(raw).equals(expectedHash)) throw new IOException("Content audio integrity mismatch");
        return path;
    }

    public static String sha256(byte[] value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value)); }
        catch (java.security.NoSuchAlgorithmException exception) { throw new IllegalStateException(exception); }
    }

    private static void require(boolean condition) {
        if (!condition) throw new IllegalStateException("Content package invalid; published versions must remain immutable");
    }
}
