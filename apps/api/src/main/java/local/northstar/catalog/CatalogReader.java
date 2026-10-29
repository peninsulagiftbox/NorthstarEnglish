package local.northstar.catalog;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Objects;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

@Service
public class CatalogReader {
    private final JdbcOperations jdbc;
    private final JsonMapper mapper = JsonMapper.builder().build();
    // Preserve the frozen Demo's existing local-test exception; it never grants access to other pending content.
    private static final String READABLE = "l.availability='available' AND v.publication_state='published' AND (l.id='demo-01' OR c.review_status='confirmed') AND EXISTS (SELECT 1 FROM sentence s WHERE s.lesson_version_id=v.id AND s.lesson_id=l.id)";
    private static final String SUMMARY = "SELECT l.id,l.slug,l.kind,l.availability,l.book_id AS bookId,l.sequence_no AS sequence,l.display_number AS displayNumber,v.id AS versionId,JSON_UNQUOTE(JSON_EXTRACT(v.payload_json,'$.title')) AS title,v.release_ready AS releaseReady,v.publication_state AS publicationState,v.content_readiness AS contentReadiness,'local_test_only' AS usageScope FROM lesson l JOIN lesson_version v ON v.id=l.current_version_id AND v.lesson_id=l.id JOIN content_license c ON c.id=v.license_id ";
    public CatalogReader(JdbcOperations jdbc) { this.jdbc = jdbc; }

    public Map<String, Object> books() {
        var books = jdbc.queryForList("SELECT b.id,b.catalog_key AS catalogKey,b.sequence_no AS sequence,b.title,b.edition_label AS editionLabel,b.availability,b.declared_lesson_count AS declaredLessonCount,b.metadata_source AS metadataSource,(SELECT COUNT(*) FROM lesson x WHERE x.book_id=b.id) AS actualLessonCount,(SELECT COUNT(*) FROM lesson l JOIN lesson_version v ON v.id=l.current_version_id AND v.lesson_id=l.id JOIN content_license c ON c.id=v.license_id WHERE l.book_id=b.id AND " + READABLE + ") AS availableLessonCount FROM book b ORDER BY b.sequence_no,b.id");
        return Map.of("books", books, "standaloneLessons", jdbc.queryForList(SUMMARY + "WHERE l.book_id IS NULL AND " + READABLE + " ORDER BY l.id"));
    }

    public List<Map<String, Object>> lessons() { return jdbc.queryForList(SUMMARY + "WHERE " + READABLE + " ORDER BY l.id"); }

    public Map<String, Object> bookLessons(String id, String cursor, int limit) {
        if (limit < 1 || limit > 100) throw problem(HttpStatus.BAD_REQUEST, "INVALID_LIMIT", "每页数量必须为1至100。");
        if (jdbc.queryForObject("SELECT COUNT(*) FROM book WHERE id=?", Integer.class, id) != 1)
            throw problem(HttpStatus.NOT_FOUND, "BOOK_NOT_FOUND", "册目录不存在。");
        List<Object> args = new ArrayList<>(); args.add(id);
        String after = "";
        if (cursor != null) {
            try {
                if (cursor.length() > 600) throw new IllegalArgumentException();
                var value = mapper.readTree(new String(Base64.getUrlDecoder().decode(cursor), StandardCharsets.UTF_8));
                if (!id.equals(value.path("book").asText()) || !value.path("id").asText().matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}") || !(value.path("sequence").isNull() || value.path("sequence").isIntegralNumber())) throw new IllegalArgumentException();
                String lastId = value.path("id").asText();
                if (value.path("sequence").isNull()) { after = " AND l.sequence_no IS NULL AND l.id>?"; args.add(lastId); }
                else {
                    long sequence = value.path("sequence").asLong();
                    if (sequence < 1 || sequence > Integer.MAX_VALUE) throw new IllegalArgumentException();
                    after = " AND (l.sequence_no>? OR l.sequence_no IS NULL OR (l.sequence_no=? AND l.id>?))";
                    args.add(sequence); args.add(sequence); args.add(lastId);
                }
            } catch (RuntimeException error) { throw problem(HttpStatus.BAD_REQUEST, "INVALID_CURSOR", "课程分页游标无效或不属于本册。"); }
        }
        args.add(limit + 1);
        // Unavailable rows expose only directory metadata, never payload text, exercises or media.
        var rows = jdbc.queryForList("SELECT l.id,l.book_id AS bookId,l.sequence_no AS sequence,l.display_number AS displayNumber,l.slug,l.kind,l.availability,CASE WHEN " + READABLE + " THEN v.id ELSE NULL END AS versionId,CASE WHEN " + READABLE + " THEN JSON_UNQUOTE(JSON_EXTRACT(v.payload_json,'$.title')) ELSE NULL END AS title,CASE WHEN " + READABLE + " THEN TRUE ELSE FALSE END AS readable FROM lesson l LEFT JOIN lesson_version v ON v.id=l.current_version_id AND v.lesson_id=l.id LEFT JOIN content_license c ON c.id=v.license_id WHERE l.book_id=?" + after + " ORDER BY l.sequence_no IS NULL,l.sequence_no,l.id LIMIT ?", args.toArray());
        for (var row : rows) row.put("readable", sqlBoolean(row.get("readable")));
        String next = null;
        if (rows.size() > limit) {
            rows = new ArrayList<>(rows.subList(0, limit));
            var last = rows.getLast();
            Map<String, Object> key = new LinkedHashMap<>(); key.put("book", id); key.put("sequence", last.get("sequence")); key.put("id", last.get("id"));
            next = Base64.getUrlEncoder().withoutPadding().encodeToString(mapper.writeValueAsString(key).getBytes(StandardCharsets.UTF_8));
        }
        var result = new LinkedHashMap<String, Object>(); result.put("items", rows); result.put("nextCursor", next); return result;
    }

    private Map<String, Object> version(String id, String requested) {
        var lessons = jdbc.queryForList("SELECT availability,current_version_id FROM lesson WHERE id=?", id);
        if (lessons.isEmpty() || !"available".equals(lessons.getFirst().get("availability"))) throw notFound();
        Object target = requested == null ? lessons.getFirst().get("current_version_id") : requested;
        var rows = jdbc.queryForList("SELECT v.id,v.lesson_id AS lessonId,v.version_no AS version,v.payload_json AS payload,v.release_ready AS releaseReady,v.publication_state AS publicationState,v.content_readiness AS contentReadiness,c.review_status AS reviewStatus FROM lesson_version v JOIN content_license c ON c.id=v.license_id WHERE v.id=?", target);
        if (rows.isEmpty()) throw problem(HttpStatus.NOT_FOUND, "VERSION_NOT_FOUND", "课程版本不存在。");
        var row = rows.getFirst();
        if (!id.equals(row.get("lessonId"))) throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "VERSION_LESSON_MISMATCH", "指定版本不属于本课。");
        if (!id.equals("demo-01") && !"confirmed".equals(row.get("reviewStatus"))) throw notFound();
        VersionAccess.require(jdbc,id,row.get("id").toString());
        return row;
    }

    public Map<String, Object> versions(String id) { return versions(id,null,null); }
    public Map<String, Object> versions(String id,String fromVersion,String fromSentence) {
        var rows=jdbc.queryForList("SELECT v.id AS versionId,v.version_no AS number,(v.id=l.current_version_id) AS isCurrent,v.publication_state AS publicationState,v.content_readiness AS contentReadiness,(v.publication_state='published') AS readable FROM lesson l JOIN lesson_version v ON v.lesson_id=l.id JOIN content_license c ON c.id=v.license_id WHERE l.id=? AND l.availability='available' AND (l.id='demo-01' OR c.review_status='confirmed') AND v.publication_state IN ('published','withdrawn') ORDER BY v.version_no,v.id",id);
        if(rows.isEmpty())throw notFound();
        if(fromVersion!=null && fromSentence!=null && jdbc.queryForObject("SELECT COUNT(*) FROM sentence WHERE id=? AND lesson_id=? AND lesson_version_id=?",Integer.class,fromSentence,id,fromVersion)!=1)throw problem(HttpStatus.UNPROCESSABLE_CONTENT,"VERSION_LESSON_MISMATCH","源句与课程版本不匹配。");
        for(var row:rows) {
            row.put("readable",sqlBoolean(row.get("readable")));row.put("isCurrent",sqlBoolean(row.get("isCurrent")));
            row.put("mappingStatus","unmapped");
            if(fromVersion!=null && fromSentence!=null) {
                var maps=jdbc.queryForList("SELECT to_sentence_id AS targetSentenceId,relation,mapping_status AS mappingStatus FROM version_sentence_map WHERE lesson_id=? AND from_version_id=? AND to_version_id=? AND from_sentence_id=?",id,fromVersion,row.get("versionId"),fromSentence);
                if(maps.size()==1 && Set.of("equivalent","edited").contains(Objects.toString(maps.getFirst().get("relation"),"")))row.putAll(maps.getFirst());
                else if(!maps.isEmpty())row.put("mappingStatus",maps.getFirst().get("mappingStatus").equals("no_target")?"no_target":"ambiguous");
            }
        }
        return Map.of("versions",rows);
    }

    public ObjectNode lesson(String id, String requested) {
        var v = version(id, requested); String versionId = v.get("id").toString();
        var raw = mapper.readTree(v.get("payload").toString());
        if (!(raw instanceof ObjectNode) || !id.equals(raw.path("id").asText()) || !versionId.equals(raw.path("versionId").asText())) throw invalid();
        ObjectNode result = (ObjectNode) raw;
        for (JsonNode exercise : result.path("exercises")) {
            if (!(exercise instanceof ObjectNode)) throw invalid();
            ((ObjectNode) exercise).remove(List.of("answerKey", "explanation"));
        }
        var paragraphs = jdbc.queryForList("SELECT id,stable_key AS stableKey,identity_id AS identityId,sequence_no AS sequence FROM paragraph WHERE version_id=? ORDER BY sequence_no,id", versionId);
        var sentences = jdbc.queryForList("SELECT id,stable_key AS stableKey,identity_id AS identityId,sequence_no AS sequence,paragraph_id AS paragraphId,speaker,text,translation,explanation,focus,audio_asset_id AS audioAssetId,start_ms AS startMs,end_ms AS endMs FROM sentence WHERE lesson_id=? AND lesson_version_id=? ORDER BY sequence_no,id", id, versionId);
        if (paragraphs.isEmpty() || sentences.isEmpty()) throw invalid();
        Map<String, Integer> positions = new LinkedHashMap<>();
        for (var paragraph : paragraphs) positions.put(paragraph.get("id").toString(), ((Number)paragraph.get("sequence")).intValue());
        int previousParagraph = 0;
        for (var sentence : sentences) {
            Integer position = positions.get(sentence.get("paragraphId").toString());
            if (position == null || position < previousParagraph || ((Number)sentence.get("sequence")).intValue() < 1) throw invalid();
            previousParagraph = position;
        }
        if (!result.has("vocabulary")) result.putArray("vocabulary");
        if (!result.has("exercises")) result.putArray("exercises");
        if (!result.has("explanationLabel")) result.put("explanationLabel", "本地预置讲解");
        result.put("usageScope", "local_test_only");
        result.set("sentences", mapper.valueToTree(sentences));
        result.set("paragraphs", mapper.valueToTree(paragraphs)); result.put("projectionVersion", "relational-v1");
        var metadata = jdbc.queryForMap("SELECT book_id AS bookId,sequence_no AS sequence,display_number AS displayNumber,kind,availability FROM lesson WHERE id=?", id);
        for (var entry : metadata.entrySet()) result.set(entry.getKey(), mapper.valueToTree(entry.getValue()));
        result.put("publicationState",v.get("publicationState").toString());result.put("contentReadiness",v.get("contentReadiness").toString());
        result.put("hasHistoricalEvidence",jdbc.queryForObject("SELECT COUNT(*) FROM version_sentence_map m JOIN exercise_attempt a ON a.sentence_id=m.from_sentence_id AND a.version_id=m.from_version_id WHERE m.lesson_id=? AND m.to_version_id=? AND m.relation='equivalent' AND m.mapping_status='confirmed'",Integer.class,id,versionId)>0);
        result.put("version", ((Number)v.get("version")).intValue()); result.put("releaseReady", (Boolean)v.get("releaseReady"));
        // No unsupported task UI for a content-only version; this is not a teaching-readiness claim.
        result.set("availableTasks", mapper.valueToTree(jdbc.queryForList("SELECT DISTINCT kind FROM exercise WHERE lesson_id=? AND version_id=? ORDER BY kind", String.class, id, versionId)));
        result.put("hasWritingTask", jdbc.queryForObject("SELECT COUNT(*) FROM writing_task WHERE lesson_id=? AND version_id=?", Integer.class, id, versionId) > 0);
        return result;
    }

    private static boolean sqlBoolean(Object value) { return Boolean.TRUE.equals(value) || value instanceof Number number && number.intValue() != 0; }

    static CatalogController.CatalogFailure notFound() { return problem(HttpStatus.NOT_FOUND, "LESSON_NOT_FOUND", "课程不存在或尚未开放。"); }
    static CatalogController.CatalogFailure invalid() { return problem(HttpStatus.SERVICE_UNAVAILABLE, "CONTENT_INCONSISTENT", "课程版本数据不完整或关联不一致。"); }
    static CatalogController.CatalogFailure problem(HttpStatus status, String code, String detail) { return new CatalogController.CatalogFailure(status, code, detail); }
}
