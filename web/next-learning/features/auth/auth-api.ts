"use client";

import { API_BASE_URL, unwrap } from "@/shared/api/envelope";
import type { StoredSession } from "@/shared/api/client";

type LoginInput = {
  email: string;
  password: string;
};

type RegisterInput = LoginInput & {
  fullName: string;
};

type UserDto = {
  id: number;
  email: string;
  fullName: string;
  status: string;
  emailVerified: boolean;
  mfaEnabled: boolean;
};

export type RegistrationResponse = {
  user: UserDto;
  emailVerificationRequired: boolean;
  verificationExpiresAt: string;
};

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  title?: string;
  statusCode?: number;
};

function friendlyAuthMessage(raw: string, fallback: string) {
  if (raw.includes("EMAIL_ALREADY_EXISTS")) return "Email này đã được đăng ký. Hãy đăng nhập hoặc dùng email khác.";
  if (raw.includes("PASSWORD_TOO_WEAK")) {
    return "Mật khẩu cần tối thiểu 12 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.";
  }
  if (raw.includes("INVALID_CREDENTIALS")) return "Email hoặc mật khẩu không đúng.";
  if (raw.includes("EMAIL_VERIFICATION_TOKEN_INVALID")) return "Liên kết xác minh đã hết hạn hoặc không hợp lệ.";
  if (raw.includes("MFA_REQUIRED")) return "Tài khoản này cần mã xác thực bổ sung.";
  if (raw.includes("PASSWORD_CHANGE_REQUIRED")) return "Tài khoản này cần đổi mật khẩu trước khi tiếp tục.";
  return raw || fallback;
}

async function readError(response: Response, fallback: string) {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    const raw = payload.detail ?? payload.message ?? payload.title ?? "";
    return friendlyAuthMessage(raw, fallback);
  } catch {
    return fallback;
  }
}

async function authPost<T>(
  path: string,
  body: LoginInput | RegisterInput | { token: string } | { email: string },
  fallback: string
) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await readError(response, fallback));
  }
  const text = await response.text();
  return text ? unwrap<T>(JSON.parse(text)) : (undefined as T);
}

export function loginLearner(input: LoginInput) {
  return authPost<StoredSession>("/v1/auth/login", input, "Đăng nhập thất bại.");
}

export function registerLearner(input: RegisterInput) {
  return authPost<RegistrationResponse>("/v1/auth/register", input, "Đăng ký thất bại.");
}

export function verifyEmail(token: string) {
  return authPost<UserDto>("/v1/auth/email/verify", { token }, "Xác minh email thất bại.");
}

export function resendEmailVerification(email: string) {
  return authPost<void>("/v1/auth/email/resend", { email }, "Chưa gửi lại được email xác minh.");
}
