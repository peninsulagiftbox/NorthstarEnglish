package local.northstar.catalog;

import java.nio.file.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;

public final class ContentImportCli {
    public static void main(String[] args) {
        try {
            ContentImport.check(args.length >= 2, "ARGUMENTS");
            String action = args[0];
            if (action.equals("validate")) {
                var issues = new CoreContent().validate(CoreContent.load(Path.of(args[1])));
                System.out.println(CoreContent.JSON.writeValueAsString(Map.of("valid", issues.isEmpty(), "issues", issues)));
                if (!issues.isEmpty()) System.exit(2);
                return;
            }
            var env = System.getenv();
            String port = env.getOrDefault("MYSQL_PORT", ""), schema = env.getOrDefault("DB_NAME", "");
            String uuid = env.getOrDefault("NORTHSTAR_IMPORT_DB_UUID", "");
            ContentImport.check(port.matches("[0-9]{4,5}") && Integer.parseInt(port) <= 65535 && !port.equals("3308")
                && (Set.of("northstar_english", "northstar_phase01_test").contains(schema)
                    || ("true".equals(env.get("NORTHSTAR_ALLOW_RESTORE_DB")) && schema.matches("northstar_restore_[0-9]{14}")))
                && uuid.matches("[a-f0-9-]{36}") && !uuid.equals("104d5d9d-cd3f-11f1-8da4-920f115cf5cb"), "ISOLATED_TARGET_REQUIRED");
            var ds = new DriverManagerDataSource("jdbc:mysql://127.0.0.1:" + port + "/" + schema
                + "?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true&characterEncoding=UTF-8&connectTimeout=3000&socketTimeout=60000",
                "northstar_importer", Objects.requireNonNull(env.get("DB_IMPORT_PASSWORD")));
            var db = new JdbcTemplate(ds);
            ContentImport.check(uuid.equals(db.queryForObject("SELECT @@server_uuid", String.class)), "DATABASE_IDENTITY");
            var service = new ContentImport(db, new TransactionTemplate(new DataSourceTransactionManager(ds)),
                Path.of(Objects.requireNonNull(env.get("NORTHSTAR_IMPORT_MEDIA_ROOT"))));
            Object result;
            if (action.equals("status")) result = service.status(args[1]);
            else {
                var bundle = CoreContent.load(Path.of(args[1]));
                result = switch (action) {
                    case "dry-run" -> service.plan(bundle);
                    case "verify" -> service.verify(bundle);
                    case "apply", "resume" -> {
                        ContentImport.check(args.length == 4, "PLAN_AND_EXPLICIT_HASH_REQUIRED");
                        yield service.apply(bundle, CoreContent.JSON.readTree(Files.readAllBytes(Path.of(args[2]))), args[3]);
                    }
                    case "publish" -> {
                        ContentImport.check(args.length == 5, "OPERATION_EXPECTED_CURRENT_ACTOR_REQUIRED");
                        yield service.publish(bundle, args[2], args[3].equals("null") ? null : args[3], args[4]);
                    }
                    default -> throw new IllegalArgumentException("UNKNOWN_COMMAND");
                };
            }
            System.out.println(CoreContent.JSON.writeValueAsString(result));
            if (result instanceof Map<?, ?> map && map.get("code") != null
                    && !Set.of("applied", "no_op", "verified", "PUBLISHED").contains(map.get("code"))) System.exit(2);
        } catch (Exception error) {
            String code = error instanceof IllegalArgumentException ? error.getMessage() : "IMPORT_OPERATION_FAILED";
            System.err.println(CoreContent.JSON.writeValueAsString(Map.of("code", Objects.toString(code, "INVALID_INPUT"),
                "path", "/", "severity", "error", "message", "导入操作未成功；未隐式执行迁移。",
                "suggestion", "核对包、冻结计划、隔离身份和媒体；保留现场后执行 status/verify/resume。")));
            System.exit(2);
        }
    }
}
