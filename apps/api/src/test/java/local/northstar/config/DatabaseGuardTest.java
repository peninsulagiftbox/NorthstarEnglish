package local.northstar.config;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.configuration.Configuration;
import org.junit.jupiter.api.Test;

class DatabaseGuardTest {
    private Flyway connectionTo(String schema, String project, int tableCount) throws Exception {
        var flyway = mock(Flyway.class);
        var config = mock(Configuration.class);
        var source = mock(DataSource.class);
        var connection = mock(Connection.class);
        when(flyway.getConfiguration()).thenReturn(config);
        when(config.getDataSource()).thenReturn(source);
        when(source.getConnection()).thenReturn(connection);
        when(connection.getCatalog()).thenReturn(schema);
        when(connection.prepareStatement(anyString())).thenAnswer(call -> {
            String sql = call.getArgument(0);
            var statement = mock(PreparedStatement.class);
            var result = mock(ResultSet.class);
            when(statement.executeQuery()).thenReturn(result);
            when(result.next()).thenReturn(true, false);
            when(result.getString(1)).thenReturn(project);
            when(result.getInt(1)).thenReturn(sql.contains("table_name =") ? 0 : tableCount);
            return statement;
        });
        return flyway;
    }

    @Test void refusesUnknownSchemaBeforeAnyMutation() throws Exception {
        var flyway = connectionTo("another_project", DatabaseGuard.PROJECT, 1);
        assertThrows(IllegalStateException.class, () -> new DatabaseGuard().guardedMigration().migrate(flyway));
        verify(flyway, never()).baseline();
        verify(flyway, never()).migrate();
    }

    @Test void refusesWrongProjectBeforeAnyMutation() throws Exception {
        var flyway = connectionTo("northstar_english", "another-project", 1);
        assertThrows(IllegalStateException.class, () -> new DatabaseGuard().guardedMigration().migrate(flyway));
        verify(flyway, never()).baseline();
        verify(flyway, never()).migrate();
    }

    @Test void refusesBootstrapWhenUnknownTablesExist() throws Exception {
        var flyway = connectionTo("northstar_english", DatabaseGuard.PROJECT, 2);
        assertThrows(IllegalStateException.class, () -> new DatabaseGuard().guardedMigration().migrate(flyway));
        verify(flyway, never()).baseline();
        verify(flyway, never()).migrate();
    }
}
