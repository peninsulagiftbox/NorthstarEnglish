package local.northstar.catalog;

import java.nio.file.*;
import tools.jackson.databind.node.ObjectNode;

final class ImportFixtures {
    static Path copy(Path destination, String name, boolean simulatedReview) throws Exception {
        Path source = Path.of(System.getenv("NORTHSTAR_IMPORT_SAMPLE_ROOT")).resolve(name);
        try (var files = Files.walk(source)) {
            for (Path path : files.toList()) {
                Path target = destination.resolve(source.relativize(path));
                if (Files.isDirectory(path)) Files.createDirectories(target);
                else Files.copy(path, target);
            }
        }
        if (simulatedReview) {
            var content = (ObjectNode) CoreContent.JSON.readTree(Files.readAllBytes(destination.resolve("package.json")));
            var manifest = (ObjectNode) CoreContent.JSON.readTree(Files.readAllBytes(destination.resolve("manifest.json")));
            for (var sourceRecord : content.path("sources"))
                ((ObjectNode) sourceRecord).put("reviewStatus", "confirmed").put("reviewer", "synthetic-contract-fixture-NOT-human-review");
            for (var asset : content.path("audioAssets"))
                ((ObjectNode) asset.path("alignment")).put("status", "verified")
                    .put("reviewer", "synthetic-contract-fixture-NOT-human-listening").put("reviewedAt", "2026-11-05T00:00:00Z");
            ((ObjectNode) manifest.path("proofreading")).put("status", "confirmed").put("revision", 1)
                .put("reviewer", "synthetic-contract-fixture-NOT-human-review").put("reviewedAt", "2026-11-05T00:00:00Z");
            save(destination, content, manifest);
        }
        return destination;
    }
    static void save(Path root, ObjectNode content, ObjectNode manifest) throws Exception {
        byte[] raw = CoreContent.bytes(content);
        manifest.put("rawSha256", ContentPackage.sha256(raw)).put("contentSha256", CoreContent.hash(content));
        Files.write(root.resolve("package.json"), raw);
        Files.write(root.resolve("manifest.json"), CoreContent.bytes(manifest));
    }
    static Path renamed(Path destination, String oldPrefix, String newPrefix, String lesson, int number, boolean noExercises) throws Exception {
        Path temporary = Files.createTempDirectory("northstar-contract-template-");
        copy(temporary, "a", true);
        try (var files = Files.walk(temporary)) {
            for (Path path : files.toList()) {
                Path target = destination.resolve(temporary.relativize(path).toString().replace(oldPrefix, newPrefix));
                if (Files.isDirectory(path)) Files.createDirectories(target);
                else Files.copy(path, target);
            }
        }
        var content = (ObjectNode) CoreContent.JSON.readTree(Files.readString(destination.resolve("package.json")).replace(oldPrefix, newPrefix));
        var manifest = (ObjectNode) CoreContent.JSON.readTree(Files.readString(destination.resolve("manifest.json")).replace(oldPrefix, newPrefix));
        ((ObjectNode) content.path("lesson")).put("id", lesson).put("slug", lesson);
        ((ObjectNode) content.path("version")).put("number", number);
        if (noExercises) {
            content.putArray("exercises");
            content.putArray("exerciseSets");
            content.putArray("knowledge");
        }
        save(destination, content, manifest);
        return destination;
    }
}
