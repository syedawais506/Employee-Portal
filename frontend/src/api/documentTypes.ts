import { apiClient } from "@/api/client";
import type { DocumentType } from "@/types";

export interface DocumentTypeInput {
  name: string;
  is_required: boolean;
  sort_order: number;
}

export async function listDocumentTypes(): Promise<DocumentType[]> {
  const response = await apiClient.get<DocumentType[]>("/document-types");
  return response.data;
}

export async function createDocumentType(payload: DocumentTypeInput): Promise<DocumentType> {
  const response = await apiClient.post<DocumentType>("/document-types", payload);
  return response.data;
}

export async function updateDocumentType(id: string, payload: Partial<DocumentTypeInput>): Promise<DocumentType> {
  const response = await apiClient.patch<DocumentType>(`/document-types/${id}`, payload);
  return response.data;
}

export async function deleteDocumentType(id: string): Promise<void> {
  await apiClient.delete(`/document-types/${id}`);
}
