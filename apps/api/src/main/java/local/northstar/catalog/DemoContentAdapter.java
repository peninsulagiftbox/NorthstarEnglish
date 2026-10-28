package local.northstar.catalog;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.HexFormat;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

public class DemoContentAdapter {
    private final Path root;
    private final JsonMapper mapper = JsonMapper.builder().build();

    public DemoContentAdapter(String root) {
        this.root = Path.of(root).toAbsolutePath().normalize();
    }

    public record Bundle(JsonNode lesson, JsonNode manifest, String lessonHash, String manifestHash) {}

    public Bundle load() throws IOException { return load(1); }

    public java.util.List<Integer> publishedVersions() throws IOException {
        var list = mapper.readTree(Files.readAllBytes(root.resolve("demo-01/active.json")));
        var versions = new java.util.ArrayList<Integer>();
        for (JsonNode version : list.path("publishedVersions")) {
            int number = version.asInt(); require(number > 0 && number < 100 && !versions.contains(number)); versions.add(number);
        }
        require(versions.contains(list.path("activeVersion").asInt()));
        return versions;
    }
    public int activeVersion() throws IOException { return mapper.readTree(Files.readAllBytes(root.resolve("demo-01/active.json"))).path("activeVersion").asInt(); }

    public Bundle load(int version) throws IOException {
        require(version > 0 && version < 100);
        String folder = "demo-01/v" + version + "/";
        String versionId = "demo-01-v" + version;
        byte[] raw = Files.readAllBytes(root.resolve(folder + "lesson.json"));
        byte[] manifestRaw = Files.readAllBytes(root.resolve(folder + "manifest.json"));
        JsonNode lesson = mapper.readTree(raw), manifest = mapper.readTree(manifestRaw);
        require(sha256(raw).equals(manifest.path("lessonSha256").asText()));
        require(lesson.path("id").asText().equals("demo-01") && lesson.path("versionId").asText().equals(versionId));
        require(manifest.path("lessonId").asText().equals("demo-01") && manifest.path("versionId").asText().equals(versionId));
        require(!lesson.path("releaseReady").asBoolean() && !manifest.path("releaseReady").asBoolean());
        require(lesson.path("sentences").size() == 10 && manifest.path("audioAssets").size() == 10);
        require(lesson.path("version").asInt() == version);
        require(manifest.path("books").size() == 4 && lesson.path("bookId").isNull());
        var ids = new HashSet<String>();
        for (JsonNode book : manifest.path("books")) require(book.path("availability").asText().equals("catalog_only"));
        for (int i = 0; i < 10; i++) {
            JsonNode sentence = lesson.path("sentences").get(i), audio = manifest.path("audioAssets").get(i);
            String key = folder + "audio/%02d.mp3".formatted(i + 1);
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
