package dev.luma.game;

import org.springframework.dao.DataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.transaction.TransactionException;

@RestControllerAdvice
public class GameErrors {
    private static final Logger LOG=LoggerFactory.getLogger(GameErrors.class);
    @ExceptionHandler(GameFault.class)
    ResponseEntity<ErrorBody> fault(GameFault e) {return ResponseEntity.status(e.status).body(new ErrorBody(e.code,e.code));}
    record ErrorBody(String code,String message) {}
    @ExceptionHandler({GameUnavailable.class,DataAccessException.class,TransactionException.class})
    ResponseEntity<ErrorBody> unavailable(RuntimeException error) {
        LOG.warn("Local game request unavailable: {}",error.getClass().getSimpleName());
        return ResponseEntity.status(503).body(new ErrorBody("GAME_UNAVAILABLE","Local game state unavailable"));
    }
}
