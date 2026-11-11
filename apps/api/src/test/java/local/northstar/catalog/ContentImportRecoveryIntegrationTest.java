package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_IMPORT_SAMPLE_ROOT", matches=".+")
class ContentImportRecoveryIntegrationTest {
    @Test void fileFailuresStalePlansEmptyExercisesAndVersionCas() throws Exception {
        assertNotEquals("3308", System.getenv("MYSQL_PORT"));
        var source = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + System.getenv("MYSQL_PORT")
            + "/northstar_phase01_test?connectionTimeZone=UTC&socketTimeout=600000",
            "northstar_importer", System.getenv("DB_IMPORT_PASSWORD"));
        var db = new JdbcTemplate(source);
        assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"), db.queryForObject("SELECT @@server_uuid", String.class));
        var tx = new TransactionTemplate(new DataSourceTransactionManager(source));
        Path root = Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"));
        var service = new ContentImport(db, tx, root);
        Path fixtures = Files.createTempDirectory("northstar-import-recovery-");
        int number = 0;
        for (String stage : List.of("before_copy", "staged", "before_materialize", "before_dml", "before_commit")) {
            String lesson = "recover-" + ++number, version = lesson + "-v1";
            var bundle = CoreContent.load(ImportFixtures.renamed(fixtures.resolve(lesson), "sample-a-v1", version, lesson, 1, true));
            var plan = service.plan(bundle);
            var faultService = new ContentImport(db, tx, root, point -> {
                if (point.equals(stage)) throw new IllegalStateException("injected:" + stage);
            });
            assertThrows(IllegalStateException.class, () -> faultService.apply(bundle, CoreContent.JSON.valueToTree(plan), plan.get("planHash").toString()));
            assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM lesson_version WHERE id=?", Integer.class, version));
            assertEquals("applied", service.apply(bundle, CoreContent.JSON.valueToTree(plan), plan.get("planHash").toString()).get("code"));
            assertEquals("no_op", service.apply(bundle, CoreContent.JSON.valueToTree(plan), plan.get("planHash").toString()).get("code"));
            assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM exercise WHERE version_id=?", Integer.class, version));
            assertEquals("PUBLISHED", service.publish(bundle, UUID.randomUUID().toString(), null, "contract-simulation").get("code"));
            assertEquals(0, new CatalogReader(db).lesson(lesson, null).path("availableTasks").size());
        }
        var old = CoreContent.load(ImportFixtures.renamed(fixtures.resolve("version-old"), "sample-a-v1", "change-v1", "change", 1, true));
        var oldPlan = service.plan(old);
        service.apply(old, CoreContent.JSON.valueToTree(oldPlan), oldPlan.get("planHash").toString());
        var newer = CoreContent.load(ImportFixtures.renamed(fixtures.resolve("version-new"), "sample-a-v1", "change-v2", "change", 2, true));
        var stale = service.plan(newer);
        service.publish(old, UUID.randomUUID().toString(), null, "contract-simulation");
        assertThrows(IllegalArgumentException.class, () -> service.apply(newer, CoreContent.JSON.valueToTree(stale), stale.get("planHash").toString()));
        var refreshed = service.plan(newer);
        service.apply(newer, CoreContent.JSON.valueToTree(refreshed), refreshed.get("planHash").toString());
        assertEquals("CURRENT_VERSION_CONFLICT", service.publish(newer, UUID.randomUUID().toString(), null, "contract-simulation").get("code"));
        assertEquals("PUBLISHED", service.publish(newer, UUID.randomUUID().toString(), "change-v1", "contract-simulation").get("code"));
        assertEquals("change-v1", new CatalogReader(db).lesson("change", "change-v1").path("versionId").asText());
        assertEquals(12, db.queryForObject("SELECT COUNT(*) FROM sentence old JOIN sentence fresh ON old.identity_id=fresh.identity_id WHERE old.lesson_version_id='change-v1' AND fresh.lesson_version_id='change-v2'", Integer.class));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='change'", Integer.class));
        assertThrows(org.springframework.dao.DataAccessException.class,
            () -> db.update("UPDATE lesson_version SET payload_json='{}' WHERE id='change-v1'"));
        var finalPlan = service.plan(CoreContent.load(ImportFixtures.renamed(fixtures.resolve("media-drift"), "sample-a-v1", "media-drift-v1", "media-drift", 1, true)));
        var drift = CoreContent.load(fixtures.resolve("media-drift"));
        var asset = drift.content().path("audioAssets").get(0);
        Path destination = root.resolve(asset.path("storageKey").asText());
        Files.createDirectories(destination.getParent());
        Files.copy(drift.root().resolve(asset.path("storageKey").asText()), destination);
        assertThrows(IllegalArgumentException.class,
            () -> service.apply(drift, CoreContent.JSON.valueToTree(finalPlan), finalPlan.get("planHash").toString()));
        System.out.println("Recovery fault hooks, stale pointers/media, stable identity, old URL and no-exercise contract: PASS.");
    }
}
