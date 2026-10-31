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
import org.springframework.web.bind.annotation.RequestParam;
import jakarta.servlet.http.HttpServletRequest;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

@RestController
public class CatalogController {
    private final JdbcOperations jdbc;
    private final ContentPackage content;
    private final CatalogReader reader;
    private final JsonMapper mapper = JsonMapper.builder().build();
    public CatalogController(JdbcOperations jdbc, ContentPackage content, CatalogReader reader) { this.jdbc = jdbc; this.content = content; this.reader = reader; }

    @GetMapping("/api/v1/books")
    public Map<String, Object> books() { return reader.books(); }

    @GetMapping("/api/v1/lessons")
    public List<Map<String, Object>> lessons() { return reader.lessons(); }

    @GetMapping("/api/v1/books/{id}/lessons")
    public Map<String, Object> bookLessons(@PathVariable String id, @RequestParam(required=false) String cursor,
            @RequestParam(defaultValue="20") int limit) { return reader.bookLessons(id, cursor, limit); }

    @GetMapping("/api/v1/lessons/{id}/versions")
    public Map<String, Object> versions(@PathVariable String id,@RequestParam(required=false) String fromVersion,@RequestParam(required=false) String fromSentence) { return reader.versions(id,fromVersion,fromSentence); }

    @GetMapping("/api/v1/lessons/{id}")
    public JsonNode lesson(@PathVariable String id, @RequestParam(required=false) String versionId) {
        ObjectNode result = reader.lesson(id, versionId);
        var assets = jdbc.queryForList("SELECT a.id, a.license_id AS licenseId, a.source_kind AS sourceKind, a.storage_key AS storageKey, a.mime_type AS mimeType, a.byte_size AS byteSize, a.duration_ms AS durationMs, a.sha256, a.status FROM audio_asset a WHERE a.lesson_version_id = ? AND (a.lesson_version_id IN (SELECT id FROM lesson_version WHERE lesson_id='demo-01') OR a.license_id IN (SELECT id FROM content_license WHERE review_status='confirmed'))", result.path("versionId").asText());
        Map<String, Map<String, Object>> byId = new LinkedHashMap<>();
        Map<String,Long> durations = new LinkedHashMap<>();
        for (Map<String, Object> asset : assets) {
            var publicAsset = new LinkedHashMap<>(asset);
            publicAsset.remove("storageKey");
            publicAsset.put("uri", "/api/v1/audio/" + asset.get("id"));
            long duration=((Number)asset.get("durationMs")).longValue();
            try {
                check(asset);
                long decoded=content.checkedDuration(asset.get("storageKey").toString(),((Number)asset.get("byteSize")).longValue(),asset.get("sha256").toString());
                if(decoded+1<duration)throw missingAudio();
            } catch (CatalogFailure | IOException | IllegalStateException error) {
                publicAsset.put("status","unavailable"); publicAsset.put("code","AUDIO_UNAVAILABLE");
            }
            durations.put(asset.get("id").toString(),duration);
            byId.put(asset.get("id").toString(),publicAsset);
        }
        var segments = mapper.convertValue(result.path("sentences"),new tools.jackson.core.type.TypeReference<List<Map<String,Object>>>() {});
        try { AudioIntervals.validate(segments,durations); }
        catch(IllegalArgumentException error) { throw new CatalogFailure(HttpStatus.SERVICE_UNAVAILABLE,"INVALID_CONTENT","句子音频区间或版本关联无效。"); }
        for (JsonNode sentence : result.path("sentences")) {
            var asset=byId.get(sentence.path("audioAssetId").asText());
            ((ObjectNode)sentence).put("assetId",sentence.path("audioAssetId").asText());
            ((ObjectNode)sentence).set("audio",mapper.valueToTree(asset));
        }
        result.set("audioAssets",mapper.valueToTree(byId.values()));
        var main=jdbc.queryForList("SELECT asset_id FROM lesson_audio WHERE version_id=?",result.path("versionId").asText());
        if(!main.isEmpty()) {
            String asset=main.getFirst().get("asset_id").toString();
            if(!byId.containsKey(asset))throw new CatalogFailure(HttpStatus.SERVICE_UNAVAILABLE,"INVALID_CONTENT","主音轨版本关联无效。");
            result.put("fullAudioAssetId",asset);
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
        var context=jdbc.queryForList("SELECT v.lesson_id,v.id,v.publication_state FROM audio_asset a JOIN lesson_version v ON v.id=a.lesson_version_id JOIN lesson l ON l.id=v.lesson_id JOIN content_license c ON c.id=v.license_id JOIN content_license ac ON ac.id=a.license_id WHERE a.id=? AND l.availability='available' AND (l.id='demo-01' OR (c.review_status='confirmed' AND ac.review_status='confirmed'))",id);
        if(!context.isEmpty() && "withdrawn".equals(context.getFirst().get("publication_state")))VersionAccess.require(jdbc,context.getFirst().get("lesson_id").toString(),context.getFirst().get("id").toString());
        var values = jdbc.queryForList("SELECT a.storage_key AS storageKey,a.byte_size AS byteSize,a.sha256,a.status,a.duration_ms AS durationMs FROM audio_asset a JOIN lesson_version v ON v.id=a.lesson_version_id JOIN lesson l ON l.id=v.lesson_id JOIN content_license c ON c.id=v.license_id JOIN content_license ac ON ac.id=a.license_id WHERE a.id=? AND v.publication_state='published' AND l.availability='available' AND (l.id='demo-01' OR (c.review_status='confirmed' AND ac.review_status='confirmed'))", id);
        if (values.isEmpty()) throw new CatalogFailure(HttpStatus.NOT_FOUND, "AUDIO_NOT_FOUND", "音频资源不存在。");
        var asset=values.getFirst();
        var path = check(asset);
        try {
            if(content.checkedDuration(asset.get("storageKey").toString(),((Number)asset.get("byteSize")).longValue(),asset.get("sha256").toString())+1<((Number)asset.get("durationMs")).longValue())throw missingAudio();
        } catch(IOException | IllegalStateException error){throw missingAudio();}
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
