package edu.courseflow.identity.service;

import java.nio.ByteBuffer;
import java.time.Instant;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Service;

@Service
public class TotpService {

    private static final int STEP_SECONDS = 30;
    private static final int DIGITS = 6;

    public boolean verify(String base32Secret, String code) {
        if (base32Secret == null || base32Secret.isBlank() || code == null || !code.matches("\\d{6}")) {
            return false;
        }
        byte[] key;
        try {
            key = decodeBase32(base32Secret);
        } catch (IllegalArgumentException ex) {
            return false;
        }
        long counter = Instant.now().getEpochSecond() / STEP_SECONDS;
        for (long offset = -1; offset <= 1; offset++) {
            if (code.equals(generate(key, counter + offset))) {
                return true;
            }
        }
        return false;
    }

    private String generate(byte[] key, long counter) {
        try {
            Mac mac = Mac.getInstance("HmacSHA1");
            mac.init(new SecretKeySpec(key, "HmacSHA1"));
            byte[] hash = mac.doFinal(ByteBuffer.allocate(Long.BYTES).putLong(counter).array());
            int offset = hash[hash.length - 1] & 0x0f;
            int binary = ((hash[offset] & 0x7f) << 24)
                    | ((hash[offset + 1] & 0xff) << 16)
                    | ((hash[offset + 2] & 0xff) << 8)
                    | (hash[offset + 3] & 0xff);
            int otp = binary % (int) Math.pow(10, DIGITS);
            return String.format("%0" + DIGITS + "d", otp);
        } catch (Exception ex) {
            return "";
        }
    }

    private byte[] decodeBase32(String value) {
        String normalized = value.replace("=", "").replace(" ", "").toUpperCase();
        ByteBuffer out = ByteBuffer.allocate(normalized.length() * 5 / 8 + 8);
        int buffer = 0;
        int bitsLeft = 0;
        for (int i = 0; i < normalized.length(); i++) {
            int decoded = decodeBase32Char(normalized.charAt(i));
            if (decoded < 0) {
                throw new IllegalArgumentException("Invalid base32 secret");
            }
            buffer = (buffer << 5) | decoded;
            bitsLeft += 5;
            if (bitsLeft >= 8) {
                out.put((byte) ((buffer >> (bitsLeft - 8)) & 0xff));
                bitsLeft -= 8;
            }
        }
        byte[] result = new byte[out.position()];
        out.flip();
        out.get(result);
        return result;
    }

    private int decodeBase32Char(char c) {
        if (c >= 'A' && c <= 'Z') {
            return c - 'A';
        }
        if (c >= '2' && c <= '7') {
            return c - '2' + 26;
        }
        return -1;
    }
}
