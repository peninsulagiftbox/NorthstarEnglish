package local.northstar.catalog;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import local.northstar.common.ApiProblems;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import jakarta.servlet.http.HttpServletRequest;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

@RestController
public class CatalogController {
    private final JdbcOperations jdbc;
    private final ContentPackage content;
    private final JsonMapper mapper = JsonMapper.builder().build();
    public CatalogController(JdbcOperations jdbc, ContentPackage content) { this.jdbc = jdbc; this.content = content; }

    @GetMapping("/api/v1/books")
    public Map<String, Object> books() {
        return Map.of("books", jdbc.queryForList("SELECT id, catalog_key AS catalogKey, sequence_no AS sequence, title, edition_label AS editionLabel, availability, declared_lesson_count AS declaredLessonCount, metadata_source AS metadataSource FROM book ORDER BY sequence_no"),
                "standaloneLessons", lessons());
    }

    @GetMapping("/api/v1/lessons")
    public List<Map<String, Object>> lessons() {
        return jdbc.queryForList("SELECT l.id, l.slug, l.kind, l.availability, l.book_id AS bookId, v.id AS versionId, JSON_UNQUOTE(JSON_EXTRACT(v.payload_json,'$.title')) AS title, v.release_ready AS releaseReady, 'local_test_only' AS usageScope FROM lesson l JOIN lesson_version v ON l.current_version_id = v.id WHERE l.availability = 'available' ORDER BY l.id");
    }

    @GetMapping("/api/v1/lessons/{id}")
    public JsonNode lesson(@PathVariable String id) {
        List<String> payloads = jdbc.queryForList("SELECT v.payload_json FROM lesson l JOIN lesson_version v ON l.current_version_id = v.id WHERE l.id = ? AND l.availability = 'available'", String.class, id);
        if (payloads.isEmpty()) throw new CatalogFailure(HttpStatus.NOT_FOUND, "LESSON_NOT_FOUND", "课程不存在或尚未开放。");
        ObjectNode result = (ObjectNode) mapper.readTree(payloads.getFirst());
        // Standard answers stay in the versioned server package until grading endpoints exist.
        for (JsonNode exercise : result.path("exercises")) {
            ((ObjectNode) exercise).remove(List.of("answerKey", "explanation"));
        }
        var assets = jdbc.queryForList("SELECT a.id, a.license_id AS licenseId, a.source_kind AS sourceKind, a.storage_key AS storageKey, a.mime_type AS mimeType, a.byte_size AS byteSize, a.duration_ms AS durationMs, a.sha256, a.status FROM audio_asset a WHERE a.lesson_version_id = ?", result.path("versionId").asText());
        Map<String, Map<String, Object>> byId = new LinkedHashMap<>();
        for (Map<String, Object> asset : assets) byId.put(asset.get("id").toString(), asset);
        for (JsonNode sentence : result.path("sentences")) {
            var asset = byId.get(sentence.path("audioAssetId").asText());
            if (asset == null) throw missingAudio();
            check(asset);
            var publicAsset = new LinkedHashMap<>(asset);
            publicAsset.remove("storageKey");
            publicAsset.put("uri", "/api/v1/audio/" + asset.get("id"));
            ((ObjectNode) sentence).set("audio", mapper.valueToTree(publicAsset));
        }
        result.set("licenses", mapper.valueToTree(licensesFor(result.path("versionId").asText())));
        return result;
    }

    private List<JsonNode> licensesFor(String versionId) {
        return jdbc.queryForList("SELECT c.details_json FROM content_license c WHERE c.id IN (SELECT license_id FROM lesson_version WHERE id = ? UNION SELECT license_id FROM audio_asset WHERE lesson_version_id = ?) ORDER BY c.id", String.class, versionId, versionId)
                .stream().map(mapper::readTree).toList();
    }

    @GetMapping("/api/v1/licenses/{id}")
    public JsonNode license(@PathVariable String id) {
        var values = jdbc.queryForList("SELECT details_json FROM content_license WHERE id = ?", String.class, id);
        if (values.isEmpty()) throw new CatalogFailure(HttpStatus.NOT_FOUND, "LICENSE_NOT_FOUND", "来源记录不存在。");
        return mapper.readTree(values.getFirst());
    }

    @GetMapping("/api/v1/audio/{id}")
    public ResponseEntity<FileSystemResource> audio(@PathVariable String id) {
        var values = jdbc.queryForList("SELECT storage_key AS storageKey, byte_size AS byteSize, sha256, status FROM audio_asset WHERE id = ?", id);
        if (values.isEmpty()) throw new CatalogFailure(HttpStatus.NOT_FOUND, "AUDIO_NOT_FOUND", "音频资源不存在。");
        var path = check(values.getFirst());
        // Spring MVC serves Resource byte ranges, including suffix ranges and 416.
        return ResponseEntity.ok().contentType(MediaType.parseMediaType("audio/mpeg"))
                .header("Accept-Ranges", "bytes").body(new FileSystemResource(path));
    }

    private java.nio.file.Path check(Map<String, Object> asset) {
        if (!"ready".equals(asset.get("status"))) throw missingAudio();
        try { return content.checkedAudio(asset.get("storageKey").toString(), ((Number) asset.get("byteSize")).longValue(), asset.get("sha256").toString()); }
        catch (IOException | IllegalStateException exception) { throw missingAudio(); }
    }

    private static CatalogFailure missingAudio() {
        return new CatalogFailure(HttpStatus.SERVICE_UNAVAILABLE, "AUDIO_UNAVAILABLE", "本地音频缺失或校验失败，请恢复对应版本内容包。");
    }

    @ExceptionHandler(CatalogFailure.class)
    public org.springframework.http.ProblemDetail failure(CatalogFailure error, HttpServletRequest request) {
        return ApiProblems.problem(error.status, error.code, error.getMessage(), request.getRequestURI());
    }

    static class CatalogFailure extends RuntimeException {
        final HttpStatus status;
        final String code;
        CatalogFailure(HttpStatus status, String code, String detail) { super(detail); this.status = status; this.code = code; }
    }
}
