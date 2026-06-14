package edu.courseflow.commonlibrary.exception;

/**
 * Marker for exceptions that expose a stable machine-readable error code to API clients.
 */
public interface ErrorCodeCarrier {

    String errorCode();
}
