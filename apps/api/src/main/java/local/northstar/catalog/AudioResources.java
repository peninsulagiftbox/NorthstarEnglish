package local.northstar.catalog;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Only database-listed assets enter here. Never derive a key from a public URL. */
final class AudioResources {
    private final Path root;
    AudioResources(Path root) { this.root = root.toAbsolutePath().normalize(); }

    Path checked(String key, long size, String hash) throws IOException {
        if (key == null || !key.matches("[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
                || java.util.Arrays.stream(key.split("/", -1)).anyMatch(p -> p.isEmpty() || p.equals(".") || p.equals(".."))) {
            throw new IllegalStateException("Invalid content resource key");
        }
        Path path = root.resolve(key).normalize();
        if (!path.startsWith(root) || !Files.isRegularFile(path) || !path.toRealPath().startsWith(root.toRealPath())
                || size <= 0 || Files.size(path) != size || hash == null || !hash.matches("[a-f0-9]{64}")) {
            throw new IOException("Content audio missing or outside allowed directory");
        }
        try {
            var digest = MessageDigest.getInstance("SHA-256");
            try (var stream = Files.newInputStream(path)) {
                byte[] buffer = new byte[8192];
                for (int n; (n = stream.read(buffer)) != -1;) digest.update(buffer, 0, n);
            }
            if (!HexFormat.of().formatHex(digest.digest()).equals(hash)) throw new IOException("Content audio integrity mismatch");
        } catch (NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
        return path;
    }
}
