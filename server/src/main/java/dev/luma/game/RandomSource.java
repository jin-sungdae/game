package dev.luma.game;

@FunctionalInterface
public interface RandomSource { long nextLong(long bound); }
