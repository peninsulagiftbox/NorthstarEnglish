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
        var bundle = content.load();
        var source = flyway.getConfiguration().getDataSource();
        var jdbc = new JdbcTemplate(source);
        new TransactionTemplate(new DataSourceTransactionManager(source)).executeWithoutResult(transaction -> {
            // Lock the project row so simultaneous local startups cannot race the seed.
            jdbc.queryForObject("SELECT project_key FROM project_identity FOR UPDATE", String.class);
            var versions = jdbc.queryForList("SELECT content_sha256, manifest_sha256 FROM lesson_version WHERE id = 'demo-01-v1'");
            if (!versions.isEmpty()) {
                if (!Objects.equals(bundle.lessonHash(), versions.getFirst().get("content_sha256"))
                        || !Objects.equals(bundle.manifestHash(), versions.getFirst().get("manifest_sha256"))) {
                    throw new IllegalStateException("Frozen content version changed; create a new version");
                }
                verifyRows(jdbc, bundle);
                return;
            }
            JsonNode lesson = bundle.lesson(), manifest = bundle.manifest();
            for (JsonNode license : manifest.path("licenses")) {
                jdbc.update("INSERT INTO content_license (id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,?,?)",
                        text(license,"id"), text(license,"sourceType"), text(license,"sourceRef"), text(license,"reviewStatus"), license.toString());
            }
            for (JsonNode book : manifest.path("books")) {
                jdbc.update("INSERT INTO book (id,catalog_key,sequence_no,title,edition_label,availability,declared_lesson_count,metadata_source) VALUES (?,?,?,?,?,?,?,?)",
                        text(book,"id"), text(book,"catalogKey"), book.path("sequence").asInt(), text(book,"title"), text(book,"editionLabel"),
                        text(book,"availability"), book.path("declaredLessonCount").asInt(), text(book,"metadataSource"));
            }
            jdbc.update("INSERT INTO lesson (id,slug,kind,availability) VALUES (?,?,?,?)", text(lesson,"id"), text(lesson,"slug"), text(lesson,"kind"), text(lesson,"availability"));
            jdbc.update("INSERT INTO lesson_version (id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready) VALUES (?,?,?,?,?,?,?,FALSE)",
                    text(lesson,"versionId"), text(lesson,"id"), lesson.path("version").asInt(), text(lesson,"licenseId"), bundle.lessonHash(), bundle.manifestHash(), lesson.toString());
            for (JsonNode audio : manifest.path("audioAssets")) {
                jdbc.update("INSERT INTO audio_asset (id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,?,?,?,?,'ready')",
                        text(audio,"id"), text(lesson,"versionId"), text(audio,"licenseId"), text(audio,"sourceKind"), "demo-01/v1/" + text(audio,"storageKey"),
                        text(audio,"mimeType"), audio.path("byteSize").asInt(), audio.path("durationMs").asInt(), text(audio,"sha256"));
            }
            for (JsonNode s : lesson.path("sentences")) {
                jdbc.update("INSERT INTO sentence (id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        text(s,"id"), text(lesson,"id"), text(lesson,"versionId"), text(s,"stableKey"), s.path("sequence").asInt(), text(s,"speaker"),
                        text(s,"text"), text(s,"translation"), text(s,"explanation"), text(s,"focus"), text(s,"audioAssetId"), 0, s.path("endMs").asInt());
            }
            jdbc.update("UPDATE lesson SET current_version_id = ? WHERE id = ?", text(lesson,"versionId"), text(lesson,"id"));
            verifyRows(jdbc, bundle);
        });
    }

    private void verifyRows(JdbcTemplate jdbc, ContentPackage.Bundle bundle) {
        if (jdbc.queryForObject("SELECT COUNT(*) FROM sentence WHERE lesson_version_id = 'demo-01-v1'", Integer.class) != 10
                || jdbc.queryForObject("SELECT COUNT(*) FROM audio_asset WHERE lesson_version_id = 'demo-01-v1'", Integer.class) != 10
                || jdbc.queryForObject("SELECT COUNT(*) FROM book WHERE availability = 'catalog_only'", Integer.class) != 4) {
            throw new IllegalStateException("Seed data incomplete; refuse silent repair");
        }
        String payload = jdbc.queryForObject("SELECT payload_json FROM lesson_version WHERE id = 'demo-01-v1'", String.class);
        if (!tools.jackson.databind.json.JsonMapper.builder().build().readTree(payload).equals(bundle.lesson())) {
            throw new IllegalStateException("Stored content differs from frozen version");
        }
        for (JsonNode sentence : bundle.lesson().path("sentences")) {
            verify(jdbc, "sentence", text(sentence,"id"), new String[]{"lesson_id","lesson_version_id","stable_key","sequence_no","speaker","text","translation","explanation","focus","audio_asset_id","start_ms","end_ms"},
                    new Object[]{"demo-01","demo-01-v1",text(sentence,"stableKey"),sentence.path("sequence").asInt(),text(sentence,"speaker"),text(sentence,"text"),text(sentence,"translation"),text(sentence,"explanation"),text(sentence,"focus"),text(sentence,"audioAssetId"),0,sentence.path("endMs").asInt()});
        }
        for (JsonNode audio : bundle.manifest().path("audioAssets")) {
            verify(jdbc, "audio_asset", text(audio,"id"), new String[]{"lesson_version_id","license_id","source_kind","storage_key","mime_type","byte_size","duration_ms","sha256","status"},
                    new Object[]{"demo-01-v1",text(audio,"licenseId"),text(audio,"sourceKind"),"demo-01/v1/"+text(audio,"storageKey"),text(audio,"mimeType"),audio.path("byteSize").asInt(),audio.path("durationMs").asInt(),text(audio,"sha256"),"ready"});
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
        verify(jdbc, "lesson", "demo-01", new String[]{"slug","kind","availability","book_id","current_version_id"},
                new Object[]{text(bundle.lesson(),"slug"),"original_demo","available",null,"demo-01-v1"});
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
