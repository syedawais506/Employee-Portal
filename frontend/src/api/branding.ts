import { apiClient } from "@/api/client";
import type { CompanyBranding } from "@/types";

export async function getBranding(): Promise<CompanyBranding> {
  const response = await apiClient.get<CompanyBranding>("/branding");
  return response.data;
}

export async function updateBrandingColor(primaryColor: string | null): Promise<CompanyBranding> {
  const response = await apiClient.patch<CompanyBranding>("/branding/color", { primary_color: primaryColor });
  return response.data;
}

export async function uploadBrandingLogo(file: File): Promise<CompanyBranding> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<CompanyBranding>("/branding/logo", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}
