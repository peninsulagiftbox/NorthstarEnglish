package local.northstar.catalog;

import java.io.IOException;
import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Compatibility facade: frozen Demo validation is separate from generic asset access. */
@Component
public class ContentPackage {
    private final DemoContentAdapter demo;
    private final AudioResources audio;
    public ContentPackage(@Value("${northstar.content-root:../../content}") String root) {
        demo = new DemoContentAdapter(root);
        audio = new AudioResources(Path.of(root));
    }
    public record Bundle(tools.jackson.databind.JsonNode lesson, tools.jackson.databind.JsonNode manifest, String lessonHash, String manifestHash) {}
    public Bundle load() throws IOException { return load(1); }
    public Bundle load(int number) throws IOException {
        var bundle = demo.load(number);
        return new Bundle(bundle.lesson(), bundle.manifest(), bundle.lessonHash(), bundle.manifestHash());
    }
    public java.util.List<Integer> publishedVersions() throws IOException { return demo.publishedVersions(); }
    public int activeVersion() throws IOException { return demo.activeVersion(); }
    public Path checkedAudio(String key, long size, String hash) throws IOException { return audio.checked(key, size, hash); }
    public long checkedDuration(String key, long size, String hash) throws IOException { return AudioProbe.duration(audio.checked(key,size,hash),hash); }
    public static String sha256(byte[] value) { return DemoContentAdapter.sha256(value); }
}
