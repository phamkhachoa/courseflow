"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { Button, PageShell, TextInput } from "@/shared/ui";

export default function CertificateVerifyEntryPage() {
  const router = useRouter();
  const [code, setCode] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (code.trim()) router.push(`/certificates/verify/${encodeURIComponent(code.trim())}`);
  }

  return (
    <PageShell
      eyebrow="Chứng chỉ"
      title="Xác minh chứng chỉ"
      description="Nhập mã xác minh in trên chứng chỉ CourseFlow"
    >
      <form className="flex max-w-md gap-2" onSubmit={submit}>
        <TextInput
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="VD: CF-2026-ABCD"
          className="flex-1"
        />
        <Button type="submit">
          <ShieldCheck className="size-4" />
          Xác minh
        </Button>
      </form>
    </PageShell>
  );
}
