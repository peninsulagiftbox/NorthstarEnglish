package local.northstar.catalog;

import java.util.Objects;
import org.flywaydb.core.Flyway;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;

@Component
public class ContentSeeder implements ApplicationRunner {
    private final ContentPackage content;
    private final Flyway flyway;
    public ContentSeeder(ContentPackage content, Flyway flyway) { this.content = content; this.flyway = flyway; }

    @Override public void run(ApplicationArguments arguments) throws Exception { seed(); }

    public void seed() throws Exception {
        var bundles = new java.util.ArrayList<ContentPackage.Bundle>();
        for (int number : content.publishedVersions()) bundles.add(content.load(number));
        String activeVersion = "demo-01-v" + content.activeVersion();
        var source = flyway.getConfiguration().getDataSource();
        var jdbc = new JdbcTemplate(source);
        new TransactionTemplate(new DataSourceTransactionManager(source)).executeWithoutResult(transaction -> {
            // Lock the project row so simultaneous local startups cannot race the seed.
            jdbc.queryForObject("SELECT project_key FROM project_identity FOR UPDATE", String.class);
            for (var bundle : bundles) {
            String versionId = text(bundle.lesson(), "versionId");
            String folder = "demo-01/v" + bundle.lesson().path("version").asInt() + "/";
            var versions = jdbc.queryForList("SELECT content_sha256, manifest_sha256 FROM lesson_version WHERE id = ?", versionId);
            if (!versions.isEmpty()) {
                if (!Objects.equals(bundle.lessonHash(), versions.getFirst().get("content_sha256"))
                        || !Objects.equals(bundle.manifestHash(), versions.getFirst().get("manifest_sha256"))) {
                    throw new IllegalStateException("Frozen content version changed; create a new version");
                }
                verifyRows(jdbc, bundle);
                seedReading(jdbc, bundle.lesson());
                seedWriting(jdbc, bundle.lesson());
                continue;
            }
            JsonNode lesson = bundle.lesson(), manifest = bundle.manifest();
            for (JsonNode license : manifest.path("licenses")) {
                if (jdbc.queryForObject("SELECT COUNT(*) FROM content_license WHERE id=?", Integer.class, text(license,"id")) == 1) continue;
                jdbc.update("INSERT INTO content_license (id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,?,?)",
                        text(license,"id"), text(license,"sourceType"), text(license,"sourceRef"), text(license,"reviewStatus"), license.toString());
            }
            for (JsonNode book : manifest.path("books")) {
                if (jdbc.queryForObject("SELECT COUNT(*) FROM book WHERE id=?", Integer.class, text(book,"id")) == 1) continue;
                jdbc.update("INSERT INTO book (id,catalog_key,sequence_no,title,edition_label,availability,declared_lesson_count,metadata_source) VALUES (?,?,?,?,?,?,?,?)",
                        text(book,"id"), text(book,"catalogKey"), book.path("sequence").asInt(), text(book,"title"), text(book,"editionLabel"),
                        text(book,"availability"), book.path("declaredLessonCount").asInt(), text(book,"metadataSource"));
            }
            if (jdbc.queryForObject("SELECT COUNT(*) FROM lesson WHERE id=?", Integer.class, text(lesson,"id")) == 0) jdbc.update("INSERT INTO lesson (id,slug,kind,availability) VALUES (?,?,?,?)", text(lesson,"id"), text(lesson,"slug"), text(lesson,"kind"), text(lesson,"availability"));
            jdbc.update("INSERT INTO lesson_version (id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready) VALUES (?,?,?,?,?,?,?,FALSE)",
                    text(lesson,"versionId"), text(lesson,"id"), lesson.path("version").asInt(), text(lesson,"licenseId"), bundle.lessonHash(), bundle.manifestHash(), lesson.toString());
            for (JsonNode audio : manifest.path("audioAssets")) {
                jdbc.update("INSERT INTO audio_asset (id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,?,?,?,?,'ready')",
                        text(audio,"id"), text(lesson,"versionId"), text(audio,"licenseId"), text(audio,"sourceKind"), folder + text(audio,"storageKey"),
                        text(audio,"mimeType"), audio.path("byteSize").asInt(), audio.path("durationMs").asInt(), text(audio,"sha256"));
            }
            for (JsonNode s : lesson.path("sentences")) {
                jdbc.update("INSERT INTO sentence (id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        text(s,"id"), text(lesson,"id"), text(lesson,"versionId"), text(s,"stableKey"), s.path("sequence").asInt(), text(s,"speaker"),
                        text(s,"text"), text(s,"translation"), text(s,"explanation"), text(s,"focus"), text(s,"audioAssetId"), 0, s.path("endMs").asInt());
            }
            // Phase 04 dictation targets publish atomically with the immutable version.
            for (JsonNode sentence : lesson.path("sentences")) {
                jdbc.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind) VALUES (?,?,?,?,'dictation')",
                        text(sentence,"id") + "-dictation", text(lesson,"id"), versionId, text(sentence,"id"));
            }
            verifyRows(jdbc, bundle);
            seedReading(jdbc, lesson);
            seedWriting(jdbc, lesson);
            }
            var current = jdbc.queryForList("SELECT current_version_id FROM lesson WHERE id='demo-01'");
            Object old = current.getFirst().get("current_version_id");
            if (old != null && bundles.stream().noneMatch(b -> old.equals(text(b.lesson(),"versionId")))) throw new IllegalStateException("Unknown active content version; refuse overwrite");
            jdbc.update("UPDATE lesson SET current_version_id=? WHERE id='demo-01'", activeVersion);
        });
    }

    private void seedWriting(JdbcTemplate jdbc, JsonNode lesson) {
        String version=text(lesson,"versionId"), id=version+"-writing-01";
        if(jdbc.queryForObject("SELECT COUNT(*) FROM writing_task WHERE id=?",Integer.class,id)==0) {
            jdbc.update("INSERT INTO writing_task(id,lesson_id,version_id,prompt) VALUES (?,?,?,?)",id,text(lesson,"id"),version,"Write 2–3 sentences about helping in a garden. Use please, beside, or I can ...");
            for(JsonNode exercise:lesson.path("exercises")) if("writing_prompt".equals(text(exercise,"kind")))
                for(JsonNode sentence:exercise.path("sentenceIds")) jdbc.update("INSERT INTO writing_source(task_id,version_id,sentence_id) VALUES (?,?,?)",id,version,sentence.asText());
        }
        if(jdbc.queryForObject("SELECT COUNT(*) FROM writing_source WHERE task_id=?",Integer.class,id)!=3)throw new IllegalStateException("Writing source incomplete");
    }

    private void seedReading(JdbcTemplate jdbc, JsonNode lesson) {
        String version = text(lesson,"versionId"), lessonId = text(lesson,"id");
        var notes = java.util.Map.of("community garden","名词短语 · 本课指社区共用的花园", "beside","介词 · 表示在某物旁边，相当于 next to", "bench","名词 · 本课指供人坐的长椅", "soil","不可数名词 · 本课指种植物的土壤", "watering can","名词短语 · 本课指浇水用的壶");
        for (JsonNode word : lesson.path("vocabulary")) {
            String id = text(word,"id"), sentence = word.path("sentenceIds").get(0).asText();
            Object[] values = {lessonId,version,sentence,text(word,"term"),text(word,"meaning"),notes.getOrDefault(text(word,"term"),"本课语境用法"),text(word,"example")};
            if (jdbc.queryForObject("SELECT COUNT(*) FROM knowledge_point WHERE id=?", Integer.class,id)==0)
                jdbc.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES (?,?,?,?,?,?,?,?)",id,values[0],values[1],values[2],values[3],values[4],values[5],values[6]);
            verify(jdbc,"knowledge_point",id,new String[]{"lesson_id","version_id","sentence_id","term","meaning","usage_note","example_text"},values);
        }
        for (JsonNode question : lesson.path("exercises")) {
            if (!"reading_choice".equals(text(question,"kind"))) continue;
            String id=text(question,"id"), sentence=question.path("sentenceIds").get(0).asText();
            if(jdbc.queryForObject("SELECT COUNT(*) FROM exercise WHERE id=?",Integer.class,id)==0) {
                jdbc.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,?,?,?,'reading_choice','reading_choice_v1')",id,lessonId,version,sentence);
                jdbc.update("INSERT INTO reading_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",id,version,sentence,version+"-kp-beside",question.toString());
                for(JsonNode option : question.path("options")) jdbc.update("INSERT INTO reading_option(id,exercise_id) VALUES (?,?)",text(option,"id"),id);
            }
            verify(jdbc,"exercise",id,new String[]{"lesson_id","version_id","sentence_id","kind","algorithm_version"},new Object[]{lessonId,version,sentence,"reading_choice","reading_choice_v1"});
            var stored=jdbc.queryForMap("SELECT payload_json,knowledge_point_id FROM reading_question WHERE exercise_id=?",id);
            if(!tools.jackson.databind.json.JsonMapper.builder().build().readTree(stored.get("payload_json").toString()).equals(question) || !(version+"-kp-beside").equals(stored.get("knowledge_point_id"))) throw new IllegalStateException("Reading content differs from frozen version");
        }
    }

    private void verifyRows(JdbcTemplate jdbc, ContentPackage.Bundle bundle) {
        String versionId = text(bundle.lesson(),"versionId");
        String folder = "demo-01/v" + bundle.lesson().path("version").asInt() + "/";
        if (jdbc.queryForObject("SELECT COUNT(*) FROM sentence WHERE lesson_version_id = ?", Integer.class, versionId) != 10
                || jdbc.queryForObject("SELECT COUNT(*) FROM audio_asset WHERE lesson_version_id = ?", Integer.class, versionId) != 10
                || jdbc.queryForObject("SELECT COUNT(*) FROM book WHERE availability = 'catalog_only'", Integer.class) != 4) {
            throw new IllegalStateException("Seed data incomplete; refuse silent repair");
        }
        String payload = jdbc.queryForObject("SELECT payload_json FROM lesson_version WHERE id = ?", String.class, versionId);
        if (!tools.jackson.databind.json.JsonMapper.builder().build().readTree(payload).equals(bundle.lesson())) {
            throw new IllegalStateException("Stored content differs from frozen version");
        }
        for (JsonNode sentence : bundle.lesson().path("sentences")) {
            verify(jdbc, "exercise", text(sentence,"id") + "-dictation", new String[]{"lesson_id","version_id","sentence_id","kind","algorithm_version"},
                    new Object[]{"demo-01",versionId,text(sentence,"id"),"dictation","english_token_v1"});
            verify(jdbc, "sentence", text(sentence,"id"), new String[]{"lesson_id","lesson_version_id","stable_key","sequence_no","speaker","text","translation","explanation","focus","audio_asset_id","start_ms","end_ms"},
                    new Object[]{"demo-01",versionId,text(sentence,"stableKey"),sentence.path("sequence").asInt(),text(sentence,"speaker"),text(sentence,"text"),text(sentence,"translation"),text(sentence,"explanation"),text(sentence,"focus"),text(sentence,"audioAssetId"),0,sentence.path("endMs").asInt()});
        }
        for (JsonNode audio : bundle.manifest().path("audioAssets")) {
            verify(jdbc, "audio_asset", text(audio,"id"), new String[]{"lesson_version_id","license_id","source_kind","storage_key","mime_type","byte_size","duration_ms","sha256","status"},
                    new Object[]{versionId,text(audio,"licenseId"),text(audio,"sourceKind"),folder+text(audio,"storageKey"),text(audio,"mimeType"),audio.path("byteSize").asInt(),audio.path("durationMs").asInt(),text(audio,"sha256"),"ready"});
        }
        for (JsonNode book : bundle.manifest().path("books")) {
            verify(jdbc, "book", text(book,"id"), new String[]{"catalog_key","sequence_no","title","edition_label","availability","declared_lesson_count","metadata_source"},
                    new Object[]{text(book,"catalogKey"),book.path("sequence").asInt(),text(book,"title"),text(book,"editionLabel"),"catalog_only",book.path("declaredLessonCount").asInt(),text(book,"metadataSource")});
        }
        var mapper = tools.jackson.databind.json.JsonMapper.builder().build();
        for (JsonNode license : bundle.manifest().path("licenses")) {
            verify(jdbc, "content_license", text(license,"id"), new String[]{"source_type","source_ref","review_status"},
                    new Object[]{text(license,"sourceType"),text(license,"sourceRef"),text(license,"reviewStatus")});
            if (!mapper.readTree(jdbc.queryForObject("SELECT details_json FROM content_license WHERE id=?", String.class, text(license,"id"))).equals(license)) {
                throw new IllegalStateException("Stored license differs from frozen version");
            }
        }
        verify(jdbc, "lesson", "demo-01", new String[]{"slug","kind","availability","book_id"},
                new Object[]{text(bundle.lesson(),"slug"),"original_demo","available",null});
    }

    private static void verify(JdbcTemplate jdbc, String table, String id, String[] columns, Object[] expected) {
        // Table and column names are private constants above, never request parameters.
        var row = jdbc.queryForMap("SELECT " + String.join(",", columns) + " FROM " + table + " WHERE id=?", id);
        for (int i = 0; i < columns.length; i++) {
            if (!Objects.equals(Objects.toString(expected[i], null), Objects.toString(row.get(columns[i]), null))) {
                throw new IllegalStateException("Stored content rows differ from frozen version");
            }
        }
    }

    private static String text(JsonNode node, String key) { return node.path(key).asText(); }
}
