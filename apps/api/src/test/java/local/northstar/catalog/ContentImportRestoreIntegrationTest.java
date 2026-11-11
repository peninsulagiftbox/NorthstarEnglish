package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.*;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_ALLOW_RESTORE_DB", matches="true")
class ContentImportRestoreIntegrationTest {
    @Test void restoredContentAcceptsAnotherIndependentCourse() throws Exception {
        assertNotEquals("3308", System.getenv("MYSQL_PORT"));
        String schema = System.getenv("DB_NAME");
        assertTrue(schema.matches("northstar_restore_[0-9]{14}"));
        var source = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + System.getenv("MYSQL_PORT")
            + "/" + schema + "?connectionTimeZone=UTC", "northstar_importer", System.getenv("DB_IMPORT_PASSWORD"));
        var db = new JdbcTemplate(source);
        assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"), db.queryForObject("SELECT @@server_uuid", String.class));
        var catalog = new CatalogReader(db);
        assertEquals(12, catalog.lesson("sample-a", null).path("sentences").size());
        assertEquals(24, catalog.lesson("sample-b", null).path("sentences").size());
        var service = new ContentImport(db, new TransactionTemplate(new DataSourceTransactionManager(source)),
            Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT")));
        var bundle = CoreContent.load(ImportFixtures.renamed(Files.createTempDirectory("northstar-restored-new-"),
            "sample-a-v1", "restored-new-v1", "restored-new", 1, true));
        var plan = service.plan(bundle);
        assertEquals("applied", service.apply(bundle, CoreContent.JSON.valueToTree(plan), plan.get("planHash").toString()).get("code"));
        assertEquals("PUBLISHED", service.publish(bundle, UUID.randomUUID().toString(), null, "synthetic-contract-fixture").get("code"));
        assertEquals(12, catalog.lesson("restored-new", null).path("sentences").size());
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='restored-new'", Integer.class));
    }
}
