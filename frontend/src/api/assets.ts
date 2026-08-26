import { apiClient } from "@/api/client";
import type { Asset, AssetAssignment, AssetSummary, AssetType, Page } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export async function listAssetTypes(): Promise<AssetType[]> {
  const response = await apiClient.get<AssetType[]>("/asset-types");
  return response.data;
}

export async function createAssetType(name: string): Promise<AssetType> {
  const response = await apiClient.post<AssetType>("/asset-types", { name });
  return response.data;
}

export async function updateAssetType(id: string, name: string): Promise<AssetType> {
  const response = await apiClient.patch<AssetType>(`/asset-types/${id}`, { name });
  return response.data;
}

export async function deleteAssetType(id: string): Promise<void> {
  await apiClient.delete(`/asset-types/${id}`);
}

export interface AssetInput {
  asset_type_id: string;
  asset_tag: string;
  name: string;
  purchase_date?: string | null;
  warranty_expiry?: string | null;
  notes?: string | null;
}

export type AssetUpdateInput = Partial<AssetInput> & { status?: string };

export interface AssetListFilters {
  assetTypeId?: string;
  status?: string;
}

export async function listAssets(page: number, pageSize: number, filters: AssetListFilters = {}): Promise<Page<Asset>> {
  const response = await apiClient.get<Page<Asset>>("/assets", {
    params: { page, page_size: pageSize, asset_type_id: filters.assetTypeId, status: filters.status },
  });
  return response.data;
}

export async function createAsset(payload: AssetInput): Promise<Asset> {
  const response = await apiClient.post<Asset>("/assets", payload);
  return response.data;
}

export async function updateAsset(id: string, payload: AssetUpdateInput): Promise<Asset> {
  const response = await apiClient.patch<Asset>(`/assets/${id}`, payload);
  return response.data;
}

export async function deleteAsset(id: string): Promise<void> {
  await apiClient.delete(`/assets/${id}`);
}

export async function assignAsset(id: string, employeeId: string): Promise<Asset> {
  const response = await apiClient.post<Asset>(`/assets/${id}/assign`, { employee_id: employeeId });
  return response.data;
}

export async function returnAsset(id: string): Promise<Asset> {
  const response = await apiClient.post<Asset>(`/assets/${id}/return`);
  return response.data;
}

export async function getAssetHistory(id: string): Promise<AssetAssignment[]> {
  const response = await apiClient.get<AssetAssignment[]>(`/assets/${id}/history`);
  return response.data;
}

export async function listMyAssets(): Promise<AssetAssignment[]> {
  const response = await apiClient.get<AssetAssignment[]>("/assets/mine");
  return response.data;
}

export async function getAssetSummary(): Promise<AssetSummary> {
  const response = await apiClient.get<AssetSummary>("/assets/summary");
  return response.data;
}

export interface AssetExportFilters {
  assetTypeId?: string;
  status?: string;
}

export async function downloadAssetExportCsv(filters: AssetExportFilters = {}): Promise<void> {
  const response = await apiClient.get<Blob>("/assets/export", {
    params: { asset_type_id: filters.assetTypeId, status: filters.status },
    responseType: "blob",
  });
  triggerCsvDownload(response.data, "asset-export.csv");
}
