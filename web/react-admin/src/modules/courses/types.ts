import { z } from "zod";

export const courseMaterialSchema = z.object({
  id: z.string().optional(),
  courseId: z.string().optional().default(""),
  title: z.string(),
  materialType: z.string().optional().default(""),
  mediaId: z.string().nullable().optional(),
  position: z.number().optional().default(0)
});
export type CourseMaterial = z.infer<typeof courseMaterialSchema>;

export const courseSchema = z.object({
  id: z.string(),
  code: z.string(),
  title: z.string(),
  slug: z.string(),
  summary: z.string().optional().default(""),
  departmentId: z.string().optional().default(""),
  ownerId: z.string().optional().default(""),
  level: z.string().optional().default(""),
  status: z.string().optional().default(""),
  listPrice: z.union([z.number(), z.string()]).nullable().optional(),
  currency: z.string().nullable().optional(),
  priceStatus: z.string().optional().default("NOT_CONFIGURED"),
  createdAt: z.string().optional().default(""),
  materials: z.array(courseMaterialSchema).optional().default([])
});

export type Course = z.infer<typeof courseSchema>;

export type CreateCourseInput = {
  code: string;
  title: string;
  slug: string;
  summary: string;
  departmentId: string;
  level: string;
  listPrice?: number;
  currency?: string;
};
