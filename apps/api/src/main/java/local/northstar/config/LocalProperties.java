package local.northstar.config;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Validated
@ConfigurationProperties("northstar")
public record LocalProperties(
        @Min(1024) @Max(65535) int webPort,
        @Min(1024) @Max(65535) int apiPort,
        @Pattern(regexp = "[a-f0-9]{64}") String dbPassword,
        @Pattern(regexp = "[a-f0-9]{64}") String migrationPassword) {
    // Deliberately exclude credentials from record-generated diagnostics.
    @Override public String toString() { return "LocalProperties[credentials=redacted]"; }
}
