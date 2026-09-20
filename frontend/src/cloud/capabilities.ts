/**
 * C8 has only a metadata registry.  Enabling the visible production switch is
 * deferred until encrypted initial upload exists, so a slot is never mistaken
 * for synchronised project data.
 */
export interface CloudProjectCapabilities {
  encryptedInitialUpload: boolean
}

export const cloudProjectCapabilities: Readonly<CloudProjectCapabilities> = {
  encryptedInitialUpload: false,
}

export function canEnableCloudProjectSync(
  capabilities: CloudProjectCapabilities = cloudProjectCapabilities,
): boolean {
  return capabilities.encryptedInitialUpload
}
