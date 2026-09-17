package dev.luma.game;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import java.util.concurrent.ThreadLocalRandom;

@SpringBootApplication
public class GameApplication {
    public static void main(String[] args) { SpringApplication.run(GameApplication.class, args); }
    @Bean RandomSource randomSource() { return bound -> ThreadLocalRandom.current().nextLong(bound); }
}
