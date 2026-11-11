package local.northstar.catalog;

import java.nio.file.*;
import java.nio.channels.FileChannel;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;
import local.northstar.exercise.QuizSets;
import local.northstar.knowledge.KnowledgeRegistrationCli;

public final class ContentImport {
    private final JdbcTemplate db;
    private final TransactionTemplate tx;
    private final Path root;
    private final ContentPublication publication;
    private final java.util.function.Consumer<String> fault;
    private static final List<String> CONTENT_TABLES = List.of("book", "lesson", "lesson_version",
        "content_license", "paragraph", "sentence", "audio_asset", "sentence_identity", "paragraph_identity",
        "knowledge_concept", "knowledge_concept_revision", "knowledge_occurrence", "exercise",
        "exercise_set", "exercise_set_item", "audio_alignment", "lesson_audio", "knowledge_projection",
        "reading_question", "reading_option", "quiz_question", "writing_task", "writing_source",
        "legacy_knowledge_link", "exercise_sentence", "exercise_knowledge", "version_sentence_map", "content_validation");

    public ContentImport(JdbcTemplate db, TransactionTemplate tx, Path root) {
        this(db, tx, root, stage -> {});
    }
    ContentImport(JdbcTemplate db, TransactionTemplate tx, Path root, java.util.function.Consumer<String> fault) {
        this.db = db; this.tx = tx; this.root = root.toAbsolutePath().normalize(); this.fault = fault;
        publication = new ContentPublication(db, tx, this.root);
    }
    static void check(boolean value, String code) {
        if (!value) throw new IllegalArgumentException(code);
    }
    private String identity() {
        check(List.of("northstar-english-local-v1").equals(db.queryForList("SELECT project_key FROM project_identity", String.class)), "DATABASE_IDENTITY");
        return db.queryForObject("SELECT CONCAT(@@server_uuid,'/',DATABASE())", String.class);
    }
    private String schema() {
        check(db.queryForObject("SELECT COUNT(*) FROM flyway_schema_history WHERE success=0", Integer.class) == 0, "SCHEMA_FAILED");
        String version = db.queryForObject("SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1", String.class);
        check("013.04".equals(version), "SCHEMA_VERSION");
        return version;
    }
    private String contentSnapshot() {
        var state = new TreeMap<String, Object>();
        for (String table : CONTENT_TABLES) {
            var keys = db.queryForList("SELECT column_name FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=? AND constraint_name='PRIMARY' ORDER BY ordinal_position", String.class, table);
            state.put(table, db.query("SELECT * FROM " + table + " ORDER BY " + String.join(",", keys), (rows, index) -> {
                var values = new ArrayList<String>();
                for (int column = 1; column <= rows.getMetaData().getColumnCount(); column++) values.add(rows.getString(column));
                return values;
            }));
        }
        return CoreContent.hash(state);
    }
    private String current(String lesson) {
        var rows = db.queryForList("SELECT current_version_id FROM lesson WHERE id=?", lesson);
        return rows.isEmpty() ? null : Objects.toString(rows.getFirst().get("current_version_id"), null);
    }
    private List<Map<String, Object>> mediaPlan(CoreContent.Bundle bundle) {
        var result = new ArrayList<Map<String, Object>>();
        for (var asset : bundle.content().path("audioAssets")) {
            String key = asset.path("storageKey").asText();
            String existing = "absent";
            Path destination = destination(key);
            if (Files.exists(destination)) {
                try { existing = ContentPackage.sha256(Files.readAllBytes(CoreContent.checked(root, key))); }
                catch (Exception error) { throw new IllegalArgumentException("MEDIA_PATH", error); }
            }
            check(existing.equals("absent") || existing.equals(asset.path("sha256").asText()), "MEDIA_CONFLICT");
            result.add(Map.of("storageKey", key, "sha256", asset.path("sha256").asText(), "existing", existing));
        }
        return result;
    }
    private Path destination(String key) {
        check(!key.isBlank() && !Path.of(key).isAbsolute() && !key.contains("\\") && !key.contains("%")
            && !Arrays.asList(key.split("/")).contains(".."), "MEDIA_PATH");
        Path target = root.resolve(key).normalize();
        try {
            Path parent = target;
            while (!Files.exists(parent, LinkOption.NOFOLLOW_LINKS)) parent = parent.getParent();
            check(parent.toRealPath().startsWith(root.toRealPath()), "MEDIA_PATH");
        } catch (java.io.IOException error) { throw new IllegalArgumentException("MEDIA_ROOT", error); }
        return target;
    }
    private void validated(CoreContent.Bundle bundle) {
        var issues = new CoreContent().validate(bundle);
        check(issues.isEmpty(), "PACKAGE_INVALID:" + CoreContent.JSON.writeValueAsString(issues));
    }
    public Map<String, Object> plan(CoreContent.Bundle bundle) {
        validated(bundle);
        var readonly = new TransactionTemplate(Objects.requireNonNull(tx.getTransactionManager()));
        readonly.setReadOnly(true);
        readonly.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_REPEATABLE_READ);
        return readonly.execute(status -> {
            var content = bundle.content();
            var plan = new LinkedHashMap<String, Object>();
            plan.put("packageId", content.path("packageId").asText());
            plan.put("packageHash", bundle.contentHash());
            plan.put("rawHash", bundle.rawHash());
            plan.put("manifestHash", bundle.manifestHash());
            plan.put("targetDatabaseIdentity", identity());
            plan.put("targetSchemaVersion", schema());
            plan.put("targetMediaRoot", root.toString());
            plan.put("expectedCurrentVersionId", current(content.path("lesson").path("id").asText()));
            plan.put("lessonId", content.path("lesson").path("id").asText());
            plan.put("versionId", content.path("version").path("id").asText());
            plan.put("targetContentHash", contentSnapshot());
            plan.put("media", mediaPlan(bundle));
            plan.put("profile", "basic_content");
            plan.put("conflicts", conflicts(bundle));
            var objects = new TreeMap<String, Object>();
            for (String name : List.of("paragraphs", "sentences", "audioAssets", "knowledge", "exercises", "exerciseSets"))
                objects.put(name, content.path(name).size());
            plan.put("objects", objects);
            var additions = new TreeMap<String, List<String>>();
            var existing = new TreeMap<String, List<String>>();
            for (var mapping : Map.of("paragraphs", "paragraph", "sentences", "sentence", "audioAssets", "audio_asset",
                    "exercises", "exercise", "exerciseSets", "exercise_set", "sources", "content_license").entrySet()) {
                var addedIds = new ArrayList<String>();
                var existingIds = new ArrayList<String>();
                for (var item : content.path(mapping.getKey())) {
                    String id = item.path("id").asText();
                    (db.queryForObject("SELECT COUNT(*) FROM " + mapping.getValue() + " WHERE id=?", Integer.class, id) == 0
                        ? addedIds : existingIds).add(id);
                }
                additions.put(mapping.getKey(), addedIds);
                existing.put(mapping.getKey(), existingIds);
            }
            plan.put("newObjects", additions);
            plan.put("existingObjects", existing);
            plan.put("review", Map.of("rights", "confirmed", "proofreading", "confirmed", "alignment", "verified"));
            plan.put("planHash", CoreContent.hash(plan));
            return plan;
        });
    }
    private List<String> conflicts(CoreContent.Bundle bundle) {
        var conflicts = new ArrayList<String>();
        var content = bundle.content();
        String packageId = content.path("packageId").asText(), version = content.path("version").path("id").asText();
        var batches = db.queryForList("SELECT package_sha256,raw_sha256,manifest_sha256 FROM import_batch WHERE package_id=?", packageId);
        if (!batches.isEmpty() && (!bundle.contentHash().equals(batches.getFirst().get("package_sha256"))
            || !bundle.rawHash().equals(batches.getFirst().get("raw_sha256"))
            || !bundle.manifestHash().equals(batches.getFirst().get("manifest_sha256")))) conflicts.add("PACKAGE_ID_CONFLICT");
        if (db.queryForObject("SELECT COUNT(*) FROM lesson_version WHERE id=?", Integer.class, version) > 0
            && db.queryForObject("SELECT COUNT(*) FROM import_entry WHERE version_id=? AND package_id=?", Integer.class, version, packageId) == 0)
            conflicts.add("IMMUTABLE_VERSION_CONFLICT");
        for (var mapping : Map.of("paragraphs", "paragraph", "sentences", "sentence", "audioAssets", "audio_asset",
                "exercises", "exercise", "exerciseSets", "exercise_set").entrySet()) {
            String column = Set.of("sentence", "audio_asset").contains(mapping.getValue()) ? "lesson_version_id" : "version_id";
            for (var item : content.path(mapping.getKey())) {
                var versions = db.queryForList("SELECT " + column + " FROM " + mapping.getValue() + " WHERE id=?", String.class, item.path("id").asText());
                if (!versions.isEmpty() && !versions.getFirst().equals(version)) conflicts.add("OBJECT_VERSION_CONFLICT:" + mapping.getKey() + "/" + item.path("id").asText());
            }
        }
        for (var concept : content.path("knowledge")) {
            var matches = db.queryForList("SELECT kind,canonical_key,sense_key FROM knowledge_concept WHERE id=?", concept.path("conceptId").asText());
            if (!matches.isEmpty() && (!matches.getFirst().get("kind").equals(concept.path("kind").asText())
                || !matches.getFirst().get("canonical_key").equals(concept.path("canonicalKey").asText())
                || !matches.getFirst().get("sense_key").equals(concept.path("senseKey").asText())))
                conflicts.add("CONCEPT_IDENTITY_CONFLICT:" + concept.path("conceptId").asText());
        }
        return conflicts;
    }
    public Map<String, Object> apply(CoreContent.Bundle bundle, JsonNode plan, String approvedHash) {
        validated(bundle);
        ObjectNode unhashed = ((ObjectNode) plan).deepCopy();
        unhashed.remove("planHash");
        check(approvedHash.equals(plan.path("planHash").asText()) && approvedHash.equals(CoreContent.hash(unhashed)), "PLAN_HASH");
        check(bundle.contentHash().equals(plan.path("packageHash").asText())
            && bundle.rawHash().equals(plan.path("rawHash").asText())
            && bundle.manifestHash().equals(plan.path("manifestHash").asText()), "PACKAGE_CHANGED");
        check(identity().equals(plan.path("targetDatabaseIdentity").asText()) && schema().equals(plan.path("targetSchemaVersion").asText()), "TARGET_CHANGED");
        check(root.toString().equals(plan.path("targetMediaRoot").asText()), "MEDIA_ROOT_CHANGED");
        String packageId = bundle.content().path("packageId").asText();
        var materializationStarted = new java.util.concurrent.atomic.AtomicBoolean();
        try {
            return tx.execute(status -> {
                check(db.queryForList("SELECT id FROM import_mutex WHERE id='content-import' FOR UPDATE").size() == 1, "IMPORT_MUTEX_MISSING");
                check(conflicts(bundle).isEmpty(), "IDENTITY_CONFLICT");
                var entries = db.queryForList("SELECT * FROM import_entry WHERE package_id=?", packageId);
                if (!entries.isEmpty()) {
                    verify(bundle);
                    return Map.of("code", "no_op", "packageId", packageId);
                }
                String lesson = plan.path("lessonId").asText();
                db.queryForList("SELECT id FROM lesson WHERE id=? FOR UPDATE", lesson);
                check(Objects.equals(current(lesson), plan.path("expectedCurrentVersionId").isNull() ? null : plan.path("expectedCurrentVersionId").asText()), "STALE_CURRENT");
                check(contentSnapshot().equals(plan.path("targetContentHash").asText()), "STALE_PLAN");
                check(plan.path("conflicts").isEmpty(), "PLAN_CONFLICT");
                var priorPlans = db.queryForList("SELECT plan_sha256 FROM import_batch WHERE package_id=?", String.class, packageId);
                check(priorPlans.isEmpty() || priorPlans.getFirst().equals(approvedHash), "RECOVERY_PLAN_CONFLICT");
                var actualMedia = CoreContent.JSON.valueToTree(mediaPlan(bundle));
                if (!actualMedia.equals(plan.path("media"))) {
                    Path journal = root.resolve("imports").resolve(packageId).resolve("plan.json");
                    check(Files.isRegularFile(journal) && Arrays.equals(read(root, root.relativize(journal).toString()), CoreContent.bytes(plan)), "STALE_MEDIA");
                }
                if (db.queryForObject("SELECT COUNT(*) FROM import_batch WHERE package_id=?", Integer.class, packageId) == 0)
                    db.update("INSERT INTO import_batch(package_id,package_sha256,raw_sha256,manifest_sha256,plan_sha256,target_identity,schema_version,package_json,manifest_json,plan_json,state) VALUES (?,?,?,?,?,?,?,?,?,?,'validated')",
                        packageId, bundle.contentHash(), bundle.rawHash(), bundle.manifestHash(), approvedHash,
                        identity(), schema(), bundle.content().toString(), bundle.manifest().toString(), plan.toString());
                materializationStarted.set(true);
                write(root.resolve("imports").resolve(packageId).resolve("plan.json"), CoreContent.bytes(plan));
                materialize(bundle);
                db.update("UPDATE import_batch SET state='materialized',error_code=NULL,updated_at=UTC_TIMESTAMP(3) WHERE package_id=?", packageId);
                fault.accept("before_dml");
                insert(bundle);
                String version = bundle.content().path("version").path("id").asText();
                String result = publication.validate(lesson, version, bundle.manifest().path("proofreading").path("reviewer").asText());
                check("VALIDATED".equals(result), result);
                db.update("INSERT INTO import_entry(version_id,package_id,lesson_id,expected_current_id,snapshot_sha256,state) VALUES (?,?,?,?,?,'applied')",
                    version, packageId, lesson, current(lesson), publication.snapshot(version));
                db.update("UPDATE import_batch SET state='applied',updated_at=UTC_TIMESTAMP(3) WHERE package_id=?", packageId);
                fault.accept("before_commit");
                return Map.<String, Object>of("code", "applied", "packageId", packageId, "versionId", version);
            });
        } catch (RuntimeException error) {
            if (!materializationStarted.get()) throw error;
            tx.executeWithoutResult(status -> {
                check(db.queryForList("SELECT id FROM import_mutex WHERE id='content-import' FOR UPDATE").size() == 1, "IMPORT_MUTEX_MISSING");
                if (db.queryForObject("SELECT COUNT(*) FROM import_batch WHERE package_id=?", Integer.class, packageId) == 0)
                    db.update("INSERT INTO import_batch(package_id,package_sha256,raw_sha256,manifest_sha256,plan_sha256,target_identity,schema_version,package_json,manifest_json,plan_json,state,error_code) VALUES (?,?,?,?,?,?,?,?,?,?,'partial_failed','APPLY_INTERRUPTED')",
                        packageId, bundle.contentHash(), bundle.rawHash(), bundle.manifestHash(), approvedHash,
                        identity(), schema(), bundle.content().toString(), bundle.manifest().toString(), plan.toString());
            });
            throw error;
        }
    }
    public Map<String, Object> verify(CoreContent.Bundle bundle) {
        validated(bundle);
        String packageId = bundle.content().path("packageId").asText();
        var batches = db.queryForList("SELECT package_sha256,raw_sha256,manifest_sha256 FROM import_batch WHERE package_id=?", packageId);
        check(batches.size() == 1 && bundle.contentHash().equals(batches.getFirst().get("package_sha256"))
            && bundle.rawHash().equals(batches.getFirst().get("raw_sha256"))
            && bundle.manifestHash().equals(batches.getFirst().get("manifest_sha256")), "PACKAGE_ID_CONFLICT");
        var rows = db.queryForList("SELECT * FROM import_entry WHERE package_id=?", packageId);
        check(rows.size() == 1, "IMPORT_NOT_APPLIED");
        var entry = rows.getFirst();
        var content = bundle.content();
        String version = entry.get("version_id").toString();
        check(Arrays.equals(read(root, "imports/" + packageId + "/package.json"), read(bundle.root(), "package.json"))
            && Arrays.equals(read(root, "imports/" + packageId + "/manifest.json"), read(bundle.root(), "manifest.json")), "SAVED_PACKAGE_CHANGED");
        check(Arrays.equals(read(root, "packages/" + version + "/lesson.json"), CoreContent.bytes(projection(content)))
            && Arrays.equals(read(root, "packages/" + version + "/manifest.json"), CoreContent.bytes(projectionManifest(content))), "SAVED_PROJECTION_CHANGED");
        check(entry.get("snapshot_sha256").equals(publication.snapshot(entry.get("version_id").toString())), "IMPORTED_CONTENT_CHANGED");
        for (var media : mediaPlan(bundle)) check(media.get("sha256").equals(media.get("existing")), "MEDIA_MISSING");
        return Map.of("code", "verified", "versionId", entry.get("version_id"), "state", entry.get("state"));
    }
    public Map<String, Object> publish(CoreContent.Bundle bundle, String operationId, String expected, String actor) {
        verify(bundle);
        var content = bundle.content();
        String version = content.path("version").path("id").asText();
        String sha = db.queryForObject("SELECT content_sha256 FROM lesson_version WHERE id=?", String.class, version);
        var result = publication.execute(new ContentPublication.Request(operationId, "publish",
            content.path("lesson").path("id").asText(), version, expected, sha, actor));
        if ("PUBLISHED".equals(result.code())) tx.executeWithoutResult(status -> {
            db.update("UPDATE import_entry SET state='published' WHERE version_id=?", version);
            db.update("UPDATE import_batch SET state='published',updated_at=UTC_TIMESTAMP(3) WHERE package_id=?", content.path("packageId").asText());
        });
        return Map.of("code", result.code(), "operationId", operationId);
    }
    public List<Map<String, Object>> status(String packageId) {
        check(packageId.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}"), "PACKAGE_ID");
        var rows = db.queryForList("SELECT package_id,package_sha256,plan_sha256,state,error_code FROM import_batch WHERE package_id=?", packageId);
        if (rows.isEmpty() && Files.isRegularFile(root.resolve("imports").resolve(packageId).resolve("plan.json")))
            return List.of(Map.of("package_id", packageId, "state", "orphaned_media", "error_code", "DATABASE_COMMIT_NOT_FOUND"));
        return rows;
    }
    private void write(Path target, byte[] bytes) {
        try {
            destination(root.relativize(target).toString());
            Files.createDirectories(target.getParent());
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
                check(Arrays.equals(Files.readAllBytes(target), bytes), "MEDIA_CONFLICT");
                return;
            }
            Path staging = Files.createTempFile(target.getParent(), ".northstar-stage-", ".tmp");
            fault.accept("before_copy");
            Files.write(staging, bytes);
            try (var channel = FileChannel.open(staging, StandardOpenOption.WRITE)) { channel.force(true); }
            fault.accept("staged");
            fault.accept("before_materialize");
            try { Files.createLink(target, staging); }
            catch (FileAlreadyExistsException error) { check(Arrays.equals(Files.readAllBytes(target), bytes), "MEDIA_CONFLICT"); }
            Files.delete(staging);
            try (var directory = FileChannel.open(target.getParent(), StandardOpenOption.READ)) { directory.force(true); }
            fault.accept("materialized");
        } catch (java.io.IOException error) { throw new IllegalStateException("MEDIA_MATERIALIZATION_FAILED", error); }
    }
    private void materialize(CoreContent.Bundle bundle) {
        var content = bundle.content();
        String version = content.path("version").path("id").asText();
        Path saved = root.resolve("imports").resolve(content.path("packageId").asText());
        write(saved.resolve("package.json"), read(bundle.root(), "package.json"));
        write(saved.resolve("manifest.json"), read(bundle.root(), "manifest.json"));
        for (var source : content.path("sources")) write(saved.resolve(source.path("sourceRef").asText()), read(bundle.root(), source.path("sourceRef").asText()));
        for (var asset : content.path("audioAssets")) {
            byte[] audio = read(bundle.root(), asset.path("storageKey").asText());
            check(ContentPackage.sha256(audio).equals(asset.path("sha256").asText()), "MEDIA_CHANGED");
            write(destination(asset.path("storageKey").asText()), audio);
            write(saved.resolve(asset.path("storageKey").asText()), audio);
        }
        write(root.resolve("packages").resolve(version).resolve("lesson.json"), CoreContent.bytes(projection(content)));
        write(root.resolve("packages").resolve(version).resolve("manifest.json"), CoreContent.bytes(projectionManifest(content)));
    }
    private static byte[] read(Path root, String name) {
        try { return Files.readAllBytes(CoreContent.checked(root, name)); }
        catch (java.io.IOException error) { throw new IllegalArgumentException("SOURCE_UNREADABLE", error); }
    }
    private ObjectNode projection(JsonNode content) {
        var projected = CoreContent.JSON.createObjectNode();
        projected.put("id", content.path("lesson").path("id").asText());
        projected.put("versionId", content.path("version").path("id").asText());
        projected.put("title", content.path("lesson").path("title").asText());
        projected.put("importPackageId", content.path("packageId").asText());
        projected.set("sentences", content.path("sentences"));
        projected.set("paragraphs", content.path("paragraphs"));
        projected.set("exercises", content.path("exercises"));
        if (content.has("fullAudioAssetId")) projected.set("fullAudioAssetId", content.path("fullAudioAssetId"));
        return projected;
    }
    private Map<String, Object> projectionManifest(JsonNode content) {
        return Map.of("versionId", content.path("version").path("id").asText(), "lessonId", content.path("lesson").path("id").asText(),
            "lessonSha256", CoreContent.hash(projection(content)), "audioAssets", content.path("audioAssets"));
    }
    private String stable(String table, String lesson, String key) {
        var rows = db.queryForList("SELECT id FROM " + table + "_identity WHERE lesson_id=? AND registry_key=?", String.class, lesson, key);
        if (!rows.isEmpty()) return rows.getFirst();
        String id = UUID.randomUUID().toString();
        db.update("INSERT INTO " + table + "_identity(id,lesson_id,registry_key) VALUES (?,?,?)", id, lesson, key);
        return id;
    }
    private void insert(CoreContent.Bundle bundle) {
        var content = bundle.content();
        String lesson = content.path("lesson").path("id").asText(), version = content.path("version").path("id").asText();
        for (var source : content.path("sources")) {
            var existing = db.queryForList("SELECT details_json FROM content_license WHERE id=?", source.path("id").asText());
            if (!existing.isEmpty()) check(CoreContent.JSON.readTree(existing.getFirst().get("details_json").toString()).equals(source), "LICENSE_CONFLICT");
            else db.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,?,?)",
                source.path("id").asText(), source.path("sourceType").asText(), source.path("sourceRef").asText(), source.path("reviewStatus").asText(), source.toString());
        }
        var book = content.path("book");
        String bookId = book.isNull() ? null : book.path("id").asText();
        if (bookId != null) {
            var books = db.queryForList("SELECT catalog_key,edition_label,title FROM book WHERE id=?", bookId);
            if (books.isEmpty()) db.update("INSERT INTO book(id,catalog_key,sequence_no,title,edition_label,availability,declared_lesson_count,metadata_source) VALUES (?,?,1,?,?,'catalog_only',1,'original import')", bookId, book.path("catalogKey").asText(), book.path("title").asText(), book.path("editionLabel").asText());
            else check(books.getFirst().get("catalog_key").equals(book.path("catalogKey").asText()) && books.getFirst().get("edition_label").equals(book.path("editionLabel").asText()), "BOOK_IDENTITY_CONFLICT");
        }
        var lessons = db.queryForList("SELECT book_id,slug,kind FROM lesson WHERE id=?", lesson);
        if (lessons.isEmpty()) db.update("INSERT INTO lesson(id,slug,kind,availability,book_id,sequence_no) VALUES (?,?,?,'draft',?,?)",
            lesson, content.path("lesson").path("slug").asText(), content.path("lesson").path("kind").asText(), bookId, content.path("lesson").path("sequence").asInt());
        else check(Objects.equals(bookId, lessons.getFirst().get("book_id")) && lessons.getFirst().get("slug").equals(content.path("lesson").path("slug").asText())
            && lessons.getFirst().get("kind").equals(content.path("lesson").path("kind").asText()), "LESSON_IDENTITY_CONFLICT");
        db.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready,publication_state,content_readiness,schema_version) VALUES (?,?,?,?,?,?,?,TRUE,'draft','basic_content','northstar.local.audio.v1')",
            version, lesson, content.path("version").path("number").asInt(), content.path("version").path("licenseId").asText(),
            CoreContent.hash(projection(content)), CoreContent.hash(projectionManifest(content)), projection(content).toString());
        for (var paragraph : content.path("paragraphs"))
            db.update("INSERT INTO paragraph(id,version_id,stable_key,sequence_no,lesson_id,identity_id) VALUES (?,?,?,?,?,?)",
                paragraph.path("id").asText(), version, paragraph.path("stableKey").asText(), paragraph.path("sequence").asInt(), lesson,
                stable("paragraph", lesson, paragraph.path("stableKey").asText()));
        for (var asset : content.path("audioAssets")) {
            db.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,?,?,?,?,'ready')",
                asset.path("id").asText(), version, asset.path("licenseId").asText(), asset.path("sourceKind").asText(), asset.path("storageKey").asText(),
                asset.path("mimeType").asText(), asset.path("byteSize").asLong(), asset.path("durationMs").asInt(), asset.path("sha256").asText());
            var alignment = asset.path("alignment");
            db.update("INSERT INTO audio_alignment(id,version_id,asset_id,audio_sha256,transcript_sha256,timebase,tool,tool_version,parameters_json,status,reviewer,reviewed_at) VALUES (?,?,?,?,?,'asset_milliseconds',?,'core-v1',?,'verified',?,?)",
                UUID.randomUUID().toString(), version, asset.path("id").asText(), asset.path("sha256").asText(), alignment.path("transcriptSha256").asText(),
                alignment.path("method").asText(), alignment.toString(), alignment.path("reviewer").asText(), java.sql.Timestamp.from(java.time.Instant.parse(alignment.path("reviewedAt").asText())));
        }
        if (content.has("fullAudioAssetId")) db.update("INSERT INTO lesson_audio(version_id,asset_id) VALUES (?,?)", version, content.path("fullAudioAssetId").asText());
        for (var sentence : content.path("sentences"))
            db.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                sentence.path("id").asText(), lesson, version, sentence.path("stableKey").asText(), sentence.path("sequence").asInt(),
                sentence.path("speaker").asText(), sentence.path("text").asText(), sentence.path("translation").asText(), sentence.path("explanation").asText(),
                sentence.path("focus").asText(), sentence.path("audioAssetId").asText(), sentence.path("startMs").asInt(), sentence.path("endMs").asInt(),
                sentence.path("paragraphId").asText(), stable("sentence", lesson, sentence.path("stableKey").asText()));
        relations(bundle);
        sets(content);
    }
    private void relations(CoreContent.Bundle bundle) {
        var content = bundle.content();
        String lesson = content.path("lesson").path("id").asText(), version = content.path("version").path("id").asText();
        String reviewer = bundle.manifest().path("proofreading").path("reviewer").asText();
        String reviewedAt = bundle.manifest().path("proofreading").path("reviewedAt").asText();
        var concepts = new ArrayList<Object>();
        var occurrences = new ArrayList<Object>();
        var links = new ArrayList<Object>();
        var sourceLinks = new ArrayList<Object>();
        var knowledgeLinks = new ArrayList<Object>();
        var revisions = new HashMap<String, String>();
        var points = new HashMap<String, String>();
        var knowledge = new HashMap<String, JsonNode>();
        for (var item : content.path("knowledge")) {
            String concept = item.path("conceptId").asText(), occurrence = item.path("occurrenceId").asText();
            knowledge.put(occurrence, item);
            if (!revisions.containsKey(concept)) {
                String revision = UUID.randomUUID().toString();
                revisions.put(concept, revision);
                concepts.add(Map.of("id", concept, "kind", item.path("kind").asText(), "canonicalKey", item.path("canonicalKey").asText(),
                    "senseKey", item.path("senseKey").asText(), "revisions", List.of(Map.of("id", revision, "displayName", item.path("term").asText(),
                    "explanation", item.path("meaning").asText(), "sourceRef", "import:" + content.path("packageId").asText(),
                    "reviewStatus", "confirmed", "reviewedAt", reviewedAt))));
            }
            occurrences.add(Map.of("id", occurrence, "revisionId", revisions.get(concept), "scope", "sentence",
                "sentenceId", item.path("sentenceId").asText(), "usage", Map.of("term", item.path("term").asText(), "meaning", item.path("meaning").asText())));
            String point = UUID.randomUUID().toString();
            points.put(occurrence, point);
            db.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES (?,?,?,?,?,?,?,?)",
                point, lesson, version, item.path("sentenceId").asText(), item.path("term").asText(), item.path("meaning").asText(), "本地预置讲解", "");
            links.add(Map.of("knowledgePointId", point, "occurrenceId", occurrence, "mappingBasis", "manual_review"));
        }
        for (var exercise : content.path("exercises")) {
            String id = exercise.path("id").asText(), kind = exercise.path("kind").asText(), anchor = exercise.path("sentenceIds").get(0).asText();
            db.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,?,?,?,?,?)",
                id, lesson, version, anchor, kind, kind.equals("dictation") ? "english_token_v1" : kind + "_v1");
            for (var sentence : exercise.path("sentenceIds")) sourceLinks.add(Map.of("exerciseId", id, "sentenceId", sentence.asText(), "role", anchor.equals(sentence.asText()) ? "primary" : "supporting"));
            for (var occurrence : exercise.path("occurrenceIds")) knowledgeLinks.add(Map.of("exerciseId", id, "occurrenceId", occurrence.asText(), "role", "target"));
            if (!kind.equals("dictation")) {
                String target = null;
                for (var occurrence : exercise.path("occurrenceIds"))
                    if (anchor.equals(knowledge.get(occurrence.asText()).path("sentenceId").asText())) { target = points.get(occurrence.asText()); break; }
                check(target != null, "PRIMARY_KNOWLEDGE_REQUIRED");
                var question = ((ObjectNode) exercise).deepCopy();
                question.put("sentenceId", anchor); question.put("knowledgePointId", target);
                String table = kind.equals("reading_choice") ? "reading_question" : "quiz_question";
                db.update("INSERT INTO " + table + "(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",
                    id, version, anchor, target, question.toString());
                if (kind.equals("reading_choice"))
                    for (var option : exercise.path("options")) db.update("INSERT INTO reading_option(id,exercise_id) VALUES (?,?)", option.path("id").asText(), id);
            }
        }
        var registration = Map.of("versionId", version, "reviewer", reviewer, "concepts", concepts,
            "occurrences", occurrences, "legacyLinks", links, "exerciseSentences", sourceLinks, "exerciseKnowledge", knowledgeLinks);
        new KnowledgeRegistrationCli(db, Objects.requireNonNull(tx.getTransactionManager())).register(CoreContent.JSON.valueToTree(registration));
    }
    private void sets(JsonNode content) {
        String version = content.path("version").path("id").asText();
        for (var set : content.path("exerciseSets")) {
            check(set.path("id").asText().length() <= 36 && "practice".equals(set.path("purpose").asText())
                && "quiz_choice_v1".equals(set.path("protocolVersion").asText()), "SET_PROTOCOL_UNSUPPORTED");
            String id = set.path("id").asText(), context = set.path("contextGroupId").asText();
            db.update("INSERT INTO exercise_set(id,version_id,purpose,protocol_version,context_group_id,snapshot_origin) VALUES (?,?,'practice','quiz_choice_v1',?,'version_content')", id, version, context);
            int ordinal = 0;
            for (var exercise : set.path("exerciseIds")) {
                var row = db.queryForMap("SELECT *,CAST(payload_json AS CHAR CHARACTER SET utf8mb4) AS question_text FROM quiz_question WHERE exercise_id=? AND version_id=?", exercise.asText(), version);
                row.put("ordinal", ++ordinal);
                db.update("INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) VALUES (?,?,?,?,?,?,?,?)",
                    id, exercise.asText(), version, row.get("sentence_id"), row.get("knowledge_point_id"), ordinal, row.get("question_text"), QuizSets.itemHash(row));
            }
            db.update("UPDATE exercise_set SET set_hash=?,frozen=TRUE WHERE id=?", QuizSets.setHash(version, context, QuizSets.items(db, id)), id);
        }
    }
}
