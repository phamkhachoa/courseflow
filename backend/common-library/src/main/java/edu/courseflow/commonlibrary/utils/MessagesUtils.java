package edu.courseflow.commonlibrary.utils;

import java.text.MessageFormat;
import java.util.ResourceBundle;

/**
 * Resolves error codes to human messages from {@code messages.properties} on the classpath.
 * Each service ships its own bundle so messages stay close to the domain that owns them.
 * Placeholders use {@code {}} (in order) and are converted to {@link MessageFormat} indices.
 */
public final class MessagesUtils {

    private static final String BUNDLE_NAME = "messages/messages";

    private MessagesUtils() {
    }

    public static String getMessage(String code, Object... args) {
        try {
            ResourceBundle bundle = ResourceBundle.getBundle(BUNDLE_NAME);
            String pattern = indexPlaceholders(bundle.getString(code));
            return MessageFormat.format(pattern, args);
        } catch (Exception ex) {
            return code;
        }
    }

    private static String indexPlaceholders(String raw) {
        StringBuilder sb = new StringBuilder();
        int index = 0;
        for (int i = 0; i < raw.length(); i++) {
            if (i + 1 < raw.length() && raw.charAt(i) == '{' && raw.charAt(i + 1) == '}') {
                sb.append('{').append(index++).append('}');
                i++;
            } else {
                sb.append(raw.charAt(i));
            }
        }
        return sb.toString();
    }
}
