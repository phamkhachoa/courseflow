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

async function authPost(path: string, body: LoginInput | RegisterInput, fallback: string) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await readError(response, fallback));
  }
  return unwrap<StoredSession>(await response.json());
}

export function loginLearner(input: LoginInput) {
  return authPost("/v1/auth/login", input, "Đăng nhập thất bại.");
}

export function registerLearner(input: RegisterInput) {
  return authPost("/v1/auth/register", input, "Đăng ký thất bại.");
}
