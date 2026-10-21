package local.northstar;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class NorthstarApplication {
    public static void main(String[] args) {
        SpringApplication.run(NorthstarApplication.class, args);
    }
}
