package local.northstar.catalog;

import java.util.*;
import org.flywaydb.core.Flyway;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

/** Test helper only: verifies pinned isolated identity before standalone Flyway migration. */
public final class IsolatedMigration {
    public static void main(String[] args){
        var env=System.getenv();String port=env.get("MYSQL_PORT"),schema=env.get("DB_NAME"),uuid=env.get("NORTHSTAR_EXPECTED_DB_UUID");
        if(!"northstar_phase01_test".equals(schema) || port==null || Integer.parseInt(port)<3313 || Integer.parseInt(port)>3399 || uuid==null || uuid.equals("104d5d9d-cd3f-11f1-8da4-920f115cf5cb"))throw new IllegalStateException("Isolated test target required");
        String url="jdbc:mysql://127.0.0.1:"+port+"/"+schema+"?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true";
        var ds=new DriverManagerDataSource(url,"northstar_migrator",env.get("DB_MIGRATION_PASSWORD"));var db=new JdbcTemplate(ds);
        if(!uuid.equals(db.queryForObject("SELECT @@server_uuid",String.class)) || !List.of("northstar-english-local-v1").equals(db.queryForList("SELECT project_key FROM project_identity",String.class)))throw new IllegalStateException("Identity mismatch");
        var flyway=Flyway.configure().dataSource(ds).cleanDisabled(true).validateOnMigrate(true).load();flyway.migrate();flyway.validate();
    }
}
