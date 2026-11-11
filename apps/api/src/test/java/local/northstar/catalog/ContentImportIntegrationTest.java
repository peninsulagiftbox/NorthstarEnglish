package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_IMPORT_SAMPLE_ROOT", matches=".+")
class ContentImportIntegrationTest {
    @Test void isolatedImportLifecycle() throws Exception {
        String port = System.getenv("MYSQL_PORT");
        assertNotEquals("3308", port);
        assertEquals("northstar_phase01_test", System.getenv("DB_NAME"));
        var source = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + port
            + "/northstar_phase01_test?connectionTimeZone=UTC&socketTimeout=600000",
            "northstar_importer", System.getenv("DB_IMPORT_PASSWORD"));
        var db = new JdbcTemplate(source);
        assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"), db.queryForObject("SELECT @@server_uuid", String.class));
        var tx = new TransactionTemplate(new DataSourceTransactionManager(source));
        Path root = Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"));
        var service = new ContentImport(db, tx, root);
        Path fixtureRoot = Files.createTempDirectory("northstar-import-contract-");
        var first = CoreContent.load(ImportFixtures.copy(fixtureRoot.resolve("a"), "a", true));
        var second = CoreContent.load(ImportFixtures.copy(fixtureRoot.resolve("b"), "b", true));
        assertEquals(List.of(), new CoreContent().validate(first));
        assertEquals(List.of(), new CoreContent().validate(second));
        var before = digest(db);
        var filesBefore = media(root);
        var plan = service.plan(first);
        assertEquals(plan, service.plan(first));
        assertEquals(before, digest(db));
        assertEquals(filesBefore, media(root));
        String planHash = plan.get("planHash").toString();
        var planJson = CoreContent.JSON.valueToTree(plan);
        assertThrows(IllegalArgumentException.class, () -> service.apply(first, planJson, "0".repeat(64)));
        try (var pool = Executors.newFixedThreadPool(2)) {
            var futures = pool.invokeAll(List.<Callable<String>>of(
                () -> service.apply(first, planJson, planHash).get("code").toString(),
                () -> service.apply(first, planJson, planHash).get("code").toString()));
            assertEquals(Set.of("applied", "no_op"), Set.of(futures.get(0).get(), futures.get(1).get()));
        }
        assertEquals("no_op", service.apply(first, planJson, planHash).get("code"));
        assertNull(db.queryForObject("SELECT current_version_id FROM lesson WHERE id='sample-a'", String.class));
        assertEquals(12, db.queryForObject("SELECT COUNT(*) FROM sentence WHERE lesson_id='sample-a'", Integer.class));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='sample-a'", Integer.class));
        var changed = ((tools.jackson.databind.node.ObjectNode)first.content()).deepCopy();
        ((tools.jackson.databind.node.ObjectNode)changed.path("lesson")).put("title", "Changed immutable package");
        ImportFixtures.save(first.root(), changed, ((tools.jackson.databind.node.ObjectNode)first.manifest()).deepCopy());
        var changedBundle = CoreContent.load(first.root());
        assertTrue(service.plan(changedBundle).get("conflicts").toString().contains("PACKAGE_ID_CONFLICT"));
        ImportFixtures.save(first.root(), (tools.jackson.databind.node.ObjectNode)first.content(),
            (tools.jackson.databind.node.ObjectNode)first.manifest());
        var secondPlan = service.plan(second);
        var faultService = new ContentImport(db, tx, root, stage -> {
            if (stage.equals("before_dml")) throw new IllegalStateException("injected database failure after media");
        });
        assertThrows(IllegalStateException.class, () -> faultService.apply(second,
            CoreContent.JSON.valueToTree(secondPlan), secondPlan.get("planHash").toString()));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM lesson WHERE id='sample-b'", Integer.class));
        assertEquals("partial_failed", service.status("sample-b-v1-package").getFirst().get("state"));
        assertEquals("applied", service.apply(second, CoreContent.JSON.valueToTree(secondPlan), secondPlan.get("planHash").toString()).get("code"));
        assertEquals("no_op", service.apply(second, CoreContent.JSON.valueToTree(secondPlan), secondPlan.get("planHash").toString()).get("code"));
        assertEquals(2, db.queryForObject("SELECT COUNT(*) FROM knowledge_occurrence WHERE concept_id='sample-beside-location'", Integer.class));
        assertEquals(2, db.queryForObject("SELECT COUNT(*) FROM knowledge_concept WHERE canonical_key='bank'", Integer.class));
        assertEquals(5, db.queryForObject("SELECT COUNT(*) FROM exercise_set_item WHERE version_id='sample-a-v1'", Integer.class));
        assertEquals(12, db.queryForObject("SELECT COUNT(*) FROM exercise_set_item WHERE version_id='sample-b-v1'", Integer.class));
        assertThrows(org.springframework.dao.DataAccessException.class,
            () -> db.update("UPDATE exercise_attempt SET correct=correct"));
        assertThrows(org.springframework.dao.DataAccessException.class,
            () -> db.execute("CREATE TABLE forbidden_import_ddl(id INT)"));
        String operation = UUID.randomUUID().toString();
        assertEquals("PUBLISHED", service.publish(first, operation, null, "synthetic-contract-test-NOT-human-review").get("code"));
        assertEquals("PUBLISHED", service.publish(first, operation, null, "synthetic-contract-test-NOT-human-review").get("code"));
        assertEquals("CURRENT_VERSION_CONFLICT", service.publish(first, UUID.randomUUID().toString(), null, "contract-test").get("code"));
        var reader = new CatalogReader(db);
        assertEquals("basic_content", reader.lesson("sample-a", null).path("contentReadiness").asText());
        assertFalse(reader.lesson("sample-a", null).toString().contains("answerKey"));
        assertFalse(reader.lesson("sample-a", null).toString().contains("storageKey"));
        var asset = second.content().path("audioAssets").get(0);
        Path audio = root.resolve(asset.path("storageKey").asText());
        Path preserved = audio.resolveSibling("preserved-original.mp3");
        Files.move(audio, preserved);
        assertThrows(IllegalArgumentException.class,
            () -> service.publish(second, UUID.randomUUID().toString(), null, "contract-test"));
        assertNull(db.queryForObject("SELECT current_version_id FROM lesson WHERE id='sample-b'", String.class));
        Files.move(preserved, audio);
        assertEquals("PUBLISHED", service.publish(second, UUID.randomUUID().toString(), null, "synthetic-contract-test-NOT-human-review").get("code"));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id IN ('sample-a','sample-b')", Integer.class));
        System.out.println("E02/E03/E04 contract simulation passed; reviewers are synthetic inputs, NOT human proofreading/listening acceptance.");
    }
    private Map<String, Object> digest(JdbcTemplate db) {
        var result = new TreeMap<String, Object>();
        for (String table : db.queryForList("SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() ORDER BY table_name", String.class)) {
            var rows = db.query("SELECT * FROM `" + table + "`", (values, index) -> {
                var cells = new ArrayList<String>();
                for (int column = 1; column <= values.getMetaData().getColumnCount(); column++) cells.add(values.getString(column));
                return CoreContent.JSON.writeValueAsString(cells);
            });
            Collections.sort(rows);
            result.put(table, CoreContent.hash(rows));
        }
        return result;
    }
    private Map<String, String> media(Path root) throws Exception {
        var result = new TreeMap<String, String>();
        try (var paths = Files.walk(root)) {
            for (Path path : paths.filter(Files::isRegularFile).toList())
                result.put(root.relativize(path).toString(), ContentPackage.sha256(Files.readAllBytes(path)));
        }
        return result;
    }
}
