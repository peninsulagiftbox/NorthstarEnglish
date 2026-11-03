package local.northstar.knowledge;

import java.lang.reflect.*;
import java.util.Map;
import local.northstar.NorthstarApplication;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

/** Reuses the frozen suite's original fixtures; deliberately retains this new QA database. */
class FinalQaFixture {
    @Test void seedOriginalCoursesWithoutLearningEvidence() throws Exception {
        if (!"1".equals(System.getenv("NORTHSTAR_FINAL_QA"))) throw new IllegalStateException("QA only");
        try (var app = new SpringApplicationBuilder(NorthstarApplication.class).run("--spring.main.web-application-type=none")) {
            var db = new JdbcTemplate(app.getBean(org.flywaydb.core.Flyway.class).getConfiguration().getDataSource());
            org.junit.jupiter.api.Assertions.assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"), db.queryForObject("SELECT @@server_uuid", String.class));
            var fixture = new ConceptReviewIntegrationTest();
            Field field = fixture.getClass().getDeclaredField("admin"); field.setAccessible(true); field.set(fixture, db);
            Method make = fixture.getClass().getDeclaredMethod("fixture", String.class, int.class, int.class, Map.class); make.setAccessible(true);
            make.invoke(fixture, "cr-a", 1, 4, Map.of(3, "The bank opens beside the garden gate."));
            make.invoke(fixture, "cr-b", 1, 3, Map.of(2, "The bank keeps the town's money safe."));
            invoke(fixture, "exercises");
            var cli = app.getBean(KnowledgeRegistrationCli.class);
            var mapper = JsonMapper.builder().build();
            org.junit.jupiter.api.Assertions.assertEquals("REGISTERED", cli.register(mapper.readTree((String) invoke(fixture, "registerA"))).get("code"));
            org.junit.jupiter.api.Assertions.assertEquals("REGISTERED", cli.register(mapper.readTree((String) invoke(fixture, "registerB"))).get("code"));
        }
    }
    private Object invoke(Object fixture, String name) throws Exception {
        Method method = fixture.getClass().getDeclaredMethod(name); method.setAccessible(true); return method.invoke(fixture);
    }
}
