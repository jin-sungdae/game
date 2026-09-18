package dev.luma.game;
public class GameFault extends RuntimeException {
    final int status;
    final String code;
    public GameFault(int status,String code) {super(code);this.status=status;this.code=code;}
}
