/** C16 enables this only through the explicit durable bootstrap flow. */
export interface CloudProjectCapabilities {
  encryptedInitialUpload: boolean
}

export const cloudProjectCapabilities: Readonly<CloudProjectCapabilities> = {
  encryptedInitialUpload: true,
}

export function canEnableCloudProjectSync(
  capabilities: CloudProjectCapabilities = cloudProjectCapabilities,
): boolean {
  return capabilities.encryptedInitialUpload
}
