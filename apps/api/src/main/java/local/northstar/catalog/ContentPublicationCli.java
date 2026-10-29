package local.northstar.catalog;

import java.nio.file.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

/** Standalone entry point: no Spring boot, Flyway, seeders or recording reconciliation. */
public final class ContentPublicationCli {
    public static void main(String[] args) {
        try {
            var env=System.getenv();String port=env.get("MYSQL_PORT"),uuid=env.get("NORTHSTAR_PUBLICATION_DB_UUID"),schema=env.get("DB_NAME");
            if(port==null || !port.matches("[0-9]{4,5}") || Integer.parseInt(port)<1024 || Integer.parseInt(port)>65535 || port.equals("3308")
                    || uuid==null || uuid.equals("104d5d9d-cd3f-11f1-8da4-920f115cf5cb") || !Set.of("northstar_english","northstar_phase01_test").contains(schema)
                    || args.length<1)throw new IllegalArgumentException();
            var ds=new DriverManagerDataSource("jdbc:mysql://127.0.0.1:"+port+"/"+schema+"?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true&characterEncoding=UTF-8&connectTimeout=3000", "northstar_publisher",Objects.requireNonNull(env.get("DB_PUBLICATION_PASSWORD")));
            var db=new JdbcTemplate(ds);
            if(!uuid.equals(db.queryForObject("SELECT @@server_uuid",String.class)) || !List.of("northstar-english-local-v1").equals(db.queryForList("SELECT project_key FROM project_identity",String.class)))throw new IllegalArgumentException();
            var service=new ContentPublication(db,new TransactionTemplate(new DataSourceTransactionManager(ds)),Path.of(Objects.requireNonNull(env.get("NORTHSTAR_CONTENT_ROOT"))));
            var json=JsonMapper.builder().build();
            if(args.length==4 && args[0].equals("validate")) {
                String result=service.validate(args[1],args[2],args[3]);System.out.println(json.writeValueAsString(Map.of("code",result)));if(!result.equals("VALIDATED"))System.exit(2);
            }else if(args.length==2 && args[0].equals("execute")) {
                var request=json.readValue(Files.readString(Path.of(args[1])),ContentPublication.Request.class);var result=service.execute(request);
                System.out.println(json.writeValueAsString(result));if(!Set.of("PUBLISHED","WITHDRAWN").contains(result.code()))System.exit(2);
            }else throw new IllegalArgumentException();
        }catch(Exception e){System.err.println("CONTENT_OPERATION_FAILED: check isolated identity, credentials and arguments; no migration attempted");System.exit(1);}
    }
}
