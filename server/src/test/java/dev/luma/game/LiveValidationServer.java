package dev.luma.game;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

/** Explicit test-only live harness, never included in bootJar. No production RNG switch. */
public class LiveValidationServer {
    @TestConfiguration
    static class FixedRandom {
        @Bean @Primary RandomSource captureFixtureRandom() {
            var index = new java.util.concurrent.atomic.AtomicInteger();
            return bound -> bound==500 && "1".equals(System.getenv("LUMA_TEST_BATCH1"))
                ? (index.getAndIncrement()%5)*100L : bound==1_000_000 && "failure".equals(System.getenv("LUMA_TEST_CAPTURE_MODE")) ? bound-1 : 0;
        }
    }
    public static void main(String[] args) {
        String url=System.getenv("LUMA_DB_URL");
        if(url==null || !url.matches("jdbc:postgresql://(127\\.0\\.0\\.1|localhost):[0-9]+/[^/?]+_test"))
            throw new IllegalArgumentException("Test-only live harness requires explicit loopback *_test database");
        SpringApplication.run(new Class<?>[]{GameApplication.class,FixedRandom.class},args);
    }
}
